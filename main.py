import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import glob

st.set_page_config(layout="wide", page_title="서울시 학업중단율 분석")

# 1. 데이터 로드 (기본 탑재 파일 + 업로드 파일)
@st.cache_data
def load_data(uploaded_files):
    all_dfs = []
    # 프로젝트 폴더 내의 모든 관련 CSV 파일 탐색
    base_files = glob.glob("학업중단율_*.csv")
    
    # 파일 리스트 통합 (중복 방지)
    file_list = base_files
    if uploaded_files:
        file_list = base_files + uploaded_files

    for f in file_list:
        try:
            # 파일 이름에서 연도 추출
            fname = f.name if hasattr(f, 'name') else f
            year_str = fname.split('_')[1].split('.')[0]
            
            # 실제 데이터는 4행부터 시작 (index 3)
            temp_df = pd.read_csv(f, skiprows=3)
            # 통계표 형식에 맞춘 컬럼명 재정의
            temp_df.columns = [
                '자치구1', '자치구2', 
                '초등_학생', '초등_중단', '초등_율', 
                '중등_학생', '중등_중단', '중등_율', 
                '고등_학생', '고등_중단', '고등_율'
            ]
            temp_df['연도'] = int(year_str)
            all_dfs.append(temp_df)
        except Exception as e:
            continue
            
    if not all_dfs:
        return None
    return pd.concat(all_dfs, ignore_index=True)

@st.cache_data
def get_seoul_geo():
    url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json"
    return requests.get(url).json()

# --- 메인 실행부 ---
st.sidebar.header("📊 필터 설정")
uploaded = st.sidebar.file_uploader("CSV 추가 업로드", accept_multiple_files=True)
full_df = load_data(uploaded)

if full_df is not None:
    # 학교급 선택 버튼
    level = st.sidebar.radio("학교급 선택", ["전체", "초등학교", "중학교", "고등학교"])
    
    # 선택된 학교급에 따른 데이터 컬럼 매핑
    if level == "전체":
        # 전체 선택 시 세 학교급의 율을 평균내어 추이를 보여줌
        full_df['selected_rate'] = full_df[['초등_율', '중등_율', '고등_율']].mean(axis=1)
    else:
        mapping = {"초등학교": "초등_율", "중학교": "중등_율", "고등학교": "고등_율"}
        full_df['selected_rate'] = full_df[mapping[level]]

    # --- [상단] 연도별 추이 그래프 ---
    st.subheader(f"📈 서울시 연도별 학업중단율 추이 ({level})")
    # '소계' 데이터가 서울시 전체 평균임
    trend_df = full_df[full_df['자치구2'] == '소계'].sort_values('연도')
    
    if not trend_df.empty:
        fig_line = px.line(trend_df, x='연도', y='selected_rate', markers=True,
                          labels={'selected_rate': '학업중단율 (%)', '연도': '연도'},
                          text='selected_rate')
        fig_line.update_traces(textposition="top center", line_color="#00CC96")
        fig_line.update_layout(xaxis=dict(tickmode='linear')) # 연도가 끊기지 않게 표시
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.error("추이 데이터를 불러올 수 없습니다. 파일 형식을 확인해주세요.")

    st.divider()

    # --- [하단] 지도 시각화 ---
    st.subheader(f"🗺️ {level} 지역별 분포")
    selected_year = st.select_slider("조회 연도", options=sorted(full_df['연도'].unique()), value=max(full_df['연도']))
    
    map_df = full_df[(full_df['연도'] == selected_year) & (full_df['자치구2'] != '소계')]
    
    geo_json = get_seoul_geo()
    fig_map = px.choropleth_mapbox(
        map_df, geojson=geo_json, locations='자치구2', featureidkey="properties.name",
        color='selected_rate', color_continuous_scale="Reds",
        mapbox_style="carto-positron", zoom=9.5, 
        center={"lat": 37.5665, "lon": 126.9780},
        labels={'selected_rate': '중단율(%)'}
    )
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_map, use_container_width=True)

else:
    st.info("데이터 파일을 읽어오는 중입니다. 파일이 없다면 '학업중단율_2024.csv'와 같은 형식으로 업로드해주세요.")
