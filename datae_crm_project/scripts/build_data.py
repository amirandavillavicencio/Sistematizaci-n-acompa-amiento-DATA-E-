"""Genera `data/apoyos_consolidados.json` para el CRM académico estático."""

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


def safe_int(value: object) -> int:
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
    cleaned = str(value).strip()
    return cleaned.title() if cleaned else "Sin nombre"


def validate_columns(dataframe: pd.DataFrame, filename: str) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(dataframe.columns))
    if missing:
        cols = ", ".join(missing)
        raise ValueError(f"El archivo {filename} no contiene columnas requeridas: {cols}")


def load_quality_issues() -> pd.DataFrame:
    file_path = DATA_DIR / "REPORTE_CALIDAD_DATOS.csv"
    quality = pd.read_csv(file_path)
    quality["rut_norm"] = quality.get("rut_norm", "").fillna("").astype(str).str.upper().str.replace(".", "", regex=False).str.strip()
    quality["issue_type"] = quality.get("issue_type", "SIN_TIPO").fillna("SIN_TIPO").astype(str)
    quality["details"] = quality.get("details", "").fillna("").astype(str)
    return quality


def build_base_rows() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for filename, campus in SOURCE_CAMPUS_FILES.items():
        file_path = DATA_DIR / filename
        frame = pd.read_csv(file_path)
        validate_columns(frame, filename)
        frame["campus_origen"] = campus
        frames.append(frame)

    base = pd.concat(frames, ignore_index=True)
    base["RUT"] = base["RUT"].apply(normalize_rut)
    base = base[base["RUT"].str.len() > 0].copy()
    base["Nombre"] = base["Nombre"].apply(normalize_name)

    base["ciac"] = base["SRC_CIAC_COUNT"].apply(safe_int)
    base["talleres"] = base["SRC_PI_S1_COUNT"].apply(safe_int) + base["SRC_PI_S2_COUNT"].apply(safe_int) + base["SRC_KATH_TALLER_COUNT"].apply(safe_int)
    base["mentorias"] = base["SRC_GLEU_MENT_COUNT"].apply(safe_int)
    base["atenciones"] = base["SRC_KATH_ATENC_COUNT"].apply(safe_int) + base["SRC_GLEU_ATENC_COUNT"].apply(safe_int)

    return base


def consolidate(base: pd.DataFrame, quality: pd.DataFrame) -> list[dict]:
    quality_map = quality.groupby("rut_norm", as_index=True).agg(
        issues_count=("issue_type", "count"),
        issue_types=("issue_type", lambda series: sorted(set(series.dropna().astype(str)))),
        details=("details", lambda series: " | ".join(series.dropna().astype(str))[:350]),
    )

    records: list[dict] = []

    for index, (rut, group) in enumerate(base.groupby("RUT", sort=True), start=1):
        campuses = sorted(set(group["campus_origen"].dropna().astype(str)))
        valid_campuses = [campus for campus in campuses if campus != "Sin Campus"]

        if len(valid_campuses) > 1:
            campus = "Multicampus"
        elif len(valid_campuses) == 1:
            campus = valid_campuses[0]
        else:
            campus = "Sin Campus"

        ciac = int(group["ciac"].sum())
        talleres = int(group["talleres"].sum())
        mentorias = int(group["mentorias"].sum())
        atenciones = int(group["atenciones"].sum())
        total = ciac + talleres + mentorias + atenciones

        quality_issues = quality_map.loc[rut] if rut in quality_map.index else None
        issues_count = int(quality_issues["issues_count"]) if quality_issues is not None else 0
        issue_types = list(quality_issues["issue_types"]) if quality_issues is not None else []
        issue_details = str(quality_issues["details"]) if quality_issues is not None else ""

        flags = " | ".join(str(flag) for flag in group["SRC_FLAGS"].dropna().unique() if str(flag).strip())
        observations = " | ".join(item for item in [flags, issue_details] if item)

        non_empty_names = group["Nombre"].replace("Sin nombre", pd.NA).dropna()
        student_name = non_empty_names.iloc[0] if not non_empty_names.empty else "Sin nombre"

        records.append(
            {
                "id": index,
                "rut": rut,
                "nombre": student_name,
                "campus": campus,
                "tiene_campus": campus != "Sin Campus",
                "ciac": ciac,
                "talleres": talleres,
                "mentorias": mentorias,
                "atenciones": atenciones,
                "total_apoyos": total,
                "estado": "Con apoyo" if total > 0 else "Sin apoyo",
                "calidad": "Con observaciones" if observations else "Sin observaciones",
                "observaciones": observations,
                "issues_count": issues_count,
                "issue_types": issue_types,
            }
        )

    return records


def main() -> None:
    base = build_base_rows()
    quality = load_quality_issues()
    records = consolidate(base, quality)

    payload = {
        "meta": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "source_files": list(SOURCE_CAMPUS_FILES) + ["REPORTE_CALIDAD_DATOS.csv", "RESUMEN_DATAE_2025.csv", "DATEapoyosFInal.xlsx"],
            "record_count": len(records),
            "note": "Consolidación por RUT desde CSV de campus y reporte de calidad.",
        },
        "quality_summary": {
            "total_issues": int(quality.shape[0]),
            "issue_types": quality["issue_type"].value_counts().to_dict(),
        },
        "records": records,
    }

    OUTPUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JSON consolidado generado: {OUTPUT_FILE} ({len(records)} registros)")


if __name__ == "__main__":
    main()
