import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import glob

st.set_page_config(layout="wide", page_title="서울시 학업중단율 통계")

# 데이터 로드 및 전처리
@st.cache_data
def load_data(uploaded_files):
    all_dfs = []
    # 기본 탑재 파일 리스트
    base_files = glob.glob("학업중단율_*.csv")
    
    # 업로드된 파일이 있다면 추가
    files_to_process = base_files
    if uploaded_files:
        files_to_process = uploaded_files

    for f in files_to_process:
        try:
            # 파일명에서 연도 추출 (예: 학업중단율_2024.csv -> 2024)
            fname = f.name if hasattr(f, 'name') else f
            year = fname.split('_')[1].split('.')[0]
            
            # 4번째 줄부터 데이터 시작 (skiprows=3)
            df_year = pd.read_csv(f, skiprows=3)
            df_year.columns = ['자치구1', '자치구2', 
                              '초등_학생수', '초등_중단자', '초등_중단율', 
                              '중등_학생수', '중등_중단자', '중등_중단율', 
                              '고등_학생수', '고등_중단자', '고등_중단율']
            df_year['연도'] = int(year)
            all_dfs.append(df_year)
        except Exception as e:
            continue
            
    if not all_dfs: return None
    return pd.concat(all_dfs, ignore_index=True)

@st.cache_data
def get_seoul_geojson():
    url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json"
    return requests.get(url).json()

# --- 실행 로직 ---
uploaded = st.sidebar.file_uploader("추가 데이터 업로드", accept_multiple_files=True)
df = load_data(uploaded)

if df is not None:
    # 1. 학교급 선택 (사이드바)
    st.sidebar.subheader("📍 분석 옵션")
    school_level = st.sidebar.selectbox(
        "학교급을 선택하세요", 
        ["초등학교", "중학교", "고등학교"]
    )
    
    # 선택에 따른 컬럼 매핑 (통계표상의 '중단율' 컬럼 사용)
    level_map = {
        "초등학교": "초등_중단율",
        "중학교": "중등_중단율",
        "고등학교": "고등_중단율"
    }
    target_col = level_map[school_level]

    # --- 상단: 연도별 추이 그래프 ---
    st.subheader(f"📈 서울시 연도별 {school_level} 학업중단율 추이")
    # '소계'행만 추출하여 연도별 정렬
    total_trend = df[df['자치구2'] == '소계'].sort_values('연도')
    
    fig_line = px.line(total_trend, x='연도', y=target_col, markers=True,
                      labels={target_col: '중단율 (%)', '연도': '연도'},
                      text=target_col)
    fig_line.update_traces(textposition="top center", line_color="#EF553B")
    st.plotly_chart(fig_line, use_container_width=True)

    st.divider()

    # --- 하단: 지도 및 상세 데이터 ---
    st.subheader(f"🗺️ {school_level} 자치구별 학업중단율 분포")
    
    # 연도 선택 슬라이더
    years = sorted(df['연도'].unique())
    selected_year = st.select_slider("조회 연도 선택", options=years, value=max(years))
    
    # 지도용 데이터 (소계 제외)
    map_df = df[(df['연도'] == selected_year) & (df['자치구2'] != '소계')]
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        geojson = get_seoul_geojson()
        fig_map = px.choropleth_mapbox(
            map_df, geojson=geojson, locations='자치구2', featureidkey="properties.name",
            color=target_col, color_continuous_scale="YlOrRd",
            mapbox_style="carto-positron", zoom=10, 
            center={"lat": 37.5665, "lon": 126.9780},
            opacity=0.8, labels={target_col: '중단율(%)'}
        )
        fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig_map, use_container_width=True)

    with col2:
        st.write(f"**{selected_year}년 구별 순위**")
        rank_df = map_df[['자치구2', target_col]].sort_values(target_col, ascending=False)
        st.dataframe(rank_df, hide_index=True, use_container_width=True)

else:
    st.warning("데이터 파일을 업로드하거나 프로젝트 폴더에 CSV 파일을 넣어주세요.")
