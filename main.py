import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import glob

# 페이지 설정
st.set_page_config(layout="wide", page_title="서울시 학업중단 알리미", page_icon="🏫")

# 데이터 로드 함수
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
            df_refined = df_raw[[1, 4, 7, 10]].copy()
            df_refined.columns = ['자치구', '초등학교', '중학교', '고등학교']
            for col in ['초등학교', '중학교', '고등학교']:
                df_refined[col] = pd.to_numeric(df_refined[col], errors='coerce')
            df_refined['연도'] = int(year_val)
            all_dfs.append(df_refined)
        except: continue
    return pd.concat(all_dfs, ignore_index=True) if all_dfs else None

@st.cache_data
def get_geojson():
    url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json"
    return requests.get(url).json()

# --- 메인 헤더 영역 (오른쪽 상단 배치) ---
header_col1, header_col2 = st.columns([1, 1])
with header_col2:
    st.title("🏫 서울시 학업중단 알리미")
    st.markdown("""
    서울시 교육청 공공데이터를 기반으로 한 **학업중단 현황 분석 시스템**입니다.  
    지역별 격차를 해소하고 맞춤형 교육 정책을 수립하기 위한 기초 자료를 제공합니다.
    """)

# --- 사이드바: 아이콘 기반 학교급 선택 ---
with st.sidebar:
    st.subheader("🎯 분석 타겟 설정")
    level_options = {
        "👶 초등학교": "초등학교",
        "👦 중학교": "중학교",
        "🧑 고등학교": "고등학교",
        "📊 전체 평균": "전체 평균"
    }
    selected_display = st.radio("아이콘을 클릭하여 선택하세요", list(level_options.keys()), index=3)
    level = level_options[selected_display]
    st.divider()
    uploaded = st.file_uploader("파일 추가 (CSV)", accept_multiple_files=True)

df = load_data(uploaded)

if df is not None:
    if level == "전체 평균":
        df['학업중단율'] = df[['초등학교', '중학교', '고등학교']].mean(axis=1).round(2)
    else:
        df['학업중단율'] = df[level].round(2)

    # 1. 상단: 연도별 학업중단 추이
    st.header("📈 연도별 학업중단 추이")
    trend_df = df[df['자치구'].str.contains('소계', na=False)].sort_values('연도')
    latest_val = trend_df['학업중단율'].iloc[-1]
    st.info(f"💡 **분석 해석:** 현재 선택된 **{level}**의 최근 서울시 평균 중단율은 **{latest_val:.2f}%**입니다.")
    
    fig_line = px.line(trend_df, x='연도', y='학업중단율', markers=True, 
                      line_shape='spline', color_discrete_sequence=['#0083B0'], text='학업중단율')
    fig_line.update_traces(textposition="top center", texttemplate='%{text:.2f}%')
    st.plotly_chart(fig_line, use_container_width=True)

    st.divider()

    # 2. 중단: 지역별 상세 분포 (연도 선택을 바로 제시)
    st.header("🗺️ 지역별 상세 분포")
    
    # 연도 선택 슬라이더를 헤더 바로 아래에 배치
    years = sorted(df['연도'].unique())
    selected_year = st.select_slider("📅 분석할 연도를 선택하세요", options=years, value=max(years))
    
    map_df = df[(df['연도'] == selected_year) & (~df['자치구'].str.contains('소계', na=False))].copy()
    top_dist = map_df.sort_values('학업중단율', ascending=False).iloc[0]
    st.success(f"💡 **분석 해석:** {selected_year}년 기준, **{top_dist['자치구']}** 지역이 **{top_dist['학업중단율']:.
