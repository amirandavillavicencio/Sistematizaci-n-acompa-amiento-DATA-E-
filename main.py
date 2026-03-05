from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from dataclasses import dataclass, asdict
from unicodedata import normalize as unicode_normalize

import pandas as pd


# =========================
# Config
# =========================

SUPPORTED_EXT = {".xlsx", ".xls", ".csv"}
REQUIRED_FILES = {"main.py", "requirements.txt"}
REQUIRED_DIRS = {"data", "output"}

ACT_CIAC = "CIAC"
ACT_TALLER = "TALLER"
ACT_MENTORIA = "MENTORIA"
ACT_ATENCION = "ATENCION"


# =========================
# RUT: Normalización + Validación
# =========================

RUT_RE = re.compile(r"^\d{7,8}-[0-9K]$")
RUT_FINAL_RE = re.compile(r"^\d{8}-[0-9K]$")
FINAL_REQUIRED_COLUMNS = [
    "RUT",
    "Nombre",
    "Apoyo_Academico_CIAC",
    "Talleres",
    "Mentorias",
    "Atenciones_Individuales",
]


def normalize_rut(value) -> str:
    """
    Normaliza RUT a ########-X

    Reglas:
      - elimina puntos
      - elimina espacios
      - DV en mayúscula
      - mantiene / asegura guión antes del DV

    Nota:
      - Si viene sin guión pero termina en [0-9K], asume último char como DV:
        '214563211' -> '21456321-1'
      - Si viene solo cuerpo sin DV (ej: '21456321'), retorna solo dígitos
        para que sea marcado como inválido luego (no inventa DV).
    """
    if value is None:
        return ""
    s = str(value).strip()
    if s == "" or s.lower() in {"nan", "none", "null"}:
        return ""

    s = s.replace(".", "")
    s = re.sub(r"\s+", "", s)
    s = s.upper()
    s = re.sub(r"[^0-9K-]", "", s)

    if "-" in s:
        parts = s.split("-")
        cuerpo = "".join(parts[:-1])
        dv = parts[-1]
        cuerpo = re.sub(r"[^0-9]", "", cuerpo)
        dv = re.sub(r"[^0-9K]", "", dv)
        if cuerpo and dv:
            return f"{cuerpo}-{dv}"
        if cuerpo:
            return cuerpo
        return ""

    if len(s) >= 2 and re.fullmatch(r"[0-9]+[0-9K]", s):
        cuerpo, dv = s[:-1], s[-1]
        if cuerpo:
            return f"{cuerpo}-{dv}"

    return re.sub(r"[^0-9]", "", s)


def _dv_expected(cuerpo: str) -> str:
    reversed_digits = list(map(int, reversed(cuerpo)))
    factors = [2, 3, 4, 5, 6, 7]
    s = 0
    for i, d in enumerate(reversed_digits):
        s += d * factors[i % len(factors)]
    mod = 11 - (s % 11)
    if mod == 11:
        return "0"
    if mod == 10:
        return "K"
    return str(mod)


def is_valid_rut(rut_norm: str) -> bool:
    if not rut_norm or not RUT_RE.fullmatch(rut_norm):
        return False
    cuerpo, dv = rut_norm.split("-")
    if not (7 <= len(cuerpo) <= 8) or not cuerpo.isdigit():
        return False
    return _dv_expected(cuerpo) == dv


def format_full_name(ap1: str | None, ap2: str | None, nombres: str | None) -> str:
    parts = []
    for p in (nombres, ap1, ap2):
        if p is None:
            continue
        p = str(p).strip()
        if p and p.lower() not in {"nan", "none", "null"}:
            parts.append(p)
    return " ".join(parts).strip()


# =========================
# QA / Reporte Calidad
# =========================

@dataclass(frozen=True)
class RutIssue:
    issue_type: str
    file: str
    sheet: str
    row: int
    rut_raw: str
    rut_norm: str
    name_raw: str
    details: str


# =========================
# IO: Lectura de archivos
# =========================

def list_data_files(data_dir: Path) -> list[Path]:
    return sorted([p for p in data_dir.glob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXT])


def verify_repo_structure(repo_root: Path) -> None:
    data_dir = repo_root / "data"
    out_dir = repo_root / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    missing_files = sorted([f for f in REQUIRED_FILES if not (repo_root / f).is_file()])
    missing_dirs = sorted([d for d in REQUIRED_DIRS if not (repo_root / d).is_dir()])
    if missing_files or missing_dirs:
        problems = []
        if missing_dirs:
            problems.append(f"directorios faltantes: {', '.join(missing_dirs)}")
        if missing_files:
            problems.append(f"archivos faltantes: {', '.join(missing_files)}")
        raise SystemExit("Estructura de repositorio incompleta: " + " | ".join(problems))

    files = list_data_files(data_dir)
    if not files:
        raise SystemExit(f"No se encontraron archivos Excel/CSV en {data_dir}.")


def read_file_all_sheets(path: Path) -> dict[str, pd.DataFrame]:
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path, dtype=str, keep_default_na=False).fillna("")
        return {"CSV": df}
    xls = pd.read_excel(path, sheet_name=None, dtype=str)
    for k, df in xls.items():
        xls[k] = df.fillna("")
    return xls


# =========================
# Detectores / Extractores
# =========================

def _detect_source(path: Path) -> str:
    name = path.name.lower()
    if "san joaquin apoyos" in name or ("apoyos" in name and "san" in name and "joaquin" in name):
        return "BASE_SJ"
    if "vitacura apoyos" in name or ("apoyos" in name and "vitacura" in name):
        return "BASE_VIT"
    if "katherine" in name:
        return "KATHERINE"
    if "gleudys" in name:
        return "GLEUDYS"
    if "asistencia" in name and "taller" in name:
        return "TALLERES_PI"
    if "ciac" in name and "vitacura" in name:
        return "CIAC_VIT"
    if "ciac" in name and ("san joaquin" in name or "san joaqu" in name):
        return "CIAC_SJ"
    return "UNKNOWN"


def _col(df: pd.DataFrame, *candidates: str) -> str | None:
    cols = {_norm_col_name(c): c for c in df.columns}
    for cand in candidates:
        key = _norm_col_name(cand)
        if key in cols:
            return cols[key]
    return None


def _find_col_contains(df: pd.DataFrame, needle: str) -> str | None:
    needle = _norm_col_name(needle)
    for c in df.columns:
        if needle in _norm_col_name(c):
            return c
    return None


def _norm_col_name(value: str) -> str:
    txt = str(value).strip().lower()
    txt = unicode_normalize("NFKD", txt).encode("ascii", "ignore").decode("ascii")
    txt = re.sub(r"[^a-z0-9]+", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def _find_col_by_tokens(df: pd.DataFrame, groups: list[set[str]]) -> str | None:
    """
    Busca una columna donde cada grupo de tokens tenga al menos una coincidencia.
    Ejemplo groups=[{"apellido"},{"paterno","1"}] detecta "Apellido Paterno" o "Apellido 1".
    """
    for c in df.columns:
        norm = _norm_col_name(c)
        tokens = set(norm.split())
        if all(any(g in tokens for g in group) for group in groups):
            return c
    return None


def _detect_rut_and_dv_cols(df: pd.DataFrame) -> tuple[str | None, str | None]:
    rut_col = (
        _col(df, "Rut", "RUT", "RUN", "R.U.N", "R.U.T")
        or _find_col_by_tokens(df, [{"rut", "run"}])
        or _find_col_contains(df, "rut")
        or _find_col_contains(df, "run")
    )
    dv_col = (
        _col(df, "DV", "Dígito Verificador", "Digito Verificador", "D.V")
        or _find_col_by_tokens(df, [{"digito", "dv"}, {"verificador", "v"}])
        or _find_col_contains(df, "digito verificador")
        or _find_col_contains(df, "dv")
    )
    return rut_col, dv_col


def _detect_name_cols(df: pd.DataFrame) -> tuple[str | None, str | None, str | None]:
    ap1 = (
        _col(df, "Apellido 1", "Apellido1", "Apellido P", "Apellido Paterno")
        or _find_col_by_tokens(df, [{"apellido"}, {"paterno", "1", "p"}])
    )
    ap2 = (
        _col(df, "Apellido 2", "Apellido2", "Apellido M", "Apellido Materno")
        or _find_col_by_tokens(df, [{"apellido"}, {"materno", "2", "m"}])
    )
    nom = (
        _col(df, "Nombres", "Nombre", "NOMBRE")
        or _find_col_by_tokens(df, [{"nombre", "nombres"}])
        or _find_col_contains(df, "nombre")
    )
    return ap1, ap2, nom


def extract_base_campus(df: pd.DataFrame, campus: str, source_file: str, source_sheet: str) -> pd.DataFrame:
    rut_col, dv_col = _detect_rut_and_dv_cols(df)
    ap1, ap2, nom = _detect_name_cols(df)

    rut_raw = df[rut_col].astype(str) if rut_col else pd.Series([""] * len(df))
    if dv_col:
        rut_raw = rut_raw.astype(str) + "-" + df[dv_col].astype(str)

    out = pd.DataFrame()
    out["RUT_RAW"] = rut_raw.astype(str)
    out["RUT_NORM"] = out["RUT_RAW"].apply(normalize_rut)

    if nom and (ap1 or ap2):
        out["Nombre"] = [
            format_full_name(df.at[i, ap1] if ap1 else "", df.at[i, ap2] if ap2 else "", df.at[i, nom] if nom else "")
            for i in range(len(df))
        ]
    elif nom:
        out["Nombre"] = df[nom].astype(str).str.strip()
    else:
        out["Nombre"] = ""

    out["Campus"] = campus
    out["FuenteArchivo"] = source_file
    out["FuenteHoja"] = source_sheet
    return out[["RUT_NORM", "Nombre", "Campus", "FuenteArchivo", "FuenteHoja"]]


def extract_activity_rows(source: str, df: pd.DataFrame, sheet_name: str, file_name: str) -> pd.DataFrame:
    """
    Devuelve filas estandarizadas:
      RUT_RAW, RUT_NORM, Nombre, Actividad, Participaciones, FuenteArchivo, FuenteHoja, Fila
    """
    rows = []

    if source == "TALLERES_PI":
        rut_col, _ = _detect_rut_and_dv_cols(df)
        ap, am, nom = _detect_name_cols(df)
        if rut_col:
            for i in range(len(df)):
                rut_raw = df.at[i, rut_col]
                rut_norm = normalize_rut(rut_raw)
                name = format_full_name(df.at[i, ap] if ap else "", df.at[i, am] if am else "", df.at[i, nom] if nom else "")
                rows.append((rut_raw, rut_norm, name, ACT_TALLER, 1, file_name, sheet_name, i))

    elif source == "CIAC_SJ":
        rut_col, _ = _detect_rut_and_dv_cols(df)
        if rut_col:
            for i in range(len(df)):
                rut_raw = df.at[i, rut_col]
                rut_norm = normalize_rut(rut_raw)
                rows.append((rut_raw, rut_norm, "", ACT_CIAC, 1, file_name, sheet_name, i))

    elif source == "CIAC_VIT":
        run_col, dv_col = _detect_rut_and_dv_cols(df)
        if run_col:
            for i in range(len(df)):
                run_raw = str(df.at[i, run_col]).strip()
                dv_raw = str(df.at[i, dv_col]).strip() if dv_col else ""
                rut_raw = f"{run_raw}-{dv_raw}" if dv_raw else run_raw
                rut_norm = normalize_rut(rut_raw)
                rows.append((rut_raw, rut_norm, "", ACT_CIAC, 1, file_name, sheet_name, i))

    elif source == "KATHERINE":
        cols = [c.lower() for c in df.columns]
        if "total de sesiones" in cols or any("total" in c and "sesion" in c for c in cols):
            rut_col, dv_col = _detect_rut_and_dv_cols(df)
            tot_col = _col(df, "Total de sesiones") or _find_col_contains(df, "total de sesiones") or _find_col_contains(df, "sesiones")
            ap1, ap2, nom = _detect_name_cols(df)

            for i in range(len(df)):
                r = str(df.at[i, rut_col]) if rut_col else ""
                dv = str(df.at[i, dv_col]) if dv_col else ""
                rut_raw = f"{r}-{dv}" if dv else r
                rut_norm = normalize_rut(rut_raw)
                name = format_full_name(df.at[i, ap1] if ap1 else "", df.at[i, ap2] if ap2 else "", df.at[i, nom] if nom else "")
                try:
                    n = int(str(df.at[i, tot_col]).strip()) if tot_col else 1
                except Exception:
                    n = 1
                n = max(1, n)
                rows.append((rut_raw, rut_norm, name, ACT_ATENCION, n, file_name, sheet_name, i))
        else:
            rut_col, _ = _detect_rut_and_dv_cols(df)
            _, _, nom_col = _detect_name_cols(df)
            if rut_col:
                for i in range(len(df)):
                    rut_raw = df.at[i, rut_col]
                    rut_norm = normalize_rut(rut_raw)
                    name = str(df.at[i, nom_col]).strip() if nom_col else ""
                    rows.append((rut_raw, rut_norm, name, ACT_TALLER, 1, file_name, sheet_name, i))

    elif source == "GLEUDYS":
        rut_col, _ = _detect_rut_and_dv_cols(df)
        if rut_col:
            ap, am, nom = _detect_name_cols(df)

            sname = sheet_name.lower()
            if "micro" in sname:
                act = ACT_MENTORIA
            elif "apoyo" in sname:
                act = ACT_CIAC
            elif "mentor" in sname:
                act = ACT_MENTORIA
            elif "taller" in sname:
                act = ACT_TALLER
            elif "atenc" in sname:
                act = ACT_ATENCION
            else:
                act = ACT_MENTORIA

            for i in range(len(df)):
                rut_raw = df.at[i, rut_col]
                rut_norm = normalize_rut(rut_raw)
                name = format_full_name(df.at[i, ap] if ap else "", df.at[i, am] if am else "", df.at[i, nom] if nom else "")
                rows.append((rut_raw, rut_norm, name, act, 1, file_name, sheet_name, i))

    if not rows:
        return pd.DataFrame(columns=["RUT_RAW","RUT_NORM","Nombre","Actividad","Participaciones","FuenteArchivo","FuenteHoja","Fila"])

    return pd.DataFrame(rows, columns=["RUT_RAW","RUT_NORM","Nombre","Actividad","Participaciones","FuenteArchivo","FuenteHoja","Fila"])


# =========================
# Consolidación
# =========================

def aggregate_activities(activity_df: pd.DataFrame) -> pd.DataFrame:
    if activity_df.empty:
        return pd.DataFrame(columns=["RUT_NORM","Nombre_best","CIAC_count","TALLER_count","MENTORIA_count","ATENCION_count"])

    tmp = activity_df.copy()
    tmp["Nombre"] = tmp["Nombre"].astype(str).str.strip()

    non_empty = tmp[tmp["Nombre"] != ""]
    if non_empty.empty:
        name_best = pd.DataFrame({"RUT_NORM": tmp["RUT_NORM"].unique(), "Nombre_best": ""})
    else:
        name_best = (non_empty.groupby(["RUT_NORM","Nombre"]).size()
                     .reset_index(name="n")
                     .sort_values(["RUT_NORM","n"], ascending=[True, False])
                     .drop_duplicates("RUT_NORM")[["RUT_NORM","Nombre"]]
                     .rename(columns={"Nombre":"Nombre_best"}))

    pivot = (tmp.groupby(["RUT_NORM","Actividad"])["Participaciones"].sum()
             .reset_index()
             .pivot(index="RUT_NORM", columns="Actividad", values="Participaciones")
             .fillna(0)
             .reset_index())

    for c in [ACT_CIAC, ACT_TALLER, ACT_MENTORIA, ACT_ATENCION]:
        if c not in pivot.columns:
            pivot[c] = 0

    out = pivot.merge(name_best, on="RUT_NORM", how="left")
    out["Nombre_best"] = out["Nombre_best"].fillna("")
    out = out.rename(columns={
        ACT_CIAC: "CIAC_count",
        ACT_TALLER: "TALLER_count",
        ACT_MENTORIA: "MENTORIA_count",
        ACT_ATENCION: "ATENCION_count",
    })
    return out[["RUT_NORM","Nombre_best","CIAC_count","TALLER_count","MENTORIA_count","ATENCION_count"]]


def _mark(count: int) -> str:
    try:
        c = int(count)
    except Exception:
        c = 0
    if c <= 0:
        return ""
    return "X" if c == 1 else str(c)


def _activity_to_int(value) -> int:
    if value is None:
        return 0
    txt = str(value).strip()
    if txt == "" or txt.lower() in {"nan", "none", "null"}:
        return 0
    if txt.upper() == "X":
        return 1
    if re.fullmatch(r"\d+", txt):
        return int(txt)
    return 0


def build_final_for_campus(base: pd.DataFrame, agg: pd.DataFrame) -> pd.DataFrame:
    out = base.merge(agg, on="RUT_NORM", how="left")
    if "Nombre_best" not in out.columns:
        out["Nombre_best"] = ""
    out["Nombre_best"] = out["Nombre_best"].fillna("")
    out["Nombre"] = out["Nombre"].astype(str).str.strip()
    out["Nombre_final"] = out["Nombre"]
    mask = (out["Nombre_final"] == "") & (out["Nombre_best"].astype(str).str.strip() != "")
    out.loc[mask, "Nombre_final"] = out.loc[mask, "Nombre_best"]

    for c in ["CIAC_count","TALLER_count","MENTORIA_count","ATENCION_count"]:
        if c not in out.columns:
            out[c] = 0
        out[c] = out[c].fillna(0).astype(int)

    return pd.DataFrame({
        "RUT": out["RUT_NORM"],
        "Nombre": out["Nombre_final"].astype(str).str.strip(),
        "Apoyo_Academico_CIAC": out["CIAC_count"].apply(_mark),
        "Talleres": out["TALLER_count"].apply(_mark),
        "Mentorias": out["MENTORIA_count"].apply(_mark),
        "Atenciones_Individuales": out["ATENCION_count"].apply(_mark),
    })


def build_rut_sin_campus(base_sj: pd.DataFrame, base_vit: pd.DataFrame, agg: pd.DataFrame) -> pd.DataFrame:
    base_all = pd.concat([base_sj[["RUT_NORM"]], base_vit[["RUT_NORM"]]], ignore_index=True).drop_duplicates()
    merged = agg.merge(base_all, on="RUT_NORM", how="left", indicator=True)
    sin = merged[merged["_merge"] == "left_only"].copy()

    out = pd.DataFrame({
        "RUT": sin["RUT_NORM"],
        "Nombre": sin["Nombre_best"].astype(str).str.strip(),
        "Apoyo_Academico_CIAC": sin["CIAC_count"].apply(_mark),
        "Talleres": sin["TALLER_count"].apply(_mark),
        "Mentorias": sin["MENTORIA_count"].apply(_mark),
        "Atenciones_Individuales": sin["ATENCION_count"].apply(_mark),
    })
    return out.sort_values("RUT")


def validate_and_prepare_outputs(final_sj: pd.DataFrame, final_vit: pd.DataFrame, sin: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[dict[str, str]]]:
    errors: list[str] = []
    report_rows: list[dict[str, str]] = []

    for campus, df in [("SAN_JOAQUIN", final_sj), ("VITACURA", final_vit)]:
        missing_cols = [c for c in FINAL_REQUIRED_COLUMNS if c not in df.columns]
        if missing_cols:
            errors.append(f"{campus}: faltan columnas requeridas: {', '.join(missing_cols)}")
            report_rows.append({"tipo": "COLUMNAS_FALTANTES", "archivo": f"{campus}_FINAL", "detalle": ", ".join(missing_cols)})
            continue

        invalid_rut = df[(df["RUT"].astype(str).str.strip() != "") & (~df["RUT"].astype(str).str.strip().str.upper().str.match(RUT_FINAL_RE))]
        if not invalid_rut.empty:
            sample = ", ".join(invalid_rut["RUT"].astype(str).head(5).tolist())
            errors.append(f"{campus}: RUT inválidos en archivo final (formato ########-X). Ejemplos: {sample}")
            report_rows.append({"tipo": "RUT_FORMATO_INVALIDO", "archivo": f"{campus}_FINAL", "detalle": sample})

        dup = df[df["RUT"].astype(str).str.strip() != ""].duplicated("RUT", keep=False)
        if dup.any():
            dup_sample = ", ".join(df.loc[dup, "RUT"].astype(str).drop_duplicates().head(5).tolist())
            errors.append(f"{campus}: existen RUT duplicados en archivo final. Ejemplos: {dup_sample}")
            report_rows.append({"tipo": "RUT_DUPLICADO_FINAL", "archivo": f"{campus}_FINAL", "detalle": dup_sample})

    sin_clean = sin.copy()
    dup_mask = sin_clean["RUT"].astype(str).str.strip() != ""
    dup_mask = dup_mask & sin_clean.duplicated("RUT", keep="first")
    dup_count = int(dup_mask.sum())
    if dup_count > 0:
        sample = ", ".join(sin_clean.loc[dup_mask, "RUT"].astype(str).head(5).tolist())
        report_rows.append({
            "tipo": "RUT_SIN_CAMPUS_DUPLICADOS_DEPURADOS",
            "archivo": "RUT_SIN_CAMPUS",
            "detalle": f"Eliminados {dup_count} duplicados. Ejemplos: {sample}",
        })
        sin_clean = sin_clean.drop_duplicates(subset=["RUT"], keep="first")

    return sin_clean, errors, report_rows


def build_resumen(final_sj: pd.DataFrame, final_vit: pd.DataFrame) -> pd.DataFrame:
    def metrics(campus: str, df: pd.DataFrame) -> dict[str, int | str]:
        return {
            "Campus": campus,
            "total_estudiantes_unicos": int(df["RUT"].astype(str).str.strip().replace("", pd.NA).dropna().nunique()),
            "total_ciac": int(df["Apoyo_Academico_CIAC"].apply(_activity_to_int).sum()),
            "total_talleres": int(df["Talleres"].apply(_activity_to_int).sum()),
            "total_mentorias": int(df["Mentorias"].apply(_activity_to_int).sum()),
            "total_atenciones": int(df["Atenciones_Individuales"].apply(_activity_to_int).sum()),
        }

    row_sj = metrics("SAN_JOAQUIN", final_sj)
    row_vit = metrics("VITACURA", final_vit)

    both = pd.concat([final_sj, final_vit], ignore_index=True)
    row_total = metrics("TOTAL", both)

    return pd.DataFrame([row_sj, row_vit, row_total])


def export_outputs_to_sqlite(out_dir: Path) -> None:
    db_path = out_dir / "datae_apoyos_2025.db"
    table_sources = {
        "san_joaquin_apoyos": out_dir / "SAN_JOAQUIN_APOYOS_2025_FINAL.csv",
        "vitacura_apoyos": out_dir / "VITACURA_APOYOS_2025_FINAL.csv",
        "rut_sin_campus": out_dir / "RUT_SIN_CAMPUS.csv",
        "reporte_calidad": out_dir / "REPORTE_CALIDAD_DATOS.csv",
    }

    with sqlite3.connect(db_path) as conn:
        for table_name, csv_path in table_sources.items():
            df = pd.read_csv(csv_path, dtype=str, keep_default_na=False).fillna("")
            df.to_sql(table_name, conn, if_exists="replace", index=False)


def _auto_adjust_worksheet(worksheet) -> None:
    worksheet.freeze_panes = "A2"
    for column_cells in worksheet.columns:
        header = str(column_cells[0].value or "")
        max_length = len(header)
        for cell in column_cells[1:]:
            value = "" if cell.value is None else str(cell.value)
            if len(value) > max_length:
                max_length = len(value)
        worksheet.column_dimensions[column_cells[0].column_letter].width = max_length + 2


def export_excel_report(out_dir: Path, final_sj: pd.DataFrame, final_vit: pd.DataFrame) -> None:
    def metric_sum(df: pd.DataFrame, col: str) -> int:
        return int(df[col].apply(_activity_to_int).sum())

    resumen_general = pd.DataFrame([
        {
            "Indicador": "Estudiantes_unicos",
            "San_Joaquin": int(final_sj["RUT"].astype(str).str.strip().replace("", pd.NA).dropna().nunique()),
            "Vitacura": int(final_vit["RUT"].astype(str).str.strip().replace("", pd.NA).dropna().nunique()),
        },
        {
            "Indicador": "Apoyo_CIAC",
            "San_Joaquin": metric_sum(final_sj, "Apoyo_Academico_CIAC"),
            "Vitacura": metric_sum(final_vit, "Apoyo_Academico_CIAC"),
        },
        {
            "Indicador": "Talleres",
            "San_Joaquin": metric_sum(final_sj, "Talleres"),
            "Vitacura": metric_sum(final_vit, "Talleres"),
        },
        {
            "Indicador": "Mentorias",
            "San_Joaquin": metric_sum(final_sj, "Mentorias"),
            "Vitacura": metric_sum(final_vit, "Mentorias"),
        },
        {
            "Indicador": "Atenciones_Individuales",
            "San_Joaquin": metric_sum(final_sj, "Atenciones_Individuales"),
            "Vitacura": metric_sum(final_vit, "Atenciones_Individuales"),
        },
    ])
    resumen_general["Total"] = resumen_general["San_Joaquin"] + resumen_general["Vitacura"]
    resumen_general = resumen_general[["Indicador", "San_Joaquin", "Vitacura", "Total"]]

    sheet_sources = {
        "SAN_JOAQUIN": out_dir / "SAN_JOAQUIN_APOYOS_2025_FINAL.csv",
        "VITACURA": out_dir / "VITACURA_APOYOS_2025_FINAL.csv",
        "RUT_SIN_CAMPUS": out_dir / "RUT_SIN_CAMPUS.csv",
        "REPORTE_CALIDAD": out_dir / "REPORTE_CALIDAD_DATOS.csv",
    }
    sheet_data = {name: pd.read_csv(path, dtype=str, keep_default_na=False) for name, path in sheet_sources.items()}

    report_path = out_dir / "DATAE_APOYOS_2025_INFORME.xlsx"
    with pd.ExcelWriter(report_path, engine="openpyxl") as writer:
        resumen_general.to_excel(writer, sheet_name="RESUMEN_GENERAL", index=False)
        for sheet_name in ["SAN_JOAQUIN", "VITACURA", "RUT_SIN_CAMPUS", "REPORTE_CALIDAD"]:
            sheet_data[sheet_name].to_excel(writer, sheet_name=sheet_name, index=False)

        for worksheet in writer.book.worksheets:
            _auto_adjust_worksheet(worksheet)


# =========================
# Pipeline principal
# =========================

def run_pipeline(repo_root: Path) -> None:
    verify_repo_structure(repo_root)

    data_dir = repo_root / "data"
    out_dir = repo_root / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    files = list_data_files(data_dir)
    if not files:
        raise SystemExit(f"No se encontraron archivos en {data_dir}. Coloca Excel/CSV en /data.")

    base_sj = None
    base_vit = None

    activity_frames = []
    issues: list[RutIssue] = []

    for f in files:
        print(f"Procesando: {f.name}")
        source = _detect_source(f)
        sheets = read_file_all_sheets(f)

        for sheet_name, df in sheets.items():
            if df is None or df.empty:
                continue

            if source == "BASE_SJ":
                base_sj = extract_base_campus(df, "SAN_JOAQUIN", f.name, sheet_name)
            elif source == "BASE_VIT":
                base_vit = extract_base_campus(df, "VITACURA", f.name, sheet_name)
            else:
                act_df = extract_activity_rows(source, df, sheet_name, f.name)
                if not act_df.empty:
                    activity_frames.append(act_df)

    if base_sj is None or base_vit is None:
        raise SystemExit("No pude identificar ambos archivos base (SAN JOAQUÍN / VITACURA). Revisa los nombres en /data.")

    activities = pd.concat(activity_frames, ignore_index=True) if activity_frames else pd.DataFrame(
        columns=["RUT_RAW","RUT_NORM","Nombre","Actividad","Participaciones","FuenteArchivo","FuenteHoja","Fila"]
    )

    # --- QA: Bases ---
    for campus, base in [("SAN_JOAQUIN", base_sj), ("VITACURA", base_vit)]:
        dup = base[base.duplicated("RUT_NORM", keep=False) & (base["RUT_NORM"] != "")]
        for idx, r in dup.iterrows():
            issues.append(RutIssue(
                issue_type="BASE_DUPLICADO",
                file=f"BASE_{campus}",
                sheet="BASE",
                row=int(idx),
                rut_raw=r.get("RUT_NORM",""),
                rut_norm=r.get("RUT_NORM",""),
                name_raw=r.get("Nombre",""),
                details="RUT duplicado en lista base del campus."
            ))

        miss_name = base[(base["RUT_NORM"] != "") & (base["Nombre"].astype(str).str.strip() == "")]
        for idx, r in miss_name.iterrows():
            issues.append(RutIssue(
                issue_type="BASE_SIN_NOMBRE",
                file=f"BASE_{campus}",
                sheet="BASE",
                row=int(idx),
                rut_raw=r.get("RUT_NORM",""),
                rut_norm=r.get("RUT_NORM",""),
                name_raw="",
                details="Estudiante sin nombre en lista base."
            ))

        bad = base[(base["RUT_NORM"] != "") & (~base["RUT_NORM"].apply(is_valid_rut))]
        for idx, r in bad.iterrows():
            issues.append(RutIssue(
                issue_type="RUT_INVALIDO_BASE",
                file=f"BASE_{campus}",
                sheet="BASE",
                row=int(idx),
                rut_raw=r.get("RUT_NORM",""),
                rut_norm=r.get("RUT_NORM",""),
                name_raw=r.get("Nombre",""),
                details="RUT no pasa validación (formato o DV)."
            ))

    inter = base_sj[["RUT_NORM"]].merge(base_vit[["RUT_NORM"]], on="RUT_NORM", how="inner")
    for _, r in inter.iterrows():
        issues.append(RutIssue(
            issue_type="RUT_EN_AMBOS_CAMPUS",
            file="BASES",
            sheet="BASE",
            row=-1,
            rut_raw=r["RUT_NORM"],
            rut_norm=r["RUT_NORM"],
            name_raw="",
            details="El mismo RUT aparece en más de un campus base."
        ))

    # --- QA: Actividades ---
    miss = activities[activities["RUT_NORM"].astype(str).str.strip() == ""]
    for _, r in miss.iterrows():
        issues.append(RutIssue(
            issue_type="REGISTRO_SIN_RUT",
            file=r.get("FuenteArchivo",""),
            sheet=r.get("FuenteHoja",""),
            row=int(r.get("Fila",-1)),
            rut_raw=str(r.get("RUT_RAW","")),
            rut_norm="",
            name_raw=str(r.get("Nombre","")),
            details="Registro sin RUT (no se puede cruzar)."
        ))

    bad = activities[(activities["RUT_NORM"].astype(str).str.strip() != "") & (~activities["RUT_NORM"].apply(is_valid_rut))]
    for _, r in bad.iterrows():
        issues.append(RutIssue(
            issue_type="RUT_INVALIDO",
            file=r.get("FuenteArchivo",""),
            sheet=r.get("FuenteHoja",""),
            row=int(r.get("Fila",-1)),
            rut_raw=str(r.get("RUT_RAW","")),
            rut_norm=str(r.get("RUT_NORM","")),
            name_raw=str(r.get("Nombre","")),
            details="RUT no pasa validación (formato o DV)."
        ))

    ne = activities[activities["Nombre"].astype(str).str.strip() != ""].copy()
    if not ne.empty:
        g = ne.groupby("RUT_NORM")["Nombre"].nunique().reset_index(name="nombres_distintos")
        conflicts = g[g["nombres_distintos"] > 1]
        for _, rr in conflicts.iterrows():
            rut = rr["RUT_NORM"]
            sample = ne[ne["RUT_NORM"] == rut].head(5)["Nombre"].astype(str).tolist()
            issues.append(RutIssue(
                issue_type="NOMBRES_DISTINTOS_MISMO_RUT",
                file="MULTI_FUENTE",
                sheet="",
                row=-1,
                rut_raw=rut,
                rut_norm=rut,
                name_raw="",
                details=f"Detectados {int(rr['nombres_distintos'])} nombres distintos. Ej: {' | '.join(sample)}"
            ))

    qa_columns = ["issue_type", "file", "sheet", "row", "rut_raw", "rut_norm", "name_raw", "details"]
    qa_df = pd.DataFrame([asdict(i) for i in issues], columns=qa_columns)

    # --- Consolidación ---
    agg = aggregate_activities(activities[["RUT_NORM","Nombre","Actividad","Participaciones"]].copy())
    final_sj = build_final_for_campus(base_sj, agg)
    final_vit = build_final_for_campus(base_vit, agg)
    sin = build_rut_sin_campus(base_sj, base_vit, agg)

    sin, validation_errors, validation_report_rows = validate_and_prepare_outputs(final_sj, final_vit, sin)

    if validation_report_rows:
        qa_extra = pd.DataFrame(validation_report_rows)
        qa_extra = qa_extra.rename(columns={"tipo": "issue_type", "archivo": "file", "detalle": "details"})
        qa_extra["sheet"] = ""
        qa_extra["row"] = -1
        qa_extra["rut_raw"] = ""
        qa_extra["rut_norm"] = ""
        qa_extra["name_raw"] = ""
        qa_df = pd.concat([qa_df, qa_extra[qa_columns]], ignore_index=True)

    resumen = build_resumen(final_sj, final_vit)

    final_sj.to_csv(out_dir / "SAN_JOAQUIN_APOYOS_2025_FINAL.csv", index=False, encoding="utf-8-sig")
    final_vit.to_csv(out_dir / "VITACURA_APOYOS_2025_FINAL.csv", index=False, encoding="utf-8-sig")
    sin.to_csv(out_dir / "RUT_SIN_CAMPUS.csv", index=False, encoding="utf-8-sig")
    resumen.to_csv(out_dir / "RESUMEN_DATAE_2025.csv", index=False, encoding="utf-8-sig")
    qa_df.to_csv(out_dir / "REPORTE_CALIDAD_DATOS.csv", index=False, encoding="utf-8-sig")
    export_excel_report(out_dir, final_sj, final_vit)
    export_outputs_to_sqlite(out_dir)

    if validation_errors:
        raise SystemExit("Validación de salidas falló: " + " | ".join(validation_errors))


def main():
    repo_root = Path(__file__).resolve().parent
    run_pipeline(repo_root)
    print("✅ Pipeline finalizado.")
    print(f"📁 Revisa output en: {repo_root / 'output'}")


if __name__ == "__main__":
    main()
