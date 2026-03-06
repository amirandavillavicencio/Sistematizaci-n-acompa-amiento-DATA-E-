"""Construye el consolidado académico por estudiante para el CRM DATA-E."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
OUTPUT_FILE = DATA_DIR / "apoyos_consolidados.json"

BASE_CAMPUS_FILES = {
    "SAN_JOAQUIN_APOYOS_2025_FINAL.csv": "San Joaquín",
    "VITACURA_APOYOS_2025_FINAL.csv": "Vitacura",
}
SIN_CAMPUS_FILE = "RUT_SIN_CAMPUS.csv"
QUALITY_FILE = "REPORTE_CALIDAD_DATOS.csv"

REQUIRED_COLUMNS = {
    "RUT",
    "Nombre",
    "SRC_CIAC_COUNT",
    "SRC_PI_S1_COUNT",
    "SRC_PI_S2_COUNT",
    "SRC_KATH_TALLER_COUNT",
    "SRC_GLEU_MENT_COUNT",
    "SRC_KATH_ATENC_COUNT",
    "SRC_GLEU_ATENC_COUNT",
    "SRC_FLAGS",
}

SOURCE_LABELS = {
    "SRC_CIAC_COUNT": "CIAC",
    "SRC_PI_S1_COUNT": "TALLER_PI_S1",
    "SRC_PI_S2_COUNT": "TALLER_PI_S2",
    "SRC_KATH_TALLER_COUNT": "KATHERINE_TALLER",
    "SRC_GLEU_MENT_COUNT": "GLEUDYS_MENTORIA",
    "SRC_KATH_ATENC_COUNT": "KATHERINE_ATENCION",
    "SRC_GLEU_ATENC_COUNT": "GLEUDYS_ATENCION",
}


def to_int(value: object) -> int:
    if pd.isna(value):
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def normalize_rut(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().upper().replace(".", "")


def normalize_name(value: object) -> str:
    if pd.isna(value):
        return "Sin nombre"
    clean = str(value).strip()
    if not clean:
        return "Sin nombre"
    return " ".join(token.capitalize() for token in clean.split())


def validate_columns(df: pd.DataFrame, filename: str) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        raise ValueError(f"{filename} no contiene columnas requeridas: {', '.join(missing)}")


def load_quality_map() -> dict[str, dict[str, object]]:
    quality_path = DATA_DIR / QUALITY_FILE
    quality = pd.read_csv(quality_path)
    quality["rut_norm"] = quality.get("rut_norm", "").fillna("").map(normalize_rut)
    quality["issue_type"] = quality.get("issue_type", "SIN_TIPO").fillna("SIN_TIPO").astype(str)
    quality["details"] = quality.get("details", "").fillna("").astype(str)

    grouped = quality[quality["rut_norm"].str.len() > 0].groupby("rut_norm", as_index=True).agg(
        issues_count=("issue_type", "count"),
        issue_types=("issue_type", lambda s: sorted(set(s.tolist()))),
        details=("details", lambda s: " | ".join(item for item in s.tolist() if item)[:450]),
    )

    return grouped.to_dict(orient="index")


def detect_sources(row: pd.Series) -> list[str]:
    sources = [label for column, label in SOURCE_LABELS.items() if to_int(row.get(column, 0)) > 0]

    raw_flags = row.get("SRC_FLAGS", "")
    if pd.notna(raw_flags):
        for raw_flag in str(raw_flags).split("|"):
            clean = raw_flag.strip()
            if clean and clean.lower() != "nan" and clean not in sources:
                sources.append(clean)

    return sorted(set(sources))


def prepare_input_frame(filename: str, campus: str, base: bool) -> pd.DataFrame:
    frame = pd.read_csv(DATA_DIR / filename)
    validate_columns(frame, filename)
    frame["RUT"] = frame["RUT"].map(normalize_rut)
    frame = frame[frame["RUT"].str.len() > 0].copy()
    frame["Nombre"] = frame["Nombre"].map(normalize_name)
    frame["campus"] = campus
    frame["origen_base"] = campus if base else "Sin base campus"
    frame["presencia_lista_base"] = base

    frame["conteo_ciac"] = frame["SRC_CIAC_COUNT"].map(to_int)
    frame["conteo_talleres"] = frame["SRC_PI_S1_COUNT"].map(to_int) + frame["SRC_PI_S2_COUNT"].map(to_int) + frame["SRC_KATH_TALLER_COUNT"].map(to_int)
    frame["conteo_mentorias"] = frame["SRC_GLEU_MENT_COUNT"].map(to_int)
    frame["conteo_atenciones"] = frame["SRC_KATH_ATENC_COUNT"].map(to_int) + frame["SRC_GLEU_ATENC_COUNT"].map(to_int)
    frame["fuentes_detectadas"] = frame.apply(detect_sources, axis=1)
    return frame


def merge_records(frames: list[pd.DataFrame], quality_map: dict[str, dict[str, object]]) -> tuple[list[dict], list[dict], dict[str, int]]:
    joined = pd.concat(frames, ignore_index=True)
    records: list[dict] = []
    sin_campus_records: list[dict] = []
    source_totals = defaultdict(int)

    for idx, (rut, group) in enumerate(joined.groupby("RUT", sort=True), start=1):
        valid_names = [name for name in group["Nombre"].tolist() if name != "Sin nombre"]
        nombre = valid_names[0] if valid_names else "Sin nombre"

        campus_values = sorted(set(group["campus"].tolist()))
        campus = campus_values[0] if len(campus_values) == 1 else "Sin Campus"
        sin_campus = campus == "Sin Campus"

        origen_base_values = sorted(set(group.loc[group["presencia_lista_base"], "origen_base"].tolist()))
        origen_base = origen_base_values[0] if len(origen_base_values) == 1 else ("Multicampus" if origen_base_values else "Sin base campus")

        conteo_ciac = int(group["conteo_ciac"].sum())
        conteo_talleres = int(group["conteo_talleres"].sum())
        conteo_mentorias = int(group["conteo_mentorias"].sum())
        conteo_atenciones = int(group["conteo_atenciones"].sum())

        fuentes = sorted(set(source for row_sources in group["fuentes_detectadas"] for source in row_sources))
        for source in fuentes:
            source_totals[source] += 1

        total_apoyos = conteo_ciac + conteo_talleres + conteo_mentorias + conteo_atenciones
        quality = quality_map.get(rut, {})
        flags = " | ".join(
            flag
            for flag in group["SRC_FLAGS"].fillna("").astype(str).tolist()
            if flag.strip() and flag.strip().lower() != "nan"
        )
        quality_details = str(quality.get("details", "")).strip()
        observacion = " | ".join(part for part in [flags, quality_details] if part)

        record = {
            "id": idx,
            "rut": rut,
            "nombre": nombre,
            "campus": campus,
            "origen_base": origen_base,
            "presencia_lista_base": bool(group["presencia_lista_base"].any()),
            "ciac": conteo_ciac > 0,
            "talleres": conteo_talleres > 0,
            "mentorias": conteo_mentorias > 0,
            "atenciones": conteo_atenciones > 0,
            "conteo_ciac": conteo_ciac,
            "conteo_talleres": conteo_talleres,
            "conteo_mentorias": conteo_mentorias,
            "conteo_atenciones": conteo_atenciones,
            "total_apoyos": total_apoyos,
            "tiene_apoyo": total_apoyos > 0,
            "sin_campus": sin_campus,
            "estado": "Con apoyo" if total_apoyos > 0 else "Sin apoyo",
            "observacion_calidad": observacion,
            "calidad": "Con observaciones" if observacion else "Sin observaciones",
            "fuentes_detectadas": fuentes,
            "issues_count": int(quality.get("issues_count", 0)),
            "issue_types": quality.get("issue_types", []),
        }

        records.append(record)
        if sin_campus:
            sin_campus_records.append(record)

    return records, sin_campus_records, dict(source_totals)


def summarize(records: list[dict], sin_campus: list[dict], quality_map: dict[str, dict[str, object]]) -> dict[str, object]:
    base_sj = sum(1 for row in records if row["origen_base"] == "San Joaquín")
    base_vit = sum(1 for row in records if row["origen_base"] == "Vitacura")
    total = len(records)
    con_apoyo = sum(1 for row in records if row["tiene_apoyo"])

    return {
        "base_san_joaquin": base_sj,
        "base_vitacura": base_vit,
        "total_estudiantes_unicos": total,
        "total_con_apoyo": con_apoyo,
        "total_sin_apoyo": total - con_apoyo,
        "total_participaciones_ciac": sum(row["conteo_ciac"] for row in records),
        "total_participaciones_talleres": sum(row["conteo_talleres"] for row in records),
        "total_participaciones_mentorias": sum(row["conteo_mentorias"] for row in records),
        "total_participaciones_atenciones": sum(row["conteo_atenciones"] for row in records),
        "total_rut_sin_campus": len(sin_campus),
        "porcentaje_estudiantes_con_apoyo": round((con_apoyo / total) * 100, 2) if total else 0,
        "total_issues_calidad": sum(int(item.get("issues_count", 0)) for item in quality_map.values()),
    }


def main() -> None:
    quality_map = load_quality_map()

    frames = [prepare_input_frame(filename, campus, base=True) for filename, campus in BASE_CAMPUS_FILES.items()]
    frames.append(prepare_input_frame(SIN_CAMPUS_FILE, "Sin Campus", base=False))

    records, sin_campus_records, source_totals = merge_records(frames, quality_map)

    payload = {
        "meta": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "record_count": len(records),
            "note": "Consolidación institucional por estudiante usando listas base por campus y fuentes complementarias en columnas SRC_*. Microgrupo excluido.",
            "source_files": list(BASE_CAMPUS_FILES.keys()) + [SIN_CAMPUS_FILE, QUALITY_FILE, "DATEapoyosFInal.xlsx"],
            "field_semantics": {
                "conteo_ciac": "Conteo de participaciones desde registro CIAC",
                "conteo_talleres": "Conteo agregado Katherine + Proyecto Inicial S1/S2",
                "conteo_mentorias": "Conteo desde Gleudys mentorías",
                "conteo_atenciones": "Conteo agregado Katherine + Gleudys atenciones",
                "ciac/talleres/mentorias/atenciones": "Banderas booleanas derivadas de conteos > 0",
            },
        },
        "summary": summarize(records, sin_campus_records, quality_map),
        "quality_summary": {
            "total_rut_con_issues": len(quality_map),
            "issue_types": pd.read_csv(DATA_DIR / QUALITY_FILE)["issue_type"].fillna("SIN_TIPO").value_counts().to_dict(),
        },
        "source_coverage": source_totals,
        "records": records,
        "rut_sin_campus": sin_campus_records,
    }

    OUTPUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Consolidado generado en {OUTPUT_FILE} ({len(records)} estudiantes).")


if __name__ == "__main__":
    main()
