# app.py
import re
import glob
import os
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="학업중단 현황 대시보드", layout="wide")

# -----------------------------
# Helpers
# -----------------------------
def read_csv_any_encoding(file_or_path):
    """Try common encodings for Korean CSV."""
    encodings = ["utf-8-sig", "cp949", "euc-kr", "utf-8"]
    last_err = None
    for enc in encodings:
        try:
            return pd.read_csv(file_or_path, encoding=enc)
        except Exception as e:
            last_err = e
    raise last_err


def infer_year_from_filename(name: str):
    m = re.search(r"(20\d{2})", name)
    return int(m.group(1)) if m else None


def tidy_dropout_csv(df_raw: pd.DataFrame, year: int) -> pd.DataFrame:
    """
    Your CSVs look like:
    - First two rows are 'header rows embedded in data':
      row 0: school level labels (초등학교/중학교/고등학교)
      row 1: measure labels (학생수, 학업중단자수, 학업중단율)
    - First two columns: 자치구별(1), 자치구별(2)
    """
    id_cols = ["자치구별(1)", "자치구별(2)"]
    if not all(c in df_raw.columns for c in id_cols):
        raise ValueError(f"필수 컬럼 {id_cols} 를 찾을 수 없습니다. 업로드 파일 형식을 확인해주세요.")

    data_cols = [c for c in df_raw.columns if c not in id_cols]

    # embedded header rows
    school_labels = df_raw.loc[0, data_cols].tolist()
    measure_labels = df_raw.loc[1, data_cols].tolist()

    new_cols = []
    for sch, meas in zip(school_labels, measure_labels):
        sch = str(sch).strip().replace(" ", "")
        meas = str(meas).strip().replace(" ", "")
        new_cols.append(f"{sch}|{meas}")

    df = df_raw.loc[2:, id_cols + data_cols].copy()
    df.columns = ["group", "region"] + new_cols
    df["year"] = year

    # drop leftover header text rows
    df = df[df["region"].notna()]
    df = df[~df["region"].astype(str).str.contains("자치구별")]

    # numeric conversion
    for c in df.columns:
        if "|" in c:
            df[c] = (
                df[c]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.replace("%", "", regex=False)
            )
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # totals (학생수/중단자수) across school levels
    dropout_cols = [c for c in df.columns if c.endswith("학업중단자수(명)")]
    student_cols = [c for c in df.columns if c.endswith("학생수(명)")]

    df["dropout_total"] = df[dropout_cols].sum(axis=1, skipna=True)
    df["students_total"] = df[student_cols].sum(axis=1, skipna=True)
    df["dropout_rate_total"] = np.where(
        df["students_total"] > 0,
        df["dropout_total"] / df["students_total"] * 100,
        np.nan
    )

    return df


def load_base_files():
    """
    Streamlit Cloud repo에 기본 데이터를 넣어두면(예: data/ 폴더),
    여기서 glob로 읽습니다.
    """
    candidates = []
    # repo root or data folder
    candidates += glob.glob("학업중단율_*.csv")
    candidates += glob.glob(os.path.join("data", "학업중단율_*.csv"))
    candidates = sorted(set(candidates))

    frames = []
    for path in candidates:
        year = infer_year_from_filename(os.path.basename(path))
        if year is None:
            continue
        raw = read_csv_any_encoding(path)
        frames.append(tidy_dropout_csv(raw, year))
    return frames


def load_uploaded_files(uploaded_files):
    frames = []
    for uf in uploaded_files:
        year = infer_year_from_filename(uf.name)
        if year is None:
            # 마지막 수단: 컬럼에 20xx가 들어 있으면 추정
            m = re.search(r"(20\d{2})", " ".join(map(str, uf.name.split())))
            year = int(m.group(1)) if m else None

        if year is None:
            st.warning(f"연도(20xx)를 파일명에서 찾을 수 없어 제외됨: {uf.name}")
            continue

        raw = read_csv_any_encoding(uf)
        frames.append(tidy_dropout_csv(raw, year))
    return frames


def make_school_long(df_all: pd.DataFrame) -> pd.DataFrame:
    """
    지역×연도×학교급별 학업중단자수(long) 생성
    """
    cols = [c for c in df_all.columns if c.endswith("학업중단자수(명)") and "|" in c]
    long = df_all.melt(
        id_vars=["year", "region", "group"],
        value_vars=cols,
        var_name="school_measure",
        value_name="dropout_count"
    )
    # school_measure: "초등학교|학업중단자수(명)" -> school="초등학교"
    long["school"] = long["school_measure"].str.split("|", n=1, expand=True)[0]
    long = long.drop(columns=["school_measure"])
    return long


# -----------------------------
# UI
# -----------------------------
st.title("학업중단 현황 대시보드")

with st.sidebar:
    st.subheader("데이터 추가 업로드")
    uploaded = st.file_uploader(
        "같은 형식의 CSV를 추가 업로드하면 자동 반영됩니다 (복수 선택 가능)",
        type=["csv"],
        accept_multiple_files=True
    )
    st.caption("팁: 파일명에 연도(예: 2025)가 포함되면 자동 인식합니다.")

# Load data
base_frames = load_base_files()
upload_frames = load_uploaded_files(uploaded) if uploaded else []

if not base_frames and not upload_frames:
    st.error("기본 데이터 파일을 찾지 못했습니다. repo에 '학업중단율_*.csv'를 포함시키거나 업로드해주세요.")
    st.stop()

df_all = pd.concat(base_frames + upload_frames, ignore_index=True)

# Deduplicate by (year, region) if same year uploaded; keep the last occurrence (uploads appended last)
df_all = df_all.sort_values(["year"]).drop_duplicates(subset=["year", "region"], keep="last")

# Controls
years = sorted(df_all["year"].dropna().unique().tolist())
min_y, max_y = min(years), max(years)

c1, c2, c3 = st.columns([1.2, 1.2, 2])
with c1:
    year_range = st.slider("연도 범위", min_value=min_y, max_value=max_y, value=(min_y, max_y))
with c2:
    region_options = sorted(df_all["region"].unique().tolist())
    default_regions = ["소계"] if "소계" in region_options else region_options[:1]
    regions_sel = st.multiselect("지역(자치구) 선택", options=region_options, default=default_regions)
with c3:
    st.caption("※ '소계'는 전체(합계) 행입니다. 연도별 전체 추이는 보통 소계 기준으로 확인합니다.")

df_f = df_all[(df_all["year"].between(year_range[0], year_range[1])) & (df_all["region"].isin(regions_sel))]

# -----------------------------
# 2) 연도별 전체 학업중단자 추이 (Plotly)
# -----------------------------
st.subheader("연도별 전체 학업중단자 변화")

# total row: region == '소계'
overall = df_all[df_all["region"] == "소계"].copy()
overall = overall[overall["year"].between(year_range[0], year_range[1])]
overall = overall.groupby("year", as_index=False).agg(
    dropout_total=("dropout_total", "sum"),
    students_total=("students_total", "sum"),
)
overall["dropout_rate_total"] = np.where(
    overall["students_total"] > 0,
    overall["dropout_total"] / overall["students_total"] * 100,
    np.nan
)

fig = px.line(
    overall.sort_values("year"),
    x="year",
    y="dropout_total",
    markers=True,
    hover_data={
        "dropout_total": ":,",
        "students_total": ":,",
        "dropout_rate_total": ":.3f",
        "year": True
    },
    labels={"year": "연도", "dropout_total": "전체 학업중단자수(명)"},
)
fig.update_layout(hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# 3) 연도별×학교급×지역 비교표
# -----------------------------
st.subheader("연도별 · 학교급 · 지역(자치구) 비교표 (학업중단자수)")

long_school = make_school_long(df_all)
long_school = long_school[long_school["year"].between(year_range[0], year_range[1])]
long_school = long_school[long_school["region"].isin(regions_sel)]

school_levels = sorted(long_school["school"].unique().tolist())
school_sel = st.multiselect("학교급 선택", options=school_levels, default=school_levels)

long_school = long_school[long_school["school"].isin(school_sel)]

# Pivot: rows=(year, region), cols=school, values=dropout_count
pivot = (
    long_school
    .groupby(["year", "region", "school"], as_index=False)["dropout_count"].sum()
    .pivot(index=["year", "region"], columns="school", values="dropout_count")
    .fillna(0)
    .sort_index()
)

# add total column
pivot["전체(학교급합)"] = pivot.sum(axis=1)

st.dataframe(
    pivot.style.format("{:,.0f}"),
    use_container_width=True
)

# Optional: download tidy data
with st.expander("데이터 다운로드"):
    st.caption("합쳐진 정제 데이터(tidy)를 CSV로 내려받을 수 있습니다.")
    out = df_all.copy()
    st.download_button(
        "정제 데이터 CSV 다운로드",
        data=out.to_csv(index=False).encode("utf-8-sig"),
        file_name="학업중단_정제데이터.csv",
        mime="text/csv"
    )
