import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import numpy as np

st.set_page_config(page_title="서울시 학업중단율 학술 분석", layout="wide")

@st.cache_data
def load_and_preprocess(file):
    df_raw = pd.read_csv(file)
    data = df_raw.iloc[3:].copy()
    data.columns = ['자치구별1', '자치구', '초_학생', '초_중단자', '초_중단율', 
                    '중_학생', '중_중단자', '중_중단율', '고_학생', '고_중단자', '고_중단율']
    data = data[data['자치구'] != '소계'].reset_index(drop=True)
    for col in data.columns[2:]:
        data[col] = pd.to_numeric(data[col], errors='coerce')
    data['전체_중단율'] = data[['초_중단율', '중_중단율', '고_중단율']].mean(axis=1)
    return data

@st.cache_data
def get_map_resources():
    geo_url = 'https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json'
    geo_data = requests.get(geo_url).json()
    rows = []
    for feature in geo_data['features']:
        name = feature['properties']['name']
        geometry = feature['geometry']
        coords = geometry['coordinates'][0]
        if geometry['type'] == 'MultiPolygon':
            coords = max(geometry['coordinates'], key=lambda x: len(x[0]))[0]
        lon = sum(p[0] for p in coords) / len(coords)
        lat = sum(p[1] for p in coords) / len(coords)
        rows.append({'자치구': name, 'lat': lat, 'lon': lon})
    return geo_data, pd.DataFrame(rows)

st.title("🎓 학술적 기준(Z-score) 기반 학업중단율 분석")

uploaded_file = st.sidebar.file_uploader("데이터 업로드", type="csv")
df = load_and_preprocess(uploaded_file if uploaded_file else '학업중단율_20260122203740.csv')
geo_json, center_df = get_map_resources()

# 분석 기준 선택
option = st.selectbox("분석 대상 학교급 선택", ["전체 평균", "초등학교", "중학교", "고등학교"])
mapping = {"전체 평균": "전체_중단율", "초등학교": "초_중단율", "중학교": "중_중단율", "고등학교": "고_중단율"}
target_col = mapping[option]

# Z-score 계산
df['Z_score'] = (df[target_col] - df[target_col].mean()) / df[target_col].std()

# 지도 시각화 (중심 0점을 기준으로 대칭 색상 적용)
fig = px.choropleth_mapbox(
    df, geojson=geo_json, locations='자치구', featureidkey='properties.name',
    color='Z_score', 
    range_color=[-2, 2], # -2표준편차 ~ +2표준편차 범위 고정
    color_continuous_scale="RdBu_r", # 빨강(높음) - 하양(평균) - 파랑(낮음)
    mapbox_style="carto-positron", zoom=10, 
    center={"lat": 37.5633, "lon": 126.9796}, opacity=0.7,
    hover_data={'자치구': True, target_col: ':.2f', 'Z_score': ':.2f'}
)

# 자치구 이름 표시
center_with_data = pd.merge(center_df, df, on='자치구')
fig.add_trace(go.Scattermapbox(
    lat=center_with_data['lat'], lon=center_with_data['lon'],
    mode='text', text=center_with_data['자치구'],
    textfont={'size': 13, 'weight': 'bold', 'color': 'black'},
    hoverinfo='skip'
))

fig.update_layout(margin={"r":0,"t":50,"l":0,"b":0}, height=700)
st.plotly_chart(fig, use_container_width=True)

# 학술적 해석 가이드
st.markdown(f"### 📊 학술적 해석 가이드: {option}")
col1, col2, col3 = st.columns(3)
col1.error("🔴 **위험 (Z > 1.0)**: 평균보다 유의미하게 높음")
col2.write("⚪ **보통 (-1.0 ≤ Z ≤ 1.0)**: 서울시 평균 수준")
col3.info("🔵 **안정 (Z < -1.0)**: 평균보다 유의미하게 낮음")

st.info(f"현재 {option}의 서울시 평균 중단율은 **{df[target_col].mean():.2f}%**이며, 표준편차는 **{df[target_col].std():.2f}**입니다.")
