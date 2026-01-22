import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests

st.set_page_config(page_title="서울시 학업중단율 지도 분석", layout="wide")

# 1. 데이터 로드 및 전처리
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

# 2. 서울시 GeoJSON 및 자치구 중심점 좌표 로드 (에러 수정 버전)
@st.cache_data
def get_map_resources():
    geo_url = 'https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json'
    geo_data = requests.get(geo_url).json()
    
    rows = []
    for feature in geo_data['features']:
        name = feature['properties']['name']
        geometry = feature['geometry']
        
        # 좌표 구조 처리 (Polygon vs MultiPolygon 대응)
        if geometry['type'] == 'Polygon':
            coords = geometry['coordinates'][0]
        elif geometry['type'] == 'MultiPolygon':
            # 가장 큰 덩어리의 좌표를 사용
            coords = max(geometry['coordinates'], key=lambda x: len(x[0]))[0]
            
        # 중심점 계산
        lon = sum(p[0] for p in coords) / len(coords)
        lat = sum(p[1] for p in coords) / len(coords)
        rows.append({'자치구': name, 'lat': lat, 'lon': lon})
    
    return geo_data, pd.DataFrame(rows)

# 앱 실행
st.title("📍 서울시 자치구별 학업중단율 시각화")

uploaded_file = st.sidebar.file_uploader("데이터 업로드", type="csv")
try:
    df = load_and_preprocess(uploaded_file if uploaded_file else '학업중단율_20260122203740.csv')
    geo_json, center_df = get_map_resources()
except Exception as e:
    st.error(f"데이터 로딩 중 오류가 발생했습니다: {e}")
    st.stop()

# 학교급 선택
option = st.selectbox("색상 표시 기준을 선택하세요", ["전체 평균", "초등학교", "중학교", "고등학교"])
mapping = {"전체 평균": "전체_중단율", "초등학교": "초_중단율", "중학교": "중_중단율", "고등학교": "고_중단율"}
target_col = mapping[option]

# 3. 지도 생성
fig = px.choropleth_mapbox(
    df, geojson=geo_json, locations='자치구', featureidkey='properties.name',
    color=target_col, color_continuous_scale="YlOrRd",
    mapbox_style="carto-positron", zoom=10, 
    center={"lat": 37.5633, "lon": 126.9796}, opacity=0.7,
    hover_data={'자치구': True, '초_중단율': ':.2f', '중_중단율': ':.2f', '고_중단율': ':.2f'}
)

# 자치구 이름 표시 레이어
center_with_data = pd.merge(center_df, df, on='자치구')
fig.add_trace(go.Scattermapbox(
    lat=center_with_data['lat'],
    lon=center_with_data['lon'],
    mode='text',
    text=center_with_data['자치구'],
    textfont={'size': 13, 'weight': 'bold', 'color': 'black'},
    hoverinfo='skip'
))

fig.update_layout(margin={"r":0,"t":50,"l":0,"b":0}, height=700)
st.plotly_chart(fig, use_container_width=True)

# 4. 범례 설명
st.markdown(f"### 🎨 색상 정보: **{option}** 학업중단율")
st.write("""
- **짙은 빨간색**: 학업중단율이 상대적으로 **높음**
- **연한 노란색**: 학업중단율이 상대적으로 **낮음**
- **지도 위 텍스트**: 자치구 명칭
""")
