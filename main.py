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

# --- 사이드바: 설명 및 설정 ---
with st.sidebar:
    st.title("🏫 서울시 학업중단 알리미")
    st.markdown("""
    **본 사이트는 서울시 교육청 데이터를 기반으로 자치구별 학업중단 현황을 분석합니다.**
    
    * **추이 분석:** 10년 이상의 흐름 파악
    * **지역 비교:** 자치구별 격차 시각화
    * **심층 탐색:** 학교급별 맞춤형 데이터
    
    ---
    """)
    
    st.subheader("🎯 분석 타겟 설정")
    # 아이콘을 포함한 학교급 선택
    level_map = {
        "👶 초등학교": "초등학교",
        "👦 중학교": "중학교",
        "🧑 고등학교": "고등학교",
        "📊 전체 평균": "전체 평균"
    }
    level_display = st.radio("학교급을 선택하세요", list(level_map.keys()), index=3)
    level = level_map[level_display]
    
    st.divider()
    uploaded = st.file_uploader("추가 데이터 업로드 (CSV)", accept_multiple_files=True)

# --- 메인 화면 시작 ---
df = load_data(uploaded)

if df is not None:
    # 데이터 처리
    if level == "전체 평균":
        df['학업중단율'] = df[['초등학교', '중학교', '고등학교']].mean(axis=1).round(2)
    else:
        df['학업중단율'] = df[level].round(2)

    # 1. 상단: 추이 그래프
    st.header("📈 연도별 학업중단 추이")
    trend_df = df[df['자치구'].str.contains('소계', na=False)].sort_values('연도')
    
    # 간략 해석 자동 생성
    latest_rate = trend_df['학업중단율'].iloc[-1]
    avg_rate = trend_df['학업중단율'].mean()
    status_msg = "상승" if latest_rate > avg_rate else "하강"
    st.caption(f"💡 서울시 전체 평균은 {latest_rate}%로, 지난 10년 평균 대비 점진적 {status_msg} 추세에 있습니다.")
    
    fig_line = px.line(trend_df, x='연도', y='학업중단율', markers=True, 
                      line_shape='spline', color_discrete_sequence=['#0083B0'], text='학업중단율')
    fig_line.update_traces(textposition="top center")
    st.plotly_chart(fig_line, use_container_width=True)

    st.divider()

    # 2. 중단: 지역별 분포 (지도)
    st.header("🗺️ 지역별 상세 분포")
    years = sorted(df['연도'].unique())
    selected_year = st.select_slider("데이터 기준 연도", options=years, value=max(years))
    
    map_df = df[(df['연도'] == selected_year) & (~df['자치구'].str.contains('소계', na=False))].copy()
    
    #
