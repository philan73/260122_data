import streamlit as st
import pandas as pd
import plotly.express as px
import requests

st.set_page_config(page_title="서울시 학업중단율 지도", layout="wide")

# 1. 데이터 로드 및 전처리 (중단율 추출)
@st.cache_data
def load_map_data(file):
    df_raw = pd.read_csv(file)
    # 실제 데이터는 4행(index 3)부터 시작
    data = df_raw.iloc[3:].copy()
    data.columns = ['자치구별1', '자치구', '초_학생', '초_중단자', '초_중단율', 
                    '중_학생', '중_중단자', '중_중단율', '고_학생', '고_중단자', '고_중단율']
    
    # '소계' 제외 및 수치형 변환
    data = data[data['자치구'] != '소계']
    for col in data.columns[2:]:
        data[col] = pd.to_numeric(data[col], errors='coerce')
    
    return data

# 2. 서울시 GeoJSON (지형 정보) 로드
@st.cache_data
def get_geojson():
    # 서울시 자치구 경계 데이터
    url = 'https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json'
    return requests.get(url).json()

st.title("🗺️ 서울시 자치구별 학업중단율 지도")

uploaded_file = st.sidebar.file_uploader("데이터 업로드", type="csv")

if uploaded_file:
    df = load_map_data(uploaded_file)
else:
    df = load_map_data('학업중단율_20260122203740.csv')

geo = get_geojson()

# 학교급 선택
option = st.selectbox("지도에 표시할 기준 학교급을 선택하세요", ["초등학교", "중학교", "고등학교"])
target_col = '초_중단율' if option == '초등학교' else ('중_중단율' if option == '중학교' else '고_중단율')

# 3. Plotly 지도 시각화
fig = px.choropleth_mapbox(
    df,
    geojson=geo,
    locations='자치구',      # 데이터의 자치구 컬럼
    featureidkey='properties.name', # GeoJSON의 이름 속성
    color=target_col,       # 색상 기준
    color_continuous_scale="Reds",
    mapbox_style="carto-positron",
    zoom=10,
    center={"lat": 37.5633, "lon": 126.9796},
    opacity=0.6,
    # 마우스 올렸을 때 보여줄 정보(Hover)
    hover_data={
        '자치구': True,
        '초_중단율': ':.2f',
        '중_중단율': ':.2f',
        '고_중단율': ':.2f'
    },
    labels={
        '초_중단율': '초등(%)',
        '중_중단율': '중등(%)',
        '고_중단율': '고등(%)'
    }
)

fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, height=600)
st.plotly_chart(fig, use_container_width=True)

st.info("💡 지도 위의 자치구에 마우스를 올리면 학교급별 상세 학업중단율을 확인할 수 있습니다.")
