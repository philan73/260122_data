import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import requests
import glob

# 페이지 설정
st.set_page_config(layout="wide", page_title="서울시 학업중단율 지도 대시보드")

# 1. 데이터 로드 및 전처리 함수
@st.cache_data
def load_combined_data(uploaded_files=None):
    all_data = []
    # 로컬 경로의 파일들 (업로드된 파일이 없을 경우 대비)
    base_files = glob.glob("학업중단율_*.csv")
    
    source_files = uploaded_files if uploaded_files else base_files

    for file in source_files:
        try:
            # 파일이 업로드 객체인지 경로 문자열인지 확인
            fname = file.name if hasattr(file, 'name') else file
            year = fname.split('_')[1].split('.')[0]
            
            df = pd.read_csv(file, skiprows=3)
            df.columns = ['자치구(1)', '자치구(2)', 
                         '초등_학생', '초등_중단자', '초등_율',
                         '중등_학생', '중등_중단자', '중등_율',
                         '고등_학생', '고등_중단자', '고등_율']
            df['연도'] = int(year)
            all_data.append(df)
        except:
            continue
            
    if not all_data: return None
    return pd.concat(all_data, ignore_index=True)

# 2. GeoJSON 로드 (서울시 자치구 경계)
@st.cache_data
def get_seoul_geojson():
    url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json"
    return requests.get(url).json()

# 앱 인터페이스 시작
st.title("📍 서울시 학업중단율 데이터 시각화")

# 사이드바 설정
st.sidebar.header("⚙️ 분석 설정")
uploaded = st.sidebar.file_uploader("CSV 데이터 추가", accept_multiple_files=True)
df = load_combined_data(uploaded)

if df is not None:
    # 학교급 선택
    school_level = st.sidebar.selectbox(
        "학교급 선택", 
        ["전체 평균", "초등학교", "중학교", "고등학교"]
    )
    
    # 분석에 사용할 컬럼 매핑
    col_map = {
        "전체 평균": ['초등_율', '중등_율', '고등_율'],
        "초등학교": ['초등_율'],
        "중학교": ['중등_율'],
        "고등학교": ['고등_율']
    }
    
    # 데이터 정리: 선택한 학교급에 따른 평균 중단율 계산
    df['선택_중단율'] = df[col_map[school_level]].mean(axis=1)
    
    # --- [상단] 연도별 추이 그래프 ---
    st.subheader(f"📈 연도별 학업중단율 추이 ({school_level})")
    
    # '소계' 데이터만 추출
    total_trend = df[df['자치구(2)'] == '소계'].sort_values('연도')
    
    fig_line = px.line(total_trend, x='연도', y='선택_중단율', markers=True,
                      labels={'선택_중단율': '중단율 (%)', '연도': '연도'},
                      template='plotly_white')
    fig_line.update_traces(line_color='#FF4B4B', line_width=3)
    st.plotly_chart(fig_line, use_container_width=True)

    st.markdown("---")

    # --- [하단] 지도 시각화 ---
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("🗺️ 지역별 지도 확인")
        selected_year = st.slider("확인할 연도 선택", 
                                 min_value=int(df['연도'].min()), 
                                 max_value=int(df['연도'].max()), 
                                 value=int(df['연도'].max()))
        
        # 선택된 연도의 자치구별 데이터 (소계 제외)
        map_df = df[(df['연도'] == selected_year) & (df['자치구(2)'] != '소계')]
        
        st.write(f"**{selected_year}년 {school_level} 데이터 요약**")
        st.dataframe(map_df[['자치구(2)', '선택_중단율']].sort_values('선택_중단율', ascending=False), height=300)

    with col2:
        geo_data = get_seoul_geojson()
        
        fig_map = px.choropleth_mapbox(
            map_df,
            geojson=geo_data,
            locations='자치구(2)',
            featureidkey="properties.name",
            color='선택_중단율',
            color_continuous_scale="Reds",
            mapbox_style="carto-positron",
            zoom=10,
            center={"lat": 37.5665, "lon": 126.9780},
            opacity=0.7,
            labels={'선택_중단율': '중단율(%)'},
            title=f"{selected_year}년 자치구별 {school_level} 학업중단율 분포"
        )
        fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
        st.plotly_chart(fig_map, use_container_width=True)

else:
    st.info("왼쪽 사이드바에 데이터를 업로드하거나 프로젝트 폴더에 CSV 파일을 넣어주세요.")
