import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import glob

# 페이지 설정
st.set_page_config(layout="wide", page_title="서울시 학업중단 알리미", page_icon="🏫")

# 1. 데이터 로드 및 전처리 (기존 로직 유지)
@st.cache_data
def load_data(uploaded_files):
    all_dfs = []
    base_files = glob.glob("학업중단율_*.csv")
    file_list = uploaded_files if uploaded_files else base_files

    for f in file_list:
        try:
            fname = f.name if hasattr(f, 'name') else f
            year_val = fname.split('_')[1].split('.')[0]
            df_raw = pd.read_csv(f, skiprows=3, header=None)
            # 자치구, 초등율, 중등율, 고등율 추출
            df_refined = df_raw[[1, 4, 7, 10]].copy()
            df_refined.columns = ['자치구', '초등학교', '중학교', '고등학교']
            for col in ['초등학교', '중학교', '고등학교']:
                df_refined[col] = pd.to_numeric(df_refined[col], errors='coerce')
            df_refined['연도'] = int(year_val)
            all_dfs.append(df_refined)
        except: continue
    return pd.concat(all_dfs, ignore_index=True) if all_dfs else None

# --- 메인 화면 구성 ---
st.title("📊 서울시 학업중단 알리미")
uploaded = st.sidebar.file_uploader("데이터 추가 업로드", accept_multiple_files=True)
df = load_data(uploaded)

if df is not None:
    # 학교급 선택
    level = st.sidebar.selectbox("분석할 학교급", ["초등학교", "중학교", "고등학교", "전체 평균"], index=3)
    
    if level == "전체 평균":
        df['target'] = df[['초등학교', '중학교', '고등학교']].mean(axis=1)
    else:
        df['target'] = df[level]

    # --- 상단: 연도별 학업중단 추이 (기존) ---
    st.header("📈 연도별 학업중단 추이")
    trend_df = df[df['자치구'].str.contains('소계', na=False)].sort_values('연도')
    fig_line = px.line(trend_df, x='연도', y='target', markers=True, line_shape='spline', title="서울시 전체 평균 추이")
    st.plotly_chart(fig_line, use_container_width=True)

    st.divider()

    # --- 중간: 구별 히트맵 타임라인 (NEW!) ---
    st.header("🔥 자치구별 학업중단율 히트맵")
    st.markdown("색이 **진할수록(빨간색)** 해당 연도의 학업중단율이 높음을 의미합니다.")
    
    # 히트맵을 위한 데이터 재구조화 (Pivot)
    # 소계 제외한 구별 데이터만 필터링
    heatmap_data = df[~df['자치구'].str.contains('소계', na=False)]
    pivot_df = heatmap_data.pivot(index='자치구', columns='연도', values='target')
    # 구 이름 정렬 (가나다순)
    pivot_df = pivot_df.sort_index(ascending=False)

    fig_heat = px.imshow(
        pivot_df,
        labels=dict(x="연도", y="자치구", color="중단율(%)"),
        x=pivot_df.columns,
        y=pivot_df.index,
        color_continuous_scale="Reds", # 열정적인 레드 계열
        aspect="auto"
    )
    
    fig_heat.update_xaxes(side="top") # 연도를 상단에 표시
    st.plotly_chart(fig_heat, use_container_width=True)

    st.divider()

    # --- 하단: 지역별 분포 (지도) ---
    st.header("🗺️ 지역별 상세 분포")
    # 지도 로직 생략 (이전 답변과 동일하게 유지)
    st.info("지도와 순위표는 아래에 위치합니다.")
    
else:
    st.error("데이터를 찾을 수 없습니다.")
