import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import numpy as np

st.set_page_config(page_title="서울시 학업중단율 분석", layout="wide")

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

# --- 상단 헤더 ---
st.title("📑 서울시 학업중단율 분석")

uploaded_file = st.sidebar.file_uploader("데이터 업로드", type="csv")
df = load_and_preprocess(uploaded_file if uploaded_file else '학업중단율_20260122203740.csv')
geo_json, center_df = get_map_resources()

# 기준 선택
option = st.selectbox("분석 대상 학교급 선택", ["전체 평균", "초등학교", "중학교", "고등학교"])
mapping = {"전체 평균": "전체_중단율", "초등학교": "초_중단율", "중학교": "중_중단율", "고등학교": "고_중단율"}
target_col = mapping[option]

# Z-score 계산
df['Z_score'] = (df[target_col] - df[target_col].mean()) / df[target_col].std()

# --- 통계 요약 (지도 위로 이동) ---
st.info(f"💡 **통계 요약:** 현재 선택한 **{option}**의 서울시 전체 평균 중단율은 **{df[target_col].mean():.2f}%**이며, 구별 편차(표준편차)는 **{df[target_col].std():.2f}**입니다.")

# --- 지도 시각화 ---
fig = px.choropleth_mapbox(
    df, geojson=geo_json, locations='자치구', featureidkey='properties.name',
    color='Z_score', 
    range_color=[-2, 2], 
    color_continuous_scale="RdBu_r",
    mapbox_style="carto-positron", zoom=10, 
    center={"lat": 37.5633, "lon": 126.9796}, opacity=0.7,
    hover_data={'자치구': True, target_col: ':.2f', 'Z_score': ':.2f'}
)

center_with_data = pd.merge(center_df, df, on='자치구')
fig.add_trace(go.Scattermapbox(
    lat=center_with_data['lat'], lon=center_with_data['lon'],
    mode='text', text=center_with_data['자치구'],
    textfont={'size': 13, 'weight': 'bold', 'color': 'black'},
    hoverinfo='skip'
))

fig.update_layout(margin={"r":0,"t":20,"l":0,"b":0}, height=650)
st.plotly_chart(fig, use_container_width=True)

# --- 하단 안내 ---
st.subheader("📝 안내")

# 구간 설명 (지도 아래로 이동)
c1, c2, c3 = st.columns(3)
c1.error("🔴 **위험 (Z > 1.0)**: 평균보다 상당히 높음")
c2.write("⚪ **보통 (-1.0 ≤ Z ≤ 1.0)**: 서울시 평균 수준")
c3.info("🔵 **안정 (Z < -1.0)**: 평균보다 상당히 낮음")

st.write("---")

# 일반인 대상 보조 설명 (보기 좋게 구성)
st.markdown("### 💡 쉽게 이해하기")
with st.container():
    st.write("""
    이 지도는 단순히 '중단율이 높다, 낮다'를 넘어, **서울시 전체 평균과 비교했을 때 해당 자치구가 얼마나 유난히 튀는가**를 보여줍니다.
    
    * **왜 숫자가 아니라 색으로 보나요?** 학교급마다 중단율의 기준치가 다릅니다. (예: 고등학교는 원래 초등학교보다 중단율이 높습니다.)  
      따라서 숫자로만 보면 고등학교는 항상 위험해 보일 수 있습니다. 이를 방지하기 위해 **각 학교급 내에서의 평균**을 기준으로 색을 칠했습니다.
      
    * **Z-score(표준점수)란 무엇인가요?** 평균으로부터의 '거리'입니다. 0이면 딱 중간이고, 1이면 평균보다 '한 걸음' 더 멀리(높게) 떨어져 있다는 뜻입니다. 
      보통 **1.0(빨간색)**이 넘어가면 해당 지역에 교육 정책적 관심이 시급함을 학술적으로 의미합니다.
    
    * **색깔의 의미** - **붉은색**: 서울시 다른 구들에 비해 학생들의 학업 중단이 빈번하게 일어나는 지역입니다.
      - **푸른색**: 서울시 내에서 상대적으로 학생들이 학업을 안정적으로 지속하고 있는 지역입니다.
    """)
