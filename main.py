import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import numpy as np

st.set_page_config(page_title="서울시 학업중단율 시계열 분석", layout="wide")

# 1. 여러 연도 데이터 통합 로드 및 전처리
@st.cache_data
def load_and_merge_data(uploaded_files):
    all_data = []
    
    # 파일이 업로드되지 않았을 때 기본 파일 리스트 (예시)
    if not uploaded_files:
        # 실제 환경에 있는 파일명들로 대체 필요
        files = ['학업중단율_2024.csv', '학업중단율_2020.csv', '학업중단율_2019.csv', 
                 '학업중단율_2018.csv', '학업중단율_2017.csv', '학업중단율_2016.csv', 
                 '학업중단율_2015.csv', '학업중단율_2014.csv']
    else:
        files = uploaded_files

    for file in files:
        try:
            df_raw = pd.read_csv(file)
            # 연도 추출 (1행 3열에 연도가 적혀 있는 구조 활용)
            year = str(df_raw.iloc[0, 2]).strip()
            
            data = df_raw.iloc[3:].copy()
            data.columns = ['자치구별1', '자치구', '초_학생', '초_중단자', '초_중단율', 
                            '중_학생', '중_중단자', '중_중단율', '고_학생', '고_중단자', '고_중단율']
            
            # 수치형 변환
            for col in data.columns[2:]:
                data[col] = pd.to_numeric(data[col], errors='coerce')
            
            data['연도'] = year
            data['전체_중단율'] = data[['초_중단율', '중_중단율', '고_중단율']].mean(axis=1)
            all_data.append(data)
        except Exception as e:
            st.warning(f"파일 {file} 처리 중 오류 발생: {e}")
            
    return pd.concat(all_data, ignore_index=True)

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

# --- 실행부 ---
st.title("📑 서울시 학업중단율 분석")

uploaded_files = st.sidebar.file_uploader("연도별 CSV 파일들을 모두 선택하세요", type="csv", accept_multiple_files=True)
full_df = load_and_merge_data(uploaded_files)
geo_json, center_df = get_map_resources()

# 연도 및 학교급 선택
col_a, col_b = st.columns(2)
with col_a:
    available_years = sorted(full_df['연도'].unique(), reverse=True)
    selected_year = st.selectbox("📅 분석 연도 선택", available_years)
with col_b:
    option = st.selectbox("🏫 분석 대상 학교급 선택", ["전체 평균", "초등학교", "중학교", "고등학교"])

mapping = {"전체 평균": "전체_중단율", "초등학교": "초_중단율", "중학교": "중_중단율", "고등학교": "고_중단율"}
target_col = mapping[option]

# 현재 연도 데이터 필터링 및 Z-score 계산
df_year = full_df[full_df['연도'] == selected_year].copy()
df_year = df_year[df_year['자치구'] != '소계']
df_year['Z_score'] = (df_year[target_col] - df_year[target_col].mean()) / df_year[target_col].std()

# --- 통계 요약 ---
st.info(f"💡 **{selected_year}년 통계:** 서울시 전체 평균 중단율은 **{df_year[target_col].mean():.2f}%**입니다.")

# --- 1. 연도별 추이 그래프 (신규 추가) ---
st.subheader(f"📈 서울시 연도별 {option} 중단율 변화 추이")
trend_data = full_df[full_df['자치구'] == '소계'].sort_values('연도')
fig_line = px.line(trend_data, x='연도', y=target_col, markers=True, 
                   line_shape='linear', title=f"서울시 전체 {option} 중단율 추이")
st.plotly_chart(fig_line, use_container_width=True)

# --- 2. 지도 시각화 ---
st.subheader(f"🗺️ {selected_year}년 자치구별 상대적 위치 (Z-score)")
fig_map = px.choropleth_mapbox(
    df_year, geojson=geo_json, locations='자치구', featureidkey='properties.name',
    color='Z_score', range_color=[-2, 2], color_continuous_scale="RdBu_r",
    mapbox_style="carto-positron", zoom=10, 
    center={"lat": 37.5633, "lon": 126.9796}, opacity=0.7,
    hover_data={'자치구': True, target_col: ':.2f', 'Z_score': ':.2f'}
)

center_with_data = pd.merge(center_df, df_year, on='자치구')
fig_map.add_trace(go.Scattermapbox(
    lat=center_with_data['lat'], lon=center_with_data['lon'],
    mode='text', text=center_with_data['자치구'],
    textfont={'size': 12, 'weight': 'bold', 'color': 'black'},
    hoverinfo='skip'
))

fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=600)
st.plotly_chart(fig_map, use_container_width=True)

# --- 안내 섹션 ---
st.subheader("📝 안내")
c1, c2, c3 = st.columns(3)
c1.error("🔴 **위험 (Z > 1.0)**: 평균보다 상당히 높음")
c2.write("⚪ **보통 (-1.0 ≤ Z ≤ 1.0)**: 서울시 평균 수준")
c3.info("🔵 **안정 (Z < -1.0)**: 평균보다 상당히 낮음")

st.markdown("### 💡 쉽게 이해하기")
st.write(f"""
- 위 그래프는 지난 **{available_years[-1]}년부터 {available_years[0]}년까지** 서울시 전체의 흐름을 보여줍니다.
- 지도는 선택하신 **{selected_year}년**에 어느 구가 상대적으로 관리가 더 필요했는지를 보여줍니다.
- **파란색**으로 갈수록 해당 연도에 학생들이 학교에 잘 적응하고 있음을, **빨간색**으로 갈수록 학업 중단 예방책이 더 필요함을 의미합니다.
""")
