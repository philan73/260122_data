import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import requests
import glob

st.set_page_config(page_title="서울시 학업중단율 분석", layout="wide")

# --- 1. 서울시 GeoJSON 데이터 로드 (자치구 경계) ---
@st.cache_data
def get_seoul_geojson():
    # 자치구 명칭이 '종로구', '중구' 등으로 되어 있는 표준 데이터셋입니다.
    url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/juso/2015/json/seoul_municipalities_geo_simple.json"
    response = requests.get(url)
    return response.json()

# --- 2. 데이터 로드 및 전처리 ---
def load_data(uploaded_files):
    all_data = []
    base_files = glob.glob("학업중단율_*.csv")
    file_sources = [('local', f) for f in base_files]
    if uploaded_files:
        for f in uploaded_files:
            file_sources.append(('uploaded', f))

    for source_type, file in file_sources:
        try:
            if source_type == 'local':
                year = file.split('_')[1].split('.')[0]
                df = pd.read_csv(file, encoding='utf-8')
            else:
                year = file.name.split('_')[1].split('.')[0]
                df = pd.read_csv(file, encoding='utf-8')
            
            df_cleaned = df.iloc[3:].copy()
            df_cleaned.columns = [
                '자치구별(1)', '자치구별(2)', 
                '초등_학생수', '초등_중단자수', '초등_중단율',
                '중등_학생수', '중등_중단자수', '중등_중단율',
                '고등_학생수', '고등_중단자수', '고등_중단율'
            ]
            df_cleaned['연도'] = year
            # 숫자 변환
            for col in df_cleaned.columns[2:-1]:
                df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')
            
            # 전체 중단율 계산 (초+중+고 합산)
            df_cleaned['전체_중단율'] = (
                (df_cleaned['초등_중단자수'].fillna(0) + df_cleaned['중등_중단자수'].fillna(0) + df_cleaned['고등_중단자수'].fillna(0)) /
                (df_cleaned['초등_학생수'].fillna(1) + df_cleaned['중등_학생수'].fillna(1) + df_cleaned['고등_학생수'].fillna(1)) * 100
            )
            all_data.append(df_cleaned)
        except: continue
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

# 데이터 및 GeoJSON 준비
uploaded_files = st.sidebar.file_uploader("추가 CSV 데이터 업로드", accept_multiple_files=True)
df = load_data(uploaded_files)
seoul_geo = get_seoul_geojson()

if not df.empty:
    st.title("📍 서울시 자치구별 학업중단율 지도 분석")

    # 컨트롤러
    c1, c2 = st.columns(2)
    with c1:
        selected_year = st.selectbox("📅 분석 연도 선택", sorted(df['연도'].unique(), reverse=True))
    with c2:
        school_level = st.radio("🏫 학교급 선택", ["전체 평균", "초등", "중등", "고등"], horizontal=True)

    # 데이터 필터링 (지도에는 '소계' 제외)
    map_df = df[(df['연도'] == selected_year) & (df['자치구별(2)'] != '소계')].copy()
    
    # 분석 대상 컬럼 설정
    target_col = '전체_중단율' if school_level == "전체 평균" else f"{school_level}_중단율"

    # --- 3. 지도 시각화 (Choropleth + 자치구 이름 표시) ---
    fig = px.choropleth_mapbox(
        map_df,
        geojson=seoul_geo,
        locations='자치구별(2)',        # CSV의 구 이름
        featureidkey="properties.name", # GeoJSON의 구 이름 키값
        color=target_col,
        color_continuous_scale="Reds",
        range_color=(0, map_df[target_col].max() if map_df[target_col].max() > 0 else 1),
        mapbox_style="carto-positron",
        zoom=9.5,
        center={"lat": 37.563, "lon": 126.978},
        opacity=0.6,
        labels={target_col: '중단율(%)'}
    )

    # 자치구 이름을 지도 위에 텍스트로 추가하기 위해 위경도 중심값 데이터 활용
    # (일반적으로는 별도의 좌표 데이터가 필요하지만, Plotly는 툴팁으로 대체하거나
    # scatter_mapbox를 레이어로 추가하여 텍스트를 표시할 수 있습니다.)
    
    fig.update_layout(
        margin={"r":0,"t":50,"l":0,"b":0},
        title=f"<b>{selected_year}년 {school_level} 학업중단율 분포</b> (마우스를 올리면 구 이름이 표시됩니다)"
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # --- 4. 색상 및 데이터 설명 ---
    st.markdown(f"""
    ### 🎨 지도 색상 가이드 ({school_level} 기준)
    - **짙은 빨간색**: 해당 자치구의 {school_level} 학업중단율이 서울시 내에서 상대적으로 **높음**을 나타냅니다.
    - **연한 분홍/흰색**: 학업중단율이 상대적으로 **낮음**을 나타냅니다.
    - **중단율 산
