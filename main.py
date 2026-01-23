import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import re

st.set_page_config(page_title="서울시 학업중단율 분석", layout="wide")

# 1. 데이터 통합 로드 및 전처리 (연도 추출 로직 수정)
@st.cache_data
def load_and_merge_data(uploaded_files):
    all_data = []
    
    # 업로드된 파일이 없으면 기본 파일 리스트 사용
    if not uploaded_files:
        files = [f'학업중단율_{y}.csv' for y in range(2014, 2025) if y != 2021] # 예시
    else:
        files = uploaded_files

    for file in files:
        try:
            # 헤더 없이 읽어서 연도부터 파악
            df_raw = pd.read_csv(file, header=None)
            
            # 첫 번째 행의 모든 값 중 숫자 4자리(연도) 찾기
            first_row_str = " ".join(df_raw.iloc[0].astype(str))
            year_match = re.search(r'(\d{4})', first_row_str)
            year = year_match.group(1) if year_match else "Unknown"
            
            # 실제 데이터는 4행(index 3)부터
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
            continue
            
    if not all_data:
        return pd.DataFrame()
        
    return pd.concat(all_data, ignore_index=True)

# 2. 지도 리소스 로드
@st.cache_data
def get_map_resources():
    geo_url = 'https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json'
    try:
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
    except:
        return {}, pd.DataFrame()

# --- 실행부 ---
st.title("📑 서울시 학업중단율 분석")

uploaded_files = st.sidebar.file_uploader("연도별 CSV 파일들을 모두 선택하세요", type="csv", accept_multiple_files=True)
full_df = load_and_merge_data(uploaded_files)

if full_df.empty:
    st.warning("데이터 파일을 업로드해주세요.")
    st.stop()

geo_json, center_df = get_map_resources()

# 연도 및 학교급 선택 (중복 제거 및 정렬)
col_a, col_b = st.columns(2)
with col_a:
    available_years = sorted([y for y in full_df['연도'].unique() if y.isdigit()], reverse=True)
    selected_year = st.selectbox("📅 분석 연도 선택", available_years)
with col_b:
    option = st.selectbox("🏫 분석 대상 학교급 선택", ["전체 평균", "초등학교", "중학교", "고등학교"])

mapping = {"전체 평균": "전체_중단율", "초등학교": "초_중단율", "중학교": "중_중단율", "고등학교": "고_중단율"}
target_col = mapping[option]

# 현재 연도 데이터 필터링 및 Z-score
df_year = full_df[full_df['연도'] == selected_year].copy()
df_year = df_year[df_year['자치구'] != '소계']
df_year['Z_score'] = (df_year[target_col] - df_year[target_col].mean()) / df_year[target_col].std()

# --- 통계 요약 ---
st.info(f"💡 **{selected_year}년 통계:** 서울시 전체 평균 중단율은 **{df_year[target_col].mean():.2f}%**입니다.")

# --- 1. 연도별 추이 그래프 ---
st.subheader(f"📈 서울시 연도별 {option} 중단율 변화 추이")
# 소계 데이터만 모아서 연도순 정렬
trend_data = full_df[full_df['자치구'] == '소계'].sort_values('연도')
fig_line = px.line(trend_data, x='연도', y=target_col, markers=True, 
                   title=f"서울시 전체 {option} 중단율 추이 (2014-2024)")
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
