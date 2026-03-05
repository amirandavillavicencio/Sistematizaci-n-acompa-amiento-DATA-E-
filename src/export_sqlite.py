from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text

SOURCE_SHEETS = {
    "SAN_JOAQUIN": "SAN_JOAQUIN",
    "VITACURA": "VITACURA",
    "RUT_SIN_CAMPUS": "SIN_CAMPUS",
}

ACTIVIDADES = [
    ("CIAC", "Apoyo Académico CIAC", "Apoyo_Academico_CIAC"),
    ("TALLERES", "Talleres", "Talleres"),
    ("MENTORIAS", "Mentorías", "Mentorias"),
    ("ATENCIONES", "Atenciones Individuales", "Atenciones_Individuales"),
]


def _normalize_participaciones(value: Any) -> int:
    if value is None:
        return 0
    txt = str(value).strip()
    if txt == "" or txt.lower() in {"nan", "none", "null"}:
        return 0
    if txt.upper() == "X":
        return 1
    try:
        return int(float(txt))
    except ValueError as exc:
        raise ValueError(f"Valor de participación inválido: {value!r}") from exc


def _get_col(df: pd.DataFrame, wanted: str, fallback: str = "") -> str:
    if wanted in df.columns:
        return wanted
    if fallback and fallback in df.columns:
        return fallback
    raise ValueError(f"No se encontró columna requerida: {wanted}")


def _git_sha(repo_root: Path) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(repo_root), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def export_excel_to_sqlite(excel_path: Path, sqlite_path: Path, repo_root: Path) -> None:
    try:
        if not excel_path.exists():
            raise FileNotFoundError(f"No existe el Excel fuente: {excel_path}")

        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        if sqlite_path.exists():
            sqlite_path.unlink()

        data_frames: dict[str, pd.DataFrame] = {}
        for sheet in [
            "RESUMEN_GENERAL",
            "SAN_JOAQUIN",
            "VITACURA",
            "RUT_SIN_CAMPUS",
            "REPORTE_CALIDAD",
            "RUT_INVALIDO_CUARENTENA",
        ]:
            data_frames[sheet] = pd.read_excel(excel_path, sheet_name=sheet, dtype=str, engine="openpyxl")

        engine = create_engine(f"sqlite:///{sqlite_path}")

        with engine.begin() as conn:
            conn.execute(text("PRAGMA foreign_keys=ON"))
            conn.execute(text("""
                CREATE TABLE dim_campus(
                    campus_id INTEGER PRIMARY KEY,
                    campus_nombre TEXT UNIQUE NOT NULL
                )
            """))
            conn.execute(text("""
                CREATE TABLE dim_estudiante(
                    estudiante_id INTEGER PRIMARY KEY,
                    rut TEXT UNIQUE NOT NULL,
                    nombre_canonico TEXT,
                    campus_id INTEGER,
                    FOREIGN KEY(campus_id) REFERENCES dim_campus(campus_id)
                )
            """))
            conn.execute(text("""
                CREATE TABLE dim_actividad(
                    actividad_id INTEGER PRIMARY KEY,
                    actividad_codigo TEXT UNIQUE NOT NULL,
                    actividad_nombre TEXT NOT NULL
                )
            """))
            conn.execute(text("""
                CREATE TABLE fact_participacion(
                    fact_id INTEGER PRIMARY KEY,
                    estudiante_id INTEGER NOT NULL,
                    actividad_id INTEGER NOT NULL,
                    campus_id INTEGER,
                    participaciones INTEGER NOT NULL,
                    fuente_resumen TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(estudiante_id, actividad_id, campus_id),
                    FOREIGN KEY(estudiante_id) REFERENCES dim_estudiante(estudiante_id),
                    FOREIGN KEY(actividad_id) REFERENCES dim_actividad(actividad_id),
                    FOREIGN KEY(campus_id) REFERENCES dim_campus(campus_id)
                )
            """))
            conn.execute(text("""
                CREATE TABLE audit_metadata(
                    clave TEXT PRIMARY KEY,
                    valor TEXT
                )
            """))

            for campus_nombre in ["SAN_JOAQUIN", "VITACURA", "SIN_CAMPUS"]:
                conn.execute(text("INSERT INTO dim_campus(campus_nombre) VALUES (:campus_nombre)"), {"campus_nombre": campus_nombre})

            for codigo, nombre, _ in ACTIVIDADES:
                conn.execute(
                    text("INSERT INTO dim_actividad(actividad_codigo, actividad_nombre) VALUES (:codigo, :nombre)"),
                    {"codigo": codigo, "nombre": nombre},
                )

            campus_ids = {
                row.campus_nombre: row.campus_id
                for row in conn.execute(text("SELECT campus_id, campus_nombre FROM dim_campus"))
            }
            actividad_ids = {
                row.actividad_codigo: row.actividad_id
                for row in conn.execute(text("SELECT actividad_id, actividad_codigo FROM dim_actividad"))
            }

            estudiantes_rows: list[dict[str, Any]] = []
            fact_rows: list[dict[str, Any]] = []

            for sheet_name, campus_dim_name in SOURCE_SHEETS.items():
                sheet_df = data_frames[sheet_name].fillna("")
                rut_col = _get_col(sheet_df, "RUT")
                nombre_col = _get_col(sheet_df, "Nombre")
                fuente_col = "fuentes" if "fuentes" in sheet_df.columns else ""
                campus_id = campus_ids[campus_dim_name]

                for _, row in sheet_df.iterrows():
                    rut = str(row[rut_col]).strip()
                    if not rut:
                        continue
                    nombre = str(row[nombre_col]).strip()
                    fuente_resumen = str(row[fuente_col]).strip() if fuente_col else ""

                    estudiantes_rows.append(
                        {
                            "rut": rut,
                            "nombre_canonico": nombre,
                            "campus_id": campus_id,
                        }
                    )

                    for codigo, _, excel_col in ACTIVIDADES:
                        participaciones = _normalize_participaciones(row.get(excel_col))
                        fact_rows.append(
                            {
                                "rut": rut,
                                "actividad_id": actividad_ids[codigo],
                                "campus_id": campus_id,
                                "participaciones": participaciones,
                                "fuente_resumen": fuente_resumen,
                            }
                        )

            estudiantes_df = pd.DataFrame(estudiantes_rows)
            estudiantes_df = (
                estudiantes_df.sort_values(["rut", "nombre_canonico"], kind="stable")
                .drop_duplicates(subset=["rut"], keep="first")
                .reset_index(drop=True)
            )
            estudiantes_df.to_sql("dim_estudiante", conn.connection, if_exists="append", index=False)

            rut_to_id = {
                row.rut: row.estudiante_id
                for row in conn.execute(text("SELECT estudiante_id, rut FROM dim_estudiante"))
            }

            fact_insert_df = pd.DataFrame(fact_rows)
            fact_insert_df["estudiante_id"] = fact_insert_df["rut"].map(rut_to_id)
            fact_insert_df = fact_insert_df.drop(columns=["rut"])
            fact_insert_df = fact_insert_df[["estudiante_id", "actividad_id", "campus_id", "participaciones", "fuente_resumen"]]
            fact_insert_df.to_sql("fact_participacion", conn.connection, if_exists="append", index=False)

            data_frames["REPORTE_CALIDAD"].to_sql("audit_reporte_calidad", conn.connection, if_exists="replace", index=False)
            data_frames["RUT_INVALIDO_CUARENTENA"].to_sql("audit_rut_invalido", conn.connection, if_exists="replace", index=False)

            metadata_rows = [
                {"clave": "generated_from", "valor": excel_path.name},
                {"clave": "generated_at", "valor": datetime.now(timezone.utc).isoformat()},
                {"clave": "pipeline_version", "valor": _git_sha(repo_root)},
                {"clave": "rows_sj", "valor": str(len(data_frames["SAN_JOAQUIN"]))},
                {"clave": "rows_vit", "valor": str(len(data_frames["VITACURA"]))},
                {"clave": "rows_sin_campus", "valor": str(len(data_frames["RUT_SIN_CAMPUS"]))},
            ]
            pd.DataFrame(metadata_rows).to_sql("audit_metadata", conn.connection, if_exists="append", index=False)

            conn.execute(text("CREATE INDEX idx_dim_estudiante_rut ON dim_estudiante(rut)"))
            conn.execute(text("CREATE INDEX idx_fact_participacion_estudiante_id ON fact_participacion(estudiante_id)"))
            conn.execute(text("CREATE INDEX idx_fact_participacion_actividad_id ON fact_participacion(actividad_id)"))
            conn.execute(text("CREATE INDEX idx_fact_participacion_campus_id ON fact_participacion(campus_id)"))

            conn.execute(text("""
                CREATE VIEW vw_resumen_por_campus AS
                SELECT
                    dc.campus_nombre AS campus,
                    da.actividad_codigo,
                    COUNT(DISTINCT de.rut) AS estudiantes_unicos,
                    SUM(fp.participaciones) AS participaciones_totales
                FROM fact_participacion fp
                JOIN dim_estudiante de ON de.estudiante_id = fp.estudiante_id
                JOIN dim_actividad da ON da.actividad_id = fp.actividad_id
                LEFT JOIN dim_campus dc ON dc.campus_id = fp.campus_id
                GROUP BY dc.campus_nombre, da.actividad_codigo
            """))

            conn.execute(text("""
                CREATE VIEW vw_estudiantes_con_apoyos AS
                SELECT
                    de.rut,
                    de.nombre_canonico AS nombre,
                    dc.campus_nombre AS campus,
                    SUM(CASE WHEN da.actividad_codigo = 'CIAC' THEN fp.participaciones ELSE 0 END) AS ciac,
                    SUM(CASE WHEN da.actividad_codigo = 'TALLERES' THEN fp.participaciones ELSE 0 END) AS talleres,
                    SUM(CASE WHEN da.actividad_codigo = 'MENTORIAS' THEN fp.participaciones ELSE 0 END) AS mentorias,
                    SUM(CASE WHEN da.actividad_codigo = 'ATENCIONES' THEN fp.participaciones ELSE 0 END) AS atenciones
                FROM fact_participacion fp
                JOIN dim_estudiante de ON de.estudiante_id = fp.estudiante_id
                JOIN dim_actividad da ON da.actividad_id = fp.actividad_id
                LEFT JOIN dim_campus dc ON dc.campus_id = COALESCE(fp.campus_id, de.campus_id)
                GROUP BY de.rut, de.nombre_canonico, dc.campus_nombre
            """))

        print(f"SQLite generado: {sqlite_path}")
    except Exception as exc:
        raise RuntimeError(f"Error exportando SQLite desde {excel_path} hacia {sqlite_path}: {exc}") from exc
