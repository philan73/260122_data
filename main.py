import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import glob
import os

# --- 1. 설정 및 데이터 로드 함수 ---
st.set_page_config(page_title="서울시 학업중단율 분석", layout="wide")

@st.cache_data
def get_seoul_geojson():
    url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/juso/2015/json/seoul_municipalities_geo_simple.json"
    return requests.get(url).json()

def load_data(uploaded_files):
    all_data = []
    # 기본 파일과 업로드된 파일 통합
    base_files = glob.glob("학업중단율_*.csv")
    file_sources = [('local', f) for f in base_files]
    if uploaded_files:
        for f in uploaded_files:
            file_sources.append(('uploaded', f))

    for source_type, file in file_sources:
        try:
            if source_type == 'local':
                year = os.path.basename(file).split('_')[1].split('.')[0]
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
            for col in df_cleaned.columns[2:-1]:
                df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')
            
            # 전체 중단율 계산
            df_cleaned['전체_중단율'] = (
                (df_cleaned['초등_중단자수'].fillna(0) + df_cleaned['중등_중단자수'].fillna(0) + df_cleaned['고등_중단자수'].fillna(0)) /
                (df_cleaned['초등_학생수'].fillna(1) + df_cleaned['중등_학생수'].fillna(1) + df_cleaned['고등_학생수'].fillna(1)) * 100
            )
            all_data.append(df_cleaned)
        except: continue
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

# --- 2. 변수 초기화 (NameError 방지) ---
school_level = "전체"
selected_year = ""

# --- 3. 사이드바 및 데이터 준비 ---
uploaded_files = st.sidebar.file_uploader("추가 CSV 업로드", accept_multiple_files=True)
df = load_data(uploaded_files)

# --- 4. 메인 화면 구성 ---
if not df.empty:
    st.title("📍 서울시 자치구별 학업중단율 지도")

    col1, col2 = st.columns(2)
    with col1:
        selected_year = st.selectbox("📅 분석 연도", sorted(df['연도'].unique(), reverse=True))
    with col2:
        school_level = st.radio("🏫 학교급 선택", ["전체", "초등", "중등", "고등"], horizontal=True)

    # 데이터 필터링
    map_df = df[(df['연도'] == selected_year) & (df['자치구별(2)'] != '소계')].copy()
    target_col = '전체_중단율' if school_level == "전체" else f"{school_level}_중단율"

    # 지도 시각화
    seoul_geo = get_seoul_geojson()
    
    # 지도 생성
    fig = px.choropleth_mapbox(
        map_df, geojson=seoul_geo, locations='자치구별(2)', featureidkey="properties.name",
        color=target_col, color_continuous_scale="Reds", opacity=0.7,
        mapbox_style="carto-positron", zoom=9.5, center={"lat": 37.5633, "lon": 126.9796},
        labels={target_col: '중단율(%)'}
    )

    # 구 이름 표시를 위한 텍스트 레이어 (위경도 수동 지정 없이 GeoJSON 기반 툴팁 활용 권장이나, 
    # 꼭 화면에 표시하려면 Scattermapbox 레이어 사용 - 여기서는 코드 안정성을 위해 기본 툴팁 강화)
    fig.update_traces(hovertemplate="<b>%{location}</b><br>중단율: %{z:.2f}%")
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=600)
    
    st.plotly_chart(fig, use_container_width=True)

    # --- 5. 설명 및 데이터 표 (에러 방지를 위해 if문 안쪽에 배치) ---
    st.markdown(f"### 🎨 지도 색상 가이드 ({school_level} 기준)")
    st.write(f"- 짙은 빨간색일
