import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import re

# 1. 페이지 설정 및 디자인 스타일
st.set_page_config(page_title="서울시 학업중단율 분석 포털", layout="wide")

# CSS 스타일 적용 (오류 수정: unsafe_allow_html=True)
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    h1 { color: #1e3a8a; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_and_merge_data(uploaded_files):
    all_data = []
    if not uploaded_files: return pd.DataFrame()
    for file in uploaded_files:
        try:
            df_raw = pd.read_csv(file, header=None)
            first_row_text = " ".join(df_raw.iloc[0].astype(str))
            year_match = re.search(r'(\d{4})', first_row_text)
            year = year_match.group(1) if year_match else "Unknown"
            data = df_raw.iloc[3:].copy()
            data.columns = ['자치구별1', '자치구', '초_학생', '초_중단자', '초_중단율', 
                            '중_학생', '중_중단자', '중_중단율', '고_학생', '고_중단자', '고_중단율']
            for col in data.columns[2:]:
                data[col] = pd.to_numeric(data[col], errors='coerce')
            data['연도'] = year
            data['전체_중단율'] = data[['초_중단율', '중_중단율', '고_중단율']].mean(axis=1)
            all_data.append(data)
        except: continue
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

@st.cache_data
def get_map_resources():
    geo_url = 'https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json'
    geo_data = requests.get(geo_url).json()
    rows = []
    for feature in geo_data['features']:
        name = feature['properties']['name']
        geom = feature['geometry']
        coords = geom['coordinates'][0]
        if geom['type'] == 'MultiPolygon':
            coords = max(geom['coordinates'], key=lambda x: len(x[0]))[0]
        lon = sum(p[0] for p in coords) / len(coords)
        lat = sum(p[1] for p in coords) / len(coords)
        rows.append({'자치구': name, 'lat': lat, 'lon': lon})
    return geo_data, pd.DataFrame(rows)

# --- 실행부 ---
st.title("📊 서울시 학업중단율 분석 포털")
st.caption("2014년 - 2024년 시계열 통합 데이터 기반 상대적 위치 분석")

uploaded_files = st.sidebar.file_uploader("📂 연도별 CSV 파일 다중 선택", type="csv", accept_multiple_files=True)
full_df = load_and_merge_data(uploaded_files)

if full_df.empty:
    st.info("👈 왼쪽 사이드바에서 분석할 연도별 CSV 파일들을 모두 선택해 주세요.")
    st.stop()

geo_json, center_df = get_map_resources()
available_years = sorted([y for y in full_df['연도'].unique() if y.isdigit()], reverse=True)

# --- 필터 ---
st.write("### 🔍 분석 조건 설정")
c1, c2 = st.columns(2)
with c1:
    selected_year = st.selectbox("📅 분석 연도 선택", available_years)
with c2:
    option = st.selectbox("🏫 학교급 선택", ["전체 평균", "초등학교", "중학교", "고등학교"])

mapping = {"전체 평균": "전체_중단율", "초등학교": "초_중단율", "중학교": "중_중단율", "고등학교": "고_중단율"}
target_col = mapping[option]

# 데이터 계산
df_year = full_df[(full_df['연도'] == selected_year) & (full_df['자치구'] != '소계')].copy()
mean_val = df_year[target_col].mean()
std_val = df_year[target_col].std()
df_year['Z_score'] = (df_year[target_col] - mean_val) / std_val if std_val > 0 else 0

# --- 핵심 지표 카드 ---
st.write("---")
m1, m2, m3 = st.columns(3)
m1.metric("분석 연도", f"{selected_year}년")
m2.metric(f"{option} 평균 중단율", f"{mean_val:.2f}%")
m3.metric("구별 편차(표준편차)", f"{std_val:.2f}")
st.write("---")

# --- 대시보드 ---
tab1, tab2 = st.tabs(["📈 시계열 추이 확인", "🗺️ 자치구별 위치 분석"])

with tab1:
    st.subheader(f"서울시 전체 연도별 {option} 중단율 흐름")
    trend_data = full_df[full_df['자치구'] == '소계'].sort_values('연도')
    fig_line = px.line(trend_data, x='연도', y=target_col, markers=True, 
                       color_discrete_sequence=['#2563eb'], template="plotly_white")
    st.plotly_chart(fig_line, use_container_width=True)

with tab2:
    st.subheader(f"{selected_year}년 자치구별 상대적 위치 (Z-score)")
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
        textfont={'size': 12, 'weight': 'bold', 'color': '#1e293b'}, hoverinfo='skip'
    ))
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=600)
    st.plotly_chart(fig_map, use_container_width=True)

# --- 하단 안내 ---
st.write("---")
with st.expander("📌 분석 결과 및 기호 안내", expanded=True):
    col_info1, col_info2 = st.columns([1, 2])
    with col_info1:
        st.error("🔴 **위험 (Z > 1.0)**")
        st.write("평균보다 유의미하게 중단율이 높은 지역")
        st.info("🔵 **안정 (Z < -1.0)**")
        st.write("평균보다 유의미하게 중단율이 낮은 지역")
    with col_info2:
        st.markdown(f"""
        **Z-Score(표준점수)란?** 단순 수치가 아닌, 서울시 평균과 해당 지역의 차이를 '표준편차' 단위로 나타낸 것입니다.  
        현재 선택된 **{selected_year}년 {option}**의 평균은 **{mean_val:.2f}%**입니다. 이 수치보다 훨씬 높은 곳은 빨간색, 낮은 곳은 파란색으로 표시됩니다.
        """)
