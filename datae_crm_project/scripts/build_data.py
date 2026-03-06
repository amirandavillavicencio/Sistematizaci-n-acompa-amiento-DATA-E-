"""Genera data/apoyos_consolidados.json para el CRM estático."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
OUTPUT_FILE = DATA_DIR / "apoyos_consolidados.json"

SOURCE_CAMPUS_FILES = {
    "SAN_JOAQUIN_APOYOS_2025_FINAL.csv": "San Joaquín",
    "VITACURA_APOYOS_2025_FINAL.csv": "Vitacura",
    "RUT_SIN_CAMPUS.csv": "Sin Campus",
}


def safe_int(value) -> int:
    if pd.isna(value):
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def normalize_rut(value: str | float) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().upper()


def normalize_name(value: str | float) -> str:
    if pd.isna(value) or not str(value).strip():
        return "Sin nombre"
    return str(value).strip().title()


def load_quality_issues() -> pd.DataFrame:
    quality_file = DATA_DIR / "REPORTE_CALIDAD_DATOS.csv"
    quality_df = pd.read_csv(quality_file)
    quality_df["rut_norm"] = quality_df["rut_norm"].fillna("").astype(str).str.strip().str.upper()
    return quality_df


def build_base_rows() -> pd.DataFrame:
    frames = []
    for filename, campus in SOURCE_CAMPUS_FILES.items():
        file_path = DATA_DIR / filename
        df = pd.read_csv(file_path)
        df["campus_origen"] = campus
        frames.append(df)

    base = pd.concat(frames, ignore_index=True)
    base["RUT"] = base["RUT"].apply(normalize_rut)
    base["Nombre"] = base["Nombre"].apply(normalize_name)

    base["ciac"] = base["SRC_CIAC_COUNT"].apply(safe_int)
    base["talleres"] = (
        base["SRC_PI_S1_COUNT"].apply(safe_int)
        + base["SRC_PI_S2_COUNT"].apply(safe_int)
        + base["SRC_KATH_TALLER_COUNT"].apply(safe_int)
    )
    base["mentorias"] = base["SRC_GLEU_MENT_COUNT"].apply(safe_int)
    base["atenciones"] = base["SRC_KATH_ATENC_COUNT"].apply(safe_int) + base["SRC_GLEU_ATENC_COUNT"].apply(safe_int)

    base["campus_limpio"] = base["campus_origen"].replace({"": "Sin Campus"})
    base["tiene_campus"] = base["campus_limpio"].ne("Sin Campus")
    return base


def consolidate(base: pd.DataFrame, quality_df: pd.DataFrame) -> list[dict]:
    quality_map = quality_df.groupby("rut_norm").agg(
        issues_count=("issue_type", "count"),
        issue_types=("issue_type", lambda items: sorted(set(str(i) for i in items if pd.notna(i)))),
        details=("details", lambda items: " | ".join(str(i) for i in items if pd.notna(i))[:300]),
    )

    records: list[dict] = []

    for index, (rut, group) in enumerate(base.groupby("RUT", sort=True), start=1):
        campus_values = sorted(set(group["campus_limpio"].dropna().astype(str)))
        campus_no_missing = [c for c in campus_values if c != "Sin Campus"]
        if len(campus_no_missing) > 1:
            campus = "Multicampus"
        elif len(campus_no_missing) == 1:
            campus = campus_no_missing[0]
        else:
            campus = "Sin Campus"

        issues_count = 0
        issue_types = []
        issue_details = ""
        if rut in quality_map.index:
            issues_count = int(quality_map.loc[rut, "issues_count"])
            issue_types = quality_map.loc[rut, "issue_types"]
            issue_details = quality_map.loc[rut, "details"]

        ciac = int(group["ciac"].sum())
        talleres = int(group["talleres"].sum())
        mentorias = int(group["mentorias"].sum())
        atenciones = int(group["atenciones"].sum())
        total = ciac + talleres + mentorias + atenciones

        raw_flags = " | ".join(str(v) for v in group["SRC_FLAGS"].dropna().unique())
        observation_parts = [p for p in [raw_flags, issue_details] if p]

        records.append(
            {
                "id": index,
                "rut": rut,
                "nombre": group["Nombre"].replace("Sin nombre", pd.NA).dropna().iloc[0] if not group["Nombre"].replace("Sin nombre", pd.NA).dropna().empty else "Sin nombre",
                "campus": campus,
                "tiene_campus": campus != "Sin Campus",
                "ciac": ciac,
                "talleres": talleres,
                "mentorias": mentorias,
                "atenciones": atenciones,
                "total_apoyos": total,
                "estado": "Con apoyo" if total > 0 else "Sin apoyo",
                "calidad": "Con observaciones" if (issues_count > 0 or raw_flags) else "Sin observaciones",
                "observaciones": " | ".join(observation_parts),
                "issues_count": issues_count,
                "issue_types": issue_types,
            }
        )

    return records


def main() -> None:
    base = build_base_rows()
    quality_df = load_quality_issues()
    records = consolidate(base, quality_df)

    payload = {
        "meta": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "source_files": list(SOURCE_CAMPUS_FILES.keys()) + ["REPORTE_CALIDAD_DATOS.csv", "RESUMEN_DATAE_2025.csv", "DATEapoyosFInal.xlsx"],
            "record_count": len(records),
            "note": "Consolidación por RUT usando CSV campus + reporte de calidad.",
        },
        "quality_summary": {
            "total_issues": int(quality_df.shape[0]),
            "issue_types": quality_df["issue_type"].fillna("SIN_TIPO").value_counts().to_dict(),
        },
        "records": records,
    }

    OUTPUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JSON consolidado generado: {OUTPUT_FILE} ({len(records)} registros)")


if __name__ == "__main__":
    main()
