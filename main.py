import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import glob
import os

# 페이지 설정
st.set_page_config(page_title="서울시 학업중단율 분석", layout="wide")

# 1. GeoJSON 데이터 로드 (서울시 자치구 경계)
@st.cache_data
def get_seoul_geojson():
    url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/juso/2015/json/seoul_municipalities_geo_simple.json"
    return requests.get(url).json()

# 2. 자치구별 중심 좌표 (지도 위에 글자를 쓰기 위한 좌표)
def get_district_centers():
    centers = {
        '종로구': [37.5730, 126.9794], '중구': [37.5641, 126.9979], '용산구': [37.5326, 126.9904],
        '성동구': [37.5633, 127.0371], '광진구': [37.5385, 127.0822], '동대문구': [37.5744, 127.0400],
        '중랑구': [37.6065, 127.0927], '성북구': [37.5891, 127.0182], '강북구': [37.6396, 127.0257],
        '도봉구': [37.6688, 127.0471], '노원구': [37.6542, 127.0568], '은평구': [37.6027, 126.9291],
        '서대문구': [37.5791, 126.9368], '마포구': [37.5661, 126.9016], '양천구': [37.5106, 126.8665],
        '강서구': [37.5509, 126.8495], '구로구': [37.4954, 126.8581], '금천구': [37.4565, 126.8954],
        '영등포구': [37.5263, 126.8962], '동작구': [37.5124, 126.9395], '관악구': [37.4784, 126.9513],
        '서초구': [37.4837, 127.0324], '강남구': [37.4959, 127.0664], '송파구': [37.5145, 127.1061],
        '강동구': [37.5302, 127.1238]
    }
    return pd.DataFrame([{'name': k, 'lat': v[0], 'lon': v[1]} for k, v in centers.items()])

# 3. 데이터 로드 함수
def load_data(uploaded_files):
    all_data = []
    # 기본 파일 찾기
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
            
            # 전체 평균 중단율 계산
            df_cleaned['전체_중단율'] = (
                (df_cleaned['초등_중단자수'].fillna(0) + df_cleaned['중등_중단자수'].fillna(0) + df_cleaned['고등_중단자수'].fillna(0)) /
                (df_cleaned['초등_학생수'].fillna(1) + df_cleaned['중등_학생수'].fillna(1) + df_cleaned['고등_학생수'].fillna(1)) * 100
            )
            all_data.append(df_cleaned)
        except: continue
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

# 메인 로직
st.sidebar.header("설정")
uploaded_files = st.sidebar.file_uploader("추가 CSV 업로드", accept_multiple_files=True)
df = load_data(uploaded_files)

if not df.empty:
    st.title("📍 서울시 자치구별 학업중단율 지도 분석")

    c1, c2
