import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import re

# 페이지 설정
st.set_page_config(page_title="서울시 학업중단율 데이터 포털", layout="wide")

# 스타일 커스텀
st.markdown("""
    <style>
    .main { background-color: #f9f9f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .css-10trblm { color: #1f77b4; }
    </style>
    """, unsafe_allow_stdio=True)

@st.cache_data
def load_and_merge_data(uploaded_files):
    all_data = []
    if not uploaded_files: return pd.DataFrame()

    for file in uploaded_files:
        try:
            df_raw = pd.read_csv(file, header=None)
            # 연도 추출 (정규식 사용)
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
        geometry = feature['geometry']
        coords = geometry['coordinates'][0]
        if geometry['type'] == 'MultiPolygon':
            coords = max(geometry['coordinates'], key=lambda x: len(x[0]))[0]
        lon = sum(p[0] for p in coords) / len(coords)
        lat = sum(p[1] for p in coords) / len(coords)
        rows.append({'자치구': name, 'lat': lat, 'lon': lon})
    return geo_data, pd.DataFrame(rows)

# --- 상단 타이틀 ---
st.title("📊 서울시 학업중단율 데이터 포털")
st.caption("2014년 - 2024년 시계열 데이터 통합 분석 대시보드")

uploaded_files = st.sidebar.file_uploader("📂 연도별 CSV 파일 다중 선택", type="csv", accept_multiple_files=True)
full_df = load_and_merge_data(uploaded_files)

if full_df.empty:
    st.info("💡 사이드바에서 CSV 파일들을 업로드하면 분석이 시작됩니다.")
    st.stop()

geo_json, center_df = get_map_resources()
available_years = sorted([y for y in full_df['연도'].unique() if y.isdigit()], reverse=True)

# --- 필터 섹션 ---
with st.container():
    c1, c2 = st.columns(2)
    with c1:
        selected_year = st.selectbox("📅 분석 연도", available_years)
    with c2:
        option = st.selectbox("🏫 학교급", ["전체 평균", "초등학교", "중학교", "고등학교"])

mapping = {"전체 평균": "전체_중단율", "초등학교": "초_중단율", "중학교": "중_중단율", "고등학교": "고_중단율"}
target_col = mapping[option]

# 데이터 필터링 및 Z-score 계산
df_year = full_df[(full_df['연도'] == selected_year) & (full_df['자치구'] != '소계')].copy()
mean_val, std_val = df_year[target_col].mean(), df_year[target_col
