from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd


# =========================
# Config
# =========================

SUPPORTED_EXT = {".xlsx", ".xls", ".csv"}

ACT_CIAC = "CIAC"
ACT_TALLER = "TALLER"
ACT_MENTORIA = "MENTORIA"
ACT_ATENCION = "ATENCION"

RUT_RE = re.compile(r"^\d{7,8}-[0-9K]$")

LOGGER = logging.getLogger("datae_pipeline")


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )


# =========================
# Normalización texto/columnas
# =========================


def _normalize_text(value: object) -> str:
    s = "" if value is None else str(value)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _normalized_columns_map(df: pd.DataFrame) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for col in df.columns:
        normalized = _normalize_text(col)
        if normalized and normalized not in mapping:
            mapping[normalized] = col
    return mapping


def _find_col(df: pd.DataFrame, *aliases: str, contains_tokens: tuple[str, ...] | None = None) -> str | None:
    cols_map = _normalized_columns_map(df)

    for alias in aliases:
        key = _normalize_text(alias)
        if key in cols_map:
            return cols_map[key]

    if contains_tokens:
        tokens = tuple(_normalize_text(t) for t in contains_tokens if _normalize_text(t))
        if tokens:
            for norm_col, raw_col in cols_map.items():
                if all(tok in norm_col for tok in tokens):
                    return raw_col

    return None


# =========================
# RUT: Normalización + Validación
# =========================


def _to_safe_string(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "null", "nat"}:
        return ""

    # Si Excel parseó a número flotante representado como texto, remover .0 final.
    m = re.fullmatch(r"(\d+)\.0+", text)
    if m:
        return m.group(1)

    return text


def _clean_rut_body(body: str) -> str:
    digits = re.sub(r"\D", "", body)
    if not digits:
        return ""

    # Mantiene largo estándar 7-8 cuando el dato viene con cero inicial extra.
    if len(digits) > 8 and digits.startswith("0"):
        digits = digits.lstrip("0")

    return digits


def normalize_rut(value: object) -> str:
    """
    Normaliza a formato ########-X cuando sea posible.
    No inventa DV si no viene en la fuente.
    """
    s = _to_safe_string(value)
    if not s:
        return ""

    s = s.replace(".", "")
    s = re.sub(r"\s+", "", s).upper()
    s = re.sub(r"[^0-9K-]", "", s)

    if "-" in s:
        parts = s.split("-")
        body = _clean_rut_body("".join(parts[:-1]))
        dv = re.sub(r"[^0-9K]", "", parts[-1])
        if body and dv:
            return f"{body}-{dv}"
        return body

    if len(s) >= 2 and re.fullmatch(r"\d+[0-9K]", s):
        body = _clean_rut_body(s[:-1])
        dv = s[-1]
        if body:
            return f"{body}-{dv}"

    return _clean_rut_body(s)


def _dv_expected(cuerpo: str) -> str:
    reversed_digits = list(map(int, reversed(cuerpo)))
    factors = [2, 3, 4, 5, 6, 7]
    total = 0
    for i, d in enumerate(reversed_digits):
        total += d * factors[i % len(factors)]
    mod = 11 - (total % 11)
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


def format_full_name(ap1: object, ap2: object, nombres: object) -> str:
    parts = []
    for p in (nombres, ap1, ap2):
        pp = _to_safe_string(p)
        if pp:
            parts.append(pp)
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
    return sorted(p for p in data_dir.glob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXT)


def iter_file_sheets(path: Path):
    try:
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False).fillna("")
            yield "CSV", df
            return

        with pd.ExcelFile(path) as xls:
            for sheet_name in xls.sheet_names:
                df = xls.parse(sheet_name=sheet_name, dtype=str).fillna("")
                yield sheet_name, df
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Error leyendo archivo %s", path.name)
        raise RuntimeError(f"No pude leer el archivo '{path.name}': {exc}") from exc


# =========================
# Detectores / Extractores
# =========================


def _detect_source(path: Path) -> str:
    name = _normalize_text(path.name)
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


def _normalize_rut_series(series: pd.Series) -> pd.Series:
    return series.astype(str).map(normalize_rut)


def extract_base_campus(df: pd.DataFrame, campus: str, source_file: str, source_sheet: str) -> pd.DataFrame:
    rut_col = _find_col(df, "rut", "run", contains_tokens=("rut",)) or _find_col(df, contains_tokens=("run",))
    dv_col = _find_col(df, "dv", "digito verificador", "digito")

    ap1_col = _find_col(df, "apellido 1", "apellido paterno", "apellido p", contains_tokens=("apellido", "1"))
    ap2_col = _find_col(df, "apellido 2", "apellido materno", "apellido m", contains_tokens=("apellido", "2"))
    nom_col = _find_col(df, "nombres", "nombre", contains_tokens=("nombre",))

    rut_raw = df[rut_col].astype(str) if rut_col else pd.Series([""] * len(df), index=df.index)
    if dv_col:
        rut_raw = rut_raw + "-" + df[dv_col].astype(str)

    out = pd.DataFrame(index=df.index)
    out["RUT_RAW"] = rut_raw
    out["RUT_NORM"] = _normalize_rut_series(out["RUT_RAW"])

    if nom_col and (ap1_col or ap2_col):
        out["Nombre"] = [
            format_full_name(
                df.at[i, ap1_col] if ap1_col else "",
                df.at[i, ap2_col] if ap2_col else "",
                df.at[i, nom_col] if nom_col else "",
            )
            for i in df.index
        ]
    elif nom_col:
        out["Nombre"] = df[nom_col].astype(str).str.strip()
    else:
        out["Nombre"] = ""

    out["Campus"] = campus
    out["FuenteArchivo"] = source_file
    out["FuenteHoja"] = source_sheet
    return out[["RUT_NORM", "Nombre", "Campus", "FuenteArchivo", "FuenteHoja"]].reset_index(drop=True)


def extract_activity_rows(source: str, df: pd.DataFrame, sheet_name: str, file_name: str) -> pd.DataFrame:
    rows: list[tuple] = []

    if source == "TALLERES_PI":
        rut_col = _find_col(df, "rut", contains_tokens=("rut",))
        nom_col = _find_col(df, "nombre", contains_tokens=("nombre",))
        ap_col = _find_col(df, "apellido paterno", contains_tokens=("apellido", "paterno"))
        am_col = _find_col(df, "apellido materno", contains_tokens=("apellido", "materno"))

        if rut_col:
            for i in df.index:
                rut_raw = df.at[i, rut_col]
                rows.append((
                    rut_raw,
                    normalize_rut(rut_raw),
                    format_full_name(df.at[i, ap_col] if ap_col else "", df.at[i, am_col] if am_col else "", df.at[i, nom_col] if nom_col else ""),
                    ACT_TALLER,
                    1,
                    file_name,
                    sheet_name,
                    int(i),
                ))

    elif source == "CIAC_SJ":
        rut_col = _find_col(df, "run", contains_tokens=("run",))
        if rut_col:
            for i in df.index:
                rut_raw = df.at[i, rut_col]
                rows.append((rut_raw, normalize_rut(rut_raw), "", ACT_CIAC, 1, file_name, sheet_name, int(i)))

    elif source == "CIAC_VIT":
        run_col = _find_col(df, "run", contains_tokens=("run",))
        dv_col = _find_col(df, "digito", "dv")
        if run_col:
            for i in df.index:
                run_raw = _to_safe_string(df.at[i, run_col])
                dv_raw = _to_safe_string(df.at[i, dv_col]) if dv_col else ""
                rut_raw = f"{run_raw}-{dv_raw}" if dv_raw else run_raw
                rows.append((rut_raw, normalize_rut(rut_raw), "", ACT_CIAC, 1, file_name, sheet_name, int(i)))

    elif source == "KATHERINE":
        cols_norm = {_normalize_text(c) for c in df.columns}
        has_sessions = "total de sesiones" in cols_norm or any("total" in c and "sesion" in c for c in cols_norm)

        if has_sessions:
            rut_col = _find_col(df, "rut", contains_tokens=("rut",))
            dv_col = _find_col(df, "dv", "digito")
            tot_col = _find_col(df, "total de sesiones", contains_tokens=("total", "sesion"))
            ap1_col = _find_col(df, "apellido 1", contains_tokens=("apellido", "1"))
            ap2_col = _find_col(df, "apellido 2", contains_tokens=("apellido", "2"))
            nom_col = _find_col(df, "nombres", contains_tokens=("nombre",))

            for i in df.index:
                rut_body = _to_safe_string(df.at[i, rut_col]) if rut_col else ""
                dv = _to_safe_string(df.at[i, dv_col]) if dv_col else ""
                rut_raw = f"{rut_body}-{dv}" if dv else rut_body

                try:
                    n = int(_to_safe_string(df.at[i, tot_col])) if tot_col else 1
                except Exception:  # noqa: BLE001
                    n = 1

                rows.append((
                    rut_raw,
                    normalize_rut(rut_raw),
                    format_full_name(df.at[i, ap1_col] if ap1_col else "", df.at[i, ap2_col] if ap2_col else "", df.at[i, nom_col] if nom_col else ""),
                    ACT_ATENCION,
                    max(1, n),
                    file_name,
                    sheet_name,
                    int(i),
                ))
        else:
            rut_col = _find_col(df, "rut", contains_tokens=("rut",))
            nom_col = _find_col(df, "nombre", contains_tokens=("nombre",))
            if rut_col:
                for i in df.index:
                    rut_raw = df.at[i, rut_col]
                    rows.append((rut_raw, normalize_rut(rut_raw), _to_safe_string(df.at[i, nom_col]) if nom_col else "", ACT_TALLER, 1, file_name, sheet_name, int(i)))

    elif source == "GLEUDYS":
        rut_col = _find_col(df, "rut", contains_tokens=("rut",))
        if rut_col:
            ap_col = _find_col(df, "apellido p", "apellido paterno", contains_tokens=("apellido", "p"))
            am_col = _find_col(df, "apellido m", "apellido materno", contains_tokens=("apellido", "m"))
            nom_col = _find_col(df, "nombres", "nombre", contains_tokens=("nombre",))

            sname = _normalize_text(sheet_name)
            if "micro" in sname or "mentor" in sname:
                act = ACT_MENTORIA
            elif "apoyo" in sname:
                act = ACT_CIAC
            elif "taller" in sname:
                act = ACT_TALLER
            elif "atenc" in sname:
                act = ACT_ATENCION
            else:
                act = ACT_MENTORIA

            for i in df.index:
                rut_raw = df.at[i, rut_col]
                rows.append((
                    rut_raw,
                    normalize_rut(rut_raw),
                    format_full_name(df.at[i, ap_col] if ap_col else "", df.at[i, am_col] if am_col else "", df.at[i, nom_col] if nom_col else ""),
                    act,
                    1,
                    file_name,
                    sheet_name,
                    int(i),
                ))

    if not rows:
        return pd.DataFrame(columns=["RUT_RAW", "RUT_NORM", "Nombre", "Actividad", "Participaciones", "FuenteArchivo", "FuenteHoja", "Fila"])

    return pd.DataFrame(
        rows,
        columns=["RUT_RAW", "RUT_NORM", "Nombre", "Actividad", "Participaciones", "FuenteArchivo", "FuenteHoja", "Fila"],
    )


# =========================
# Consolidación
# =========================


def aggregate_activities(activity_df: pd.DataFrame) -> pd.DataFrame:
    if activity_df.empty:
        return pd.DataFrame(columns=["RUT_NORM", "Nombre_best", "CIAC_count", "TALLER_count", "MENTORIA_count", "ATENCION_count"])

    tmp = activity_df.copy()
    tmp["Nombre"] = tmp["Nombre"].astype(str).str.strip()

    non_empty = tmp[tmp["Nombre"] != ""]
    if non_empty.empty:
        name_best = pd.DataFrame({"RUT_NORM": tmp["RUT_NORM"].unique(), "Nombre_best": ""})
    else:
        name_best = (
            non_empty.groupby(["RUT_NORM", "Nombre"]).size().reset_index(name="n").sort_values(["RUT_NORM", "n"], ascending=[True, False]).drop_duplicates("RUT_NORM")[["RUT_NORM", "Nombre"]].rename(columns={"Nombre": "Nombre_best"})
        )

    pivot = (
        tmp.groupby(["RUT_NORM", "Actividad"], observed=True)["Participaciones"]
        .sum()
        .reset_index()
        .pivot(index="RUT_NORM", columns="Actividad", values="Participaciones")
        .fillna(0)
        .reset_index()
    )

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
    return out[["RUT_NORM", "Nombre_best", "CIAC_count", "TALLER_count", "MENTORIA_count", "ATENCION_count"]]


def _mark(count: int) -> str:
    try:
        c = int(count)
    except Exception:  # noqa: BLE001
        c = 0
    if c <= 0:
        return ""
    return "X" if c == 1 else str(c)


def build_final_for_campus(base: pd.DataFrame, agg: pd.DataFrame) -> pd.DataFrame:
    out = base.merge(agg, on="RUT_NORM", how="left")
    if "Nombre_best" not in out.columns:
        out["Nombre_best"] = ""
    out["Nombre_best"] = out["Nombre_best"].fillna("")
    out["Nombre"] = out["Nombre"].astype(str).str.strip()
    out["Nombre_final"] = out["Nombre"]
    mask = (out["Nombre_final"] == "") & (out["Nombre_best"].astype(str).str.strip() != "")
    out.loc[mask, "Nombre_final"] = out.loc[mask, "Nombre_best"]

    for c in ["CIAC_count", "TALLER_count", "MENTORIA_count", "ATENCION_count"]:
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
    base_all = pd.concat([base_sj[["RUT_NORM"]], base_vit[["RUT_NORM"]]], ignore_index=True)
    in_base = set(base_all["RUT_NORM"].astype(str).tolist())

    out = agg[~agg["RUT_NORM"].isin(in_base)].copy()
    for c in ["CIAC_count", "TALLER_count", "MENTORIA_count", "ATENCION_count"]:
        if c not in out.columns:
            out[c] = 0

    out = pd.DataFrame({
        "RUT": out["RUT_NORM"],
        "Nombre": out["Nombre_best"].fillna(""),
        "Apoyo_Academico_CIAC": out["CIAC_count"].apply(_mark),
        "Talleres": out["TALLER_count"].apply(_mark),
        "Mentorias": out["MENTORIA_count"].apply(_mark),
        "Atenciones_Individuales": out["ATENCION_count"].apply(_mark),
    })
    return out.sort_values("RUT")


# =========================
# QA helpers
# =========================


def _qa_base(base: pd.DataFrame, campus: str, issues: list[RutIssue]) -> None:
    dup = base[base.duplicated("RUT_NORM", keep=False) & (base["RUT_NORM"] != "")]
    for idx, r in dup.iterrows():
        issues.append(RutIssue("BASE_DUPLICADO", f"BASE_{campus}", "BASE", int(idx), r.get("RUT_NORM", ""), r.get("RUT_NORM", ""), r.get("Nombre", ""), "RUT duplicado en lista base del campus."))

    miss_name = base[(base["RUT_NORM"] != "") & (base["Nombre"].astype(str).str.strip() == "")]
    for idx, r in miss_name.iterrows():
        issues.append(RutIssue("BASE_SIN_NOMBRE", f"BASE_{campus}", "BASE", int(idx), r.get("RUT_NORM", ""), r.get("RUT_NORM", ""), "", "Estudiante sin nombre en lista base."))

    bad = base[(base["RUT_NORM"] != "") & (~base["RUT_NORM"].apply(is_valid_rut))]
    for idx, r in bad.iterrows():
        issues.append(RutIssue("RUT_INVALIDO_BASE", f"BASE_{campus}", "BASE", int(idx), r.get("RUT_NORM", ""), r.get("RUT_NORM", ""), r.get("Nombre", ""), "RUT no pasa validación (formato o DV)."))


def _qa_activities(activities: pd.DataFrame, issues: list[RutIssue]) -> None:
    miss = activities[activities["RUT_NORM"].astype(str).str.strip() == ""]
    for _, r in miss.iterrows():
        issues.append(RutIssue("REGISTRO_SIN_RUT", r.get("FuenteArchivo", ""), r.get("FuenteHoja", ""), int(r.get("Fila", -1)), str(r.get("RUT_RAW", "")), "", str(r.get("Nombre", "")), "Registro sin RUT (no se puede cruzar)."))

    bad = activities[(activities["RUT_NORM"].astype(str).str.strip() != "") & (~activities["RUT_NORM"].apply(is_valid_rut))]
    for _, r in bad.iterrows():
        issues.append(RutIssue("RUT_INVALIDO", r.get("FuenteArchivo", ""), r.get("FuenteHoja", ""), int(r.get("Fila", -1)), str(r.get("RUT_RAW", "")), str(r.get("RUT_NORM", "")), str(r.get("Nombre", "")), "RUT no pasa validación (formato o DV)."))

    ne = activities[activities["Nombre"].astype(str).str.strip() != ""].copy()
    if ne.empty:
        return

    g = ne.groupby("RUT_NORM")["Nombre"].nunique().reset_index(name="nombres_distintos")
    conflicts = g[g["nombres_distintos"] > 1]
    for _, rr in conflicts.iterrows():
        rut = rr["RUT_NORM"]
        sample = ne[ne["RUT_NORM"] == rut].head(5)["Nombre"].astype(str).tolist()
        issues.append(RutIssue("NOMBRES_DISTINTOS_MISMO_RUT", "MULTI_FUENTE", "", -1, rut, rut, "", f"Detectados {int(rr['nombres_distintos'])} nombres distintos. Ej: {' | '.join(sample)}"))


# =========================
# Pipeline principal
# =========================


def run_pipeline(repo_root: Path) -> None:
    data_dir = repo_root / "data"
    out_dir = repo_root / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    files = list_data_files(data_dir)
    if not files:
        raise SystemExit(f"No se encontraron archivos en {data_dir}. Coloca Excel/CSV en /data.")

    LOGGER.info("Archivos detectados: %s", len(files))

    base_sj = None
    base_vit = None
    activity_frames: list[pd.DataFrame] = []
    issues: list[RutIssue] = []

    for f in files:
        source = _detect_source(f)
        LOGGER.info("Procesando %s (source=%s)", f.name, source)

        try:
            for sheet_name, df in iter_file_sheets(f):
                if df is None or df.empty:
                    LOGGER.info("  Hoja vacía omitida: %s", sheet_name)
                    continue

                if source == "BASE_SJ":
                    base_sj = extract_base_campus(df, "SAN_JOAQUIN", f.name, sheet_name)
                elif source == "BASE_VIT":
                    base_vit = extract_base_campus(df, "VITACURA", f.name, sheet_name)
                else:
                    act_df = extract_activity_rows(source, df, sheet_name, f.name)
                    if not act_df.empty:
                        activity_frames.append(act_df)
        except RuntimeError as exc:
            issues.append(RutIssue("ARCHIVO_NO_LEIBLE", f.name, "", -1, "", "", "", str(exc)))
            LOGGER.error("Archivo omitido por error: %s", f.name)

    if base_sj is None or base_vit is None:
        raise SystemExit("No pude identificar ambos archivos base (SAN JOAQUÍN / VITACURA). Revisa los nombres en /data.")

    activities = pd.concat(activity_frames, ignore_index=True) if activity_frames else pd.DataFrame(
        columns=["RUT_RAW", "RUT_NORM", "Nombre", "Actividad", "Participaciones", "FuenteArchivo", "FuenteHoja", "Fila"]
    )

    _qa_base(base_sj, "SAN_JOAQUIN", issues)
    _qa_base(base_vit, "VITACURA", issues)

    inter = base_sj[["RUT_NORM"]].merge(base_vit[["RUT_NORM"]], on="RUT_NORM", how="inner")
    for _, r in inter.iterrows():
        issues.append(RutIssue("RUT_EN_AMBOS_CAMPUS", "BASES", "BASE", -1, r["RUT_NORM"], r["RUT_NORM"], "", "El mismo RUT aparece en más de un campus base."))

    _qa_activities(activities, issues)

    qa_df = pd.DataFrame([asdict(i) for i in issues])
    qa_df.to_csv(out_dir / "REPORTE_CALIDAD_DATOS.csv", index=False, encoding="utf-8-sig")

    agg = aggregate_activities(activities[["RUT_NORM", "Nombre", "Actividad", "Participaciones"]].copy())
    final_sj = build_final_for_campus(base_sj, agg)
    final_vit = build_final_for_campus(base_vit, agg)
    sin = build_rut_sin_campus(base_sj, base_vit, agg)

    final_sj.to_csv(out_dir / "SAN_JOAQUIN_APOYOS_2025_FINAL.csv", index=False, encoding="utf-8-sig")
    final_vit.to_csv(out_dir / "VITACURA_APOYOS_2025_FINAL.csv", index=False, encoding="utf-8-sig")
    sin.to_csv(out_dir / "RUT_SIN_CAMPUS.csv", index=False, encoding="utf-8-sig")


def main() -> None:
    configure_logging()
    repo_root = Path(__file__).resolve().parent
    run_pipeline(repo_root)
    print("✅ Pipeline finalizado.")
    print(f"📁 Revisa output en: {repo_root / 'output'}")


if __name__ == "__main__":
    main()
