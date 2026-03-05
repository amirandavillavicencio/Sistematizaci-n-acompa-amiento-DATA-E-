from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

ACTIVITY_TRACE_COLS = [
    "SRC_CIAC_COUNT",
    "SRC_PI_S1_COUNT",
    "SRC_PI_S2_COUNT",
    "SRC_KATH_ATENC_COUNT",
    "SRC_GLEU_ATENC_COUNT",
    "SRC_KATH_TALLER_COUNT",
    "SRC_GLEU_MENT_COUNT",
    "SRC_FLAGS",
]


def norm_text(value: Any) -> str:
    if value is None:
        return ""
    txt = str(value).strip()
    return "" if txt.lower() in {"", "nan", "none", "null"} else txt


def normalize_rut(value: Any) -> str:
    txt = norm_text(value).upper().replace(".", "")
    txt = re.sub(r"\s+", "", txt)
    txt = re.sub(r"[^0-9K-]", "", txt)
    if not txt:
        return ""

    if "-" in txt:
        body, dv = txt.rsplit("-", 1)
        body = re.sub(r"[^0-9]", "", body)
        dv = re.sub(r"[^0-9K]", "", dv)
        return f"{body}-{dv}" if body and dv else ""

    compact = re.sub(r"[^0-9K]", "", txt)
    if len(compact) >= 2 and re.fullmatch(r"[0-9]+[0-9K]", compact):
        return f"{compact[:-1]}-{compact[-1]}"
    return ""


def expected_dv(body: str) -> str:
    factors = [2, 3, 4, 5, 6, 7]
    total = sum(int(d) * factors[i % len(factors)] for i, d in enumerate(reversed(body)))
    mod = 11 - (total % 11)
    if mod == 11:
        return "0"
    if mod == 10:
        return "K"
    return str(mod)


def validate_rut(rut: str) -> tuple[bool, str]:
    if not rut:
        return False, "RUT vacío"
    if not re.fullmatch(r"\d{7,8}-[0-9K]", rut):
        return False, "Formato inválido (debe ser 7-8 dígitos + guion + DV)"
    body, dv = rut.split("-")
    if expected_dv(body) != dv:
        return False, "DV inválido"
    return True, ""


def norm_col(col: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(col).lower())).strip()


def find_col(df: pd.DataFrame, *needles: str) -> str | None:
    cols = {norm_col(c): c for c in df.columns}
    for needle in needles:
        n = norm_col(needle)
        if n in cols:
            return cols[n]
    for c in df.columns:
        n = norm_col(c)
        if any(norm_col(needle) in n for needle in needles):
            return c
    return None


def parse_int(value: Any, default: int = 0) -> int:
    txt = norm_text(value)
    if not txt:
        return default
    m = re.search(r"-?\d+", txt)
    if not m:
        return default
    return int(m.group())


def campus_from_text(value: Any) -> str | None:
    t = norm_text(value).lower()
    if not t:
        return None
    if "joa" in t or "san" in t:
        return "SAN_JOAQUIN"
    if "vit" in t:
        return "VITACURA"
    return None


def mark_count(n: int) -> str:
    if n <= 0:
        return ""
    return "X" if n == 1 else str(n)


@dataclass
class StudentAgg:
    rut: str
    names: Counter
    campus_hints: Counter
    src_ciac: int = 0
    src_pi_s1: int = 0
    src_pi_s2: int = 0
    src_kath_atenc: int = 0
    src_gleu_atenc: int = 0
    src_kath_taller: int = 0
    src_gleu_ment: int = 0
    flags: set[str] = None

    def __post_init__(self) -> None:
        if self.flags is None:
            self.flags = set()


def add_record(store: dict[str, StudentAgg], invalid_rows: list[dict[str, Any]], *, rut_raw: Any, name: Any = "", campus_hint: Any = "", source_file: str, source_sheet: str, row_number: int, increments: dict[str, int]) -> None:
    rut = normalize_rut(rut_raw)
    valid, detail = validate_rut(rut)
    if not valid:
        invalid_rows.append({
            "fuente_archivo": source_file,
            "fuente_hoja": source_sheet,
            "fila": row_number,
            "rut_raw": norm_text(rut_raw),
            "rut_normalizado": rut,
            "motivo": detail,
        })
        return

    if rut not in store:
        store[rut] = StudentAgg(rut=rut, names=Counter(), campus_hints=Counter())

    st = store[rut]
    clean_name = norm_text(name)
    if clean_name:
        st.names[clean_name] += 1
    hint = campus_from_text(campus_hint)
    if hint:
        st.campus_hints[hint] += 1

    for k, v in increments.items():
        setattr(st, k, getattr(st, k) + int(v))
    st.flags.add(f"{source_file}::{source_sheet}")


def load_base(path: Path, campus: str) -> pd.DataFrame:
    df = pd.read_excel(path, dtype=str).fillna("")
    rut_col = find_col(df, "Rut", "RUN")
    dv_col = find_col(df, "DV", "Digito Verificador")
    ap1 = find_col(df, "Apellido 1", "Apellido Paterno")
    ap2 = find_col(df, "Apellido 2", "Apellido Materno")
    nom = find_col(df, "Nombres", "Nombre")

    rows = []
    for idx in range(len(df)):
        raw = f"{df.at[idx, rut_col]}-{df.at[idx, dv_col]}" if rut_col and dv_col else (df.at[idx, rut_col] if rut_col else "")
        rut = normalize_rut(raw)
        valid, reason = validate_rut(rut)
        full_name = " ".join([norm_text(df.at[idx, c]) for c in [nom, ap1, ap2] if c]).strip()
        rows.append({"RUT": rut, "Nombre": full_name, "Campus": campus, "Valido": valid, "Motivo": reason})
    return pd.DataFrame(rows)


def run_pipeline(repo_root: Path) -> None:
    data_dir = repo_root / "data"
    output_dir = repo_root / "output"
    artifact_dir = repo_root / "_artifacts"
    output_dir.mkdir(exist_ok=True)
    artifact_dir.mkdir(exist_ok=True)

    base_sj = load_base(data_dir / "SAN JOAQUIN APOYOS 2025.xlsx", "SAN_JOAQUIN")
    base_vit = load_base(data_dir / "VITACURA APOYOS 2025.xlsx", "VITACURA")

    invalid_rows: list[dict[str, Any]] = []
    students: dict[str, StudentAgg] = {}

    # Talleres Proyecto Inicial S1
    pi_s1 = pd.read_excel(data_dir / "Asistencia Talleres Proyecto Inicial Santiago 2025-1.xlsx", dtype=str).fillna("")
    rut_col = find_col(pi_s1, "RUT")
    campus_col = find_col(pi_s1, "campus")
    name_col = find_col(pi_s1, "Nombre2", "Nombre")
    for i in range(len(pi_s1)):
        add_record(students, invalid_rows, rut_raw=pi_s1.at[i, rut_col], name=pi_s1.at[i, name_col] if name_col else "", campus_hint=pi_s1.at[i, campus_col] if campus_col else "", source_file="PI_S1", source_sheet="Sheet1", row_number=i + 2, increments={"src_pi_s1": 1})

    # Talleres Proyecto Inicial S2
    pi_s2 = pd.read_excel(data_dir / "AsistenciaTalleres Proyecto Inicial 2025-2.xlsx", dtype=str).fillna("")
    rut_col = find_col(pi_s2, "RUT")
    campus_col = find_col(pi_s2, "campus")
    name_col = find_col(pi_s2, "Nombre2", "Nombre")
    for i in range(len(pi_s2)):
        add_record(students, invalid_rows, rut_raw=pi_s2.at[i, rut_col], name=pi_s2.at[i, name_col] if name_col else "", campus_hint=pi_s2.at[i, campus_col] if campus_col else "", source_file="PI_S2", source_sheet="Sheet1", row_number=i + 2, increments={"src_pi_s2": 1})

    # CIAC SJ
    ciac_sj = pd.read_excel(data_dir / "CIAC San Joaquín - Registro participación estudiantes.xlsx", sheet_name="Asistencia 2S 2025", dtype=str).fillna("")
    rut_col = find_col(ciac_sj, "RUN")
    for i in range(len(ciac_sj)):
        add_record(students, invalid_rows, rut_raw=ciac_sj.at[i, rut_col], source_file="CIAC_SJ", source_sheet="Asistencia 2S 2025", row_number=i + 2, increments={"src_ciac": 1})

    # CIAC VIT
    ciac_vit = pd.read_excel(data_dir / "CIAC Vitacura - Registro participación estudiantes.xlsx", sheet_name="Registro de participación", dtype=str).fillna("")
    run_col = find_col(ciac_vit, "RUN (sin puntos ni digito verificador)", "RUN")
    dv_col = find_col(ciac_vit, "Dígito Verificador", "DV")
    for i in range(len(ciac_vit)):
        rut_raw = f"{ciac_vit.at[i, run_col]}-{ciac_vit.at[i, dv_col]}" if dv_col else ciac_vit.at[i, run_col]
        add_record(students, invalid_rows, rut_raw=rut_raw, source_file="CIAC_VIT", source_sheet="Registro de participación", row_number=i + 2, increments={"src_ciac": 1})

    # Katherine: Atenciones + Talleres
    kath_at = pd.read_excel(data_dir / "Katherine - AtencionesyTalleresPsi2025.xlsx", sheet_name="AtenciónIndividual2025", dtype=str).fillna("")
    rut_col = find_col(kath_at, "Rut")
    dv_col = find_col(kath_at, "DV")
    name_cols = [find_col(kath_at, "Nombres"), find_col(kath_at, "Apellido 1"), find_col(kath_at, "Apellido 2")]
    total_col = find_col(kath_at, "Total de sesiones")
    for i in range(len(kath_at)):
        rut_raw = f"{kath_at.at[i, rut_col]}-{kath_at.at[i, dv_col]}" if dv_col else kath_at.at[i, rut_col]
        name = " ".join(norm_text(kath_at.at[i, c]) for c in name_cols if c).strip()
        n = max(0, parse_int(kath_at.at[i, total_col], 0))
        if n > 0:
            add_record(students, invalid_rows, rut_raw=rut_raw, name=name, source_file="KATH_ATENC", source_sheet="AtenciónIndividual2025", row_number=i + 2, increments={"src_kath_atenc": n})

    kath_taller = pd.read_excel(data_dir / "Katherine - AtencionesyTalleresPsi2025.xlsx", sheet_name="Talleres2025", dtype=str).fillna("")
    rut_col = find_col(kath_taller, "RUT")
    campus_col = find_col(kath_taller, "Campus")
    name_col = find_col(kath_taller, "Nombre")
    for i in range(len(kath_taller)):
        add_record(students, invalid_rows, rut_raw=kath_taller.at[i, rut_col], name=kath_taller.at[i, name_col] if name_col else "", campus_hint=kath_taller.at[i, campus_col] if campus_col else "", source_file="KATH_TALLER", source_sheet="Talleres2025", row_number=i + 2, increments={"src_kath_taller": 1})

    # Gleudys: atenciones (header fila 2)
    gleu_at = pd.read_excel(data_dir / "Gleudys - Datos implementación 2025 DATA PACE.xlsx", sheet_name="Atenciones individuales", header=1, dtype=str).fillna("")
    rut_col = find_col(gleu_at, "RUT")
    ap1 = find_col(gleu_at, "APELLIDO P")
    ap2 = find_col(gleu_at, "APELLIDO M")
    nom = find_col(gleu_at, "NOMBRE")
    at_col = find_col(gleu_at, "N° de atenciones", "No de atenciones")
    camp_col = find_col(gleu_at, "Campus")
    for i in range(len(gleu_at)):
        name = " ".join(norm_text(gleu_at.at[i, c]) for c in [nom, ap1, ap2] if c).strip()
        n = max(0, parse_int(gleu_at.at[i, at_col], 0))
        if n > 0:
            add_record(students, invalid_rows, rut_raw=gleu_at.at[i, rut_col], name=name, campus_hint=gleu_at.at[i, camp_col] if camp_col else "", source_file="GLEU_ATENC", source_sheet="Atenciones individuales", row_number=i + 3, increments={"src_gleu_atenc": n})

    # Gleudys mentorías: 1 fila = 1 participación
    gleu_ment = pd.read_excel(data_dir / "Gleudys - Datos implementación 2025 DATA PACE.xlsx", sheet_name="Mentorías", header=1, dtype=str).fillna("")
    rut_col = find_col(gleu_ment, "Inscritos")
    name_col = find_col(gleu_ment, "Nombre y apellido")
    for i in range(len(gleu_ment)):
        add_record(students, invalid_rows, rut_raw=gleu_ment.at[i, rut_col], name=gleu_ment.at[i, name_col] if name_col else "", source_file="GLEU_MENT", source_sheet="Mentorías", row_number=i + 3, increments={"src_gleu_ment": 1})

    # Base maps válidos
    base_sj_valid = base_sj[base_sj["Valido"]].drop_duplicates("RUT")
    base_vit_valid = base_vit[base_vit["Valido"]].drop_duplicates("RUT")
    sj_map = dict(zip(base_sj_valid["RUT"], base_sj_valid["Nombre"]))
    vit_map = dict(zip(base_vit_valid["RUT"], base_vit_valid["Nombre"]))

    all_ruts = set(sj_map) | set(vit_map) | set(students)

    final_rows = []
    for rut in sorted(all_ruts):
        st = students.get(rut, StudentAgg(rut=rut, names=Counter(), campus_hints=Counter()))
        if rut in sj_map:
            campus = "SAN_JOAQUIN"
        elif rut in vit_map:
            campus = "VITACURA"
        else:
            if len(st.campus_hints) == 1:
                campus = st.campus_hints.most_common(1)[0][0]
            else:
                campus = "SIN_CAMPUS"

        name = sj_map.get(rut) or vit_map.get(rut) or (st.names.most_common(1)[0][0] if st.names else "")
        ciac = st.src_ciac
        talleres = st.src_pi_s1 + st.src_pi_s2 + st.src_kath_taller
        mentorias = st.src_gleu_ment
        atenciones = st.src_kath_atenc + st.src_gleu_atenc

        final_rows.append({
            "RUT": rut,
            "Nombre": name,
            "Campus": campus,
            "Apoyo_Academico_CIAC": mark_count(ciac),
            "Talleres": mark_count(talleres),
            "Mentorias": mark_count(mentorias),
            "Atenciones_Individuales": mark_count(atenciones),
            "SRC_CIAC_COUNT": ciac,
            "SRC_PI_S1_COUNT": st.src_pi_s1,
            "SRC_PI_S2_COUNT": st.src_pi_s2,
            "SRC_KATH_ATENC_COUNT": st.src_kath_atenc,
            "SRC_GLEU_ATENC_COUNT": st.src_gleu_atenc,
            "SRC_KATH_TALLER_COUNT": st.src_kath_taller,
            "SRC_GLEU_MENT_COUNT": st.src_gleu_ment,
            "SRC_FLAGS": " | ".join(sorted(st.flags)),
        })

    final = pd.DataFrame(final_rows)
    final_sj = final[final["Campus"] == "SAN_JOAQUIN"].drop(columns=["Campus"]).reset_index(drop=True)
    final_vit = final[final["Campus"] == "VITACURA"].drop(columns=["Campus"]).reset_index(drop=True)
    final_sin = final[final["Campus"] == "SIN_CAMPUS"].drop(columns=["Campus"]).reset_index(drop=True)

    # Auditoría
    invalid_df = pd.DataFrame(invalid_rows)
    if invalid_df.empty:
        invalid_df = pd.DataFrame(columns=["fuente_archivo", "fuente_hoja", "fila", "rut_raw", "rut_normalizado", "motivo"])

    resumen = pd.DataFrame([
        {"metric": "total_sj", "value": len(final_sj)},
        {"metric": "total_vit", "value": len(final_vit)},
        {"metric": "total_sin_campus", "value": len(final_sin)},
        {"metric": "total_rut_invalidos", "value": len(invalid_df)},
        {"metric": "sum_ciac", "value": int(final["SRC_CIAC_COUNT"].sum())},
        {"metric": "sum_talleres", "value": int((final["SRC_PI_S1_COUNT"] + final["SRC_PI_S2_COUNT"] + final["SRC_KATH_TALLER_COUNT"]).sum())},
        {"metric": "sum_mentorias", "value": int(final["SRC_GLEU_MENT_COUNT"].sum())},
        {"metric": "sum_atenciones", "value": int((final["SRC_KATH_ATENC_COUNT"] + final["SRC_GLEU_ATENC_COUNT"]).sum())},
    ])

    # CSV texto versionados
    final_sj.to_csv(output_dir / "SAN_JOAQUIN_APOYOS_2025_FINAL.csv", index=False, encoding="utf-8")
    final_vit.to_csv(output_dir / "VITACURA_APOYOS_2025_FINAL.csv", index=False, encoding="utf-8")
    final_sin.to_csv(output_dir / "RUT_SIN_CAMPUS.csv", index=False, encoding="utf-8")
    resumen.to_csv(output_dir / "auditoria_resumen_corregido.csv", index=False, encoding="utf-8")
    invalid_df.to_csv(output_dir / "auditoria_detalle_corregido.csv", index=False, encoding="utf-8")

    # Excel corregido fuera de control de git
    excel_path = artifact_dir / "DATAE_APOYOS_2025_INFORME_CORREGIDO.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        resumen.to_excel(writer, sheet_name="RESUMEN", index=False)
        final_sj.to_excel(writer, sheet_name="SAN_JOAQUIN", index=False)
        final_vit.to_excel(writer, sheet_name="VITACURA", index=False)
        final_sin.to_excel(writer, sheet_name="SIN_CAMPUS", index=False)
        invalid_df.to_excel(writer, sheet_name="RUT_INVALIDOS", index=False)

    print("=== MÉTRICAS CORREGIDAS ===")
    print(resumen.to_string(index=False))
    print(f"Excel corregido generado en: {excel_path}")


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    run_pipeline(repo_root)


if __name__ == "__main__":
    main()
