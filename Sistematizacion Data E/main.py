from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from dataclasses import dataclass, asdict

import pandas as pd


# =========================
# Config
# =========================

SUPPORTED_EXT = {".xlsx", ".xls", ".csv"}

ACT_CIAC = "CIAC"
ACT_TALLER = "TALLER"
ACT_MENTORIA = "MENTORIA"
ACT_ATENCION = "ATENCION"


# =========================
# RUT: Normalización + Validación
# =========================

RUT_RE = re.compile(r"^\d{7,8}-[0-9K]$")


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
    cols = {_norm_colname(c): c for c in df.columns}
    for cand in candidates:
        key = _norm_colname(cand)
        if key in cols:
            return cols[key]
    return None


def _norm_colname(value: str) -> str:
    s = str(value).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _find_col_contains(df: pd.DataFrame, needle: str) -> str | None:
    needle = _norm_colname(needle)
    for c in df.columns:
        if needle in _norm_colname(c):
            return c
    return None


def _find_col_by_tokens(df: pd.DataFrame, *tokens: str) -> str | None:
    wanted = {_norm_colname(t) for t in tokens}
    for c in df.columns:
        parts = set(_norm_colname(c).split())
        if parts & wanted:
            return c
    return None


def extract_base_campus(df: pd.DataFrame, campus: str, source_file: str, source_sheet: str) -> pd.DataFrame:
    rut_col = _col(df, "Rut", "RUT", "RUN") or _find_col_by_tokens(df, "rut", "run")
    dv_col = _col(df, "DV", "Dígito Verificador", "Digito Verificador") or _find_col_contains(df, "dv")

    ap1 = _col(df, "Apellido 1", "Apellido1", "Apellido P", "Apellido Paterno") or _find_col_contains(df, "apellido 1")
    ap2 = _col(df, "Apellido 2", "Apellido2", "Apellido M", "Apellido Materno") or _find_col_contains(df, "apellido 2")
    nom = _col(df, "Nombres", "Nombre", "NOMBRE") or _find_col_contains(df, "nombres") or _find_col_contains(df, "nombre")

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
        rut_col = _find_col_by_tokens(df, "rut", "run")
        nom = _col(df, "Nombre") or _find_col_contains(df, "nombre")
        ap = _col(df, "Apellido Paterno") or _find_col_contains(df, "apellido paterno")
        am = _col(df, "Apellido Materno") or _find_col_contains(df, "apellido materno")
        if rut_col:
            for i in range(len(df)):
                rut_raw = df.at[i, rut_col]
                rut_norm = normalize_rut(rut_raw)
                name = format_full_name(df.at[i, ap] if ap else "", df.at[i, am] if am else "", df.at[i, nom] if nom else "")
                rows.append((rut_raw, rut_norm, name, ACT_TALLER, 1, file_name, sheet_name, i))

    elif source == "CIAC_SJ":
        rut_col = _col(df, "RUN", "Run") or _find_col_by_tokens(df, "run", "rut")
        if rut_col:
            for i in range(len(df)):
                rut_raw = df.at[i, rut_col]
                rut_norm = normalize_rut(rut_raw)
                rows.append((rut_raw, rut_norm, "", ACT_CIAC, 1, file_name, sheet_name, i))

    elif source == "CIAC_VIT":
        run_col = _find_col_by_tokens(df, "run", "rut")
        dv_col = _find_col_contains(df, "dígito") or _find_col_contains(df, "digito") or _find_col_contains(df, "dv")
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
            rut_col = _col(df, "Rut") or _find_col_contains(df, "rut")
            dv_col = _col(df, "DV") or _find_col_contains(df, "dv")
            tot_col = _col(df, "Total de sesiones") or _find_col_contains(df, "total de sesiones") or _find_col_contains(df, "sesiones")
            ap1 = _col(df, "Apellido 1") or _find_col_contains(df, "apellido 1")
            ap2 = _col(df, "Apellido 2") or _find_col_contains(df, "apellido 2")
            nom = _col(df, "Nombres") or _find_col_contains(df, "nombres")

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
            rut_col = _find_col_by_tokens(df, "rut", "run")
            nom_col = _col(df, "Nombre") or _find_col_contains(df, "nombre")
            if rut_col:
                for i in range(len(df)):
                    rut_raw = df.at[i, rut_col]
                    rut_norm = normalize_rut(rut_raw)
                    name = str(df.at[i, nom_col]).strip() if nom_col else ""
                    rows.append((rut_raw, rut_norm, name, ACT_TALLER, 1, file_name, sheet_name, i))

    elif source == "GLEUDYS":
        rut_col = _col(df, "RUT") or _find_col_by_tokens(df, "rut", "run")
        if rut_col:
            ap = _col(df, "Apellido p", "Apellido P", "Apellido Paterno") or _find_col_contains(df, "apellido p")
            am = _col(df, "Apellido m", "Apellido M", "Apellido Materno") or _find_col_contains(df, "apellido m")
            nom = _col(df, "Nombres", "Nombre") or _find_col_contains(df, "nombres") or _find_col_contains(df, "nombre")

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

    base_sj = None
    base_vit = None

    activity_frames = []
    issues: list[RutIssue] = []

    for f in files:
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

    qa_df = pd.DataFrame([asdict(i) for i in issues])
    qa_df.to_csv(out_dir / "REPORTE_CALIDAD_DATOS.csv", index=False, encoding="utf-8-sig")

    # --- Consolidación ---
    agg = aggregate_activities(activities[["RUT_NORM","Nombre","Actividad","Participaciones"]].copy())
    final_sj = build_final_for_campus(base_sj, agg)
    final_vit = build_final_for_campus(base_vit, agg)
    sin = build_rut_sin_campus(base_sj, base_vit, agg)

    final_sj.to_csv(out_dir / "SAN_JOAQUIN_APOYOS_2025_FINAL.csv", index=False, encoding="utf-8-sig")
    final_vit.to_csv(out_dir / "VITACURA_APOYOS_2025_FINAL.csv", index=False, encoding="utf-8-sig")
    sin.to_csv(out_dir / "RUT_SIN_CAMPUS.csv", index=False, encoding="utf-8-sig")


def main():
    repo_root = Path(__file__).resolve().parent
    run_pipeline(repo_root)
    print("✅ Pipeline finalizado.")
    print(f"📁 Revisa output en: {repo_root / 'output'}")


if __name__ == "__main__":
    main()
