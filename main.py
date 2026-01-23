import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import glob

st.set_page_config(layout="wide", page_title="서울시 학업중단율 분석")

# 1. 데이터 로드 함수 (위치 기반으로 컬럼을 강제 지정)
@st.cache_data
def load_data(uploaded_files):
    all_dfs = []
    # 로컬에 저장된 기본 파일들
    base_files = glob.glob("학업중단율_*.csv")
    
    # 처리할 파일 목록 통합
    file_list = []
    if uploaded_files:
        file_list = uploaded_files
    else:
        file_list = base_files

    for f in file_list:
        try:
            # 파일명에서 연도 추출
            fname = f.name if hasattr(f, 'name') else f
            year_val = fname.split('_')[1].split('.')[0]
            
            # 상단 3줄 무시하고 데이터 읽기
            df_raw = pd.read_csv(f, skiprows=3, header=None)
            
            # 필요한 컬럼만 추출 (0:자치구1, 1:자치구2, 4:초등율, 7:중등율, 10:고등율)
            df_refined = df_raw[[0, 1, 4, 7, 10]].copy()
            df_refined.columns = ['자치구1', '자치구2', '초등학교', '중학교', '고등학교']
            
            # 숫자 데이터로 변환 (문자열 등이 섞여있을 경우 대비)
            for col in ['초등학교', '중학교', '고등학교']:
                df_refined[col] = pd.to_numeric(df_refined[col], errors='coerce')
                
            df_refined['연도'] = int(year_val)
            all_dfs.append(df_refined)
        except Exception:
            continue
            
    if not all_dfs: return None
    return pd.concat(all_dfs, ignore_index=True)

@st.cache_data
def get_geojson():
    url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json"
    return requests.get(url).json()

# --- 화면 구성 ---
st.sidebar.header("📊 데이터 설정")
uploaded = st.sidebar.file_uploader("파일 업로드 (학업중단율_YYYY.csv)", accept_multiple_files=True)
df = load_data(uploaded)

if df is not None:
    # 2. 학교급 선택
    level = st.sidebar.selectbox("확인할 학교급", ["초등학교", "중학교", "고등학교", "전체 평균"])
    
    # 선택에 따른 값 설정
    if level == "전체 평균":
        df['target'] = df[['초등학교', '중학교', '고등학교']].mean(axis=1)
    else:
        df['target'] = df[level]

    # --- [상단] 연도별 추이 그래프 ---
    st.subheader(f"📈 서울시 연도별 {level} 학업중단율 추이")
    
    # '소계' 행이 서울시 전체 데이터임
    trend_df = df[df['자치구2'].str.contains('소계', na=False)].sort_values('연도')
    
    if not trend_df.empty:
        fig_line = px.line(trend_df, x='연도', y='target', markers=True,
                          labels={'target': '중단율 (%)', '연도': '연도'},
                          text=trend_df['target'].round(2))
        fig_line.update_traces(textposition="top center", line_color="#FF4B4B", line_width=3)
        fig_line.update_xaxes(type='category') # 연도를 중복 없이 순서대로 표시
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.error("연도별 데이터를 찾을 수 없습니다. 파일 내 '소계' 행이 있는지 확인해주세요.")

    st.divider()

    # --- [하단] 지도 시각화 ---
    st.subheader(f"🗺️ {level} 지역별 분포")
    selected_year = st.select_slider("연도 선택", options=sorted(df['연도'].unique()), value=max(df['연도']))
    
    map_df = df[(df['연도'] == selected_year) & (~df['자치구2'].str.contains('소계', na=False))]
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        geo = get_geojson()
        fig_map = px.choropleth_mapbox(
            map_df, geojson=geo, locations='자치구2', featureidkey="properties.name",
            color='target', color_continuous_scale="Reds",
            mapbox_style="carto-positron", zoom=9.5, 
            center={"lat": 37.5665, "lon": 126.9780},
            labels={'target': '중단율(%)'}
        )
        fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig_map, use_container_width=True)
        
    with col2:
        st.write(f"**{selected_year}년 자치구 순위**")
        st.dataframe(map_df[['자치구2', 'target']].sort_values('target', ascending=False), hide_index=True)

else:
    st.warning("데이터 로드에 실패했습니다. 사이드바에서 CSV 파일을 업로드해주세요.")
