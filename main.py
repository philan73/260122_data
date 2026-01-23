import streamlit as st
import pandas as pd
import plotly.express as px
import json
import requests
import glob

# 페이지 설정
st.set_page_config(page_title="서울시 학업중단율 지도 대시보드", layout="wide")

# --- 데이터 및 지도 데이터 로드 ---
@st.cache_data
def get_seoul_geojson():
    # 서울시 자치구 경계 데이터 (GeoJSON)
    url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/juso/2015/json/seoul_municipalities_geo_simple.json"
    return requests.get(url).json()

def load_data(uploaded_files):
    all_data = []
    base_files = glob.glob("학업중단율_*.csv")
    file_sources = [('local', f) for f in base_files]
    if uploaded_files:
        for f in uploaded_files:
            file_sources.append(('uploaded', f))

    for source_type, file in file_sources:
        try:
            if source_type == 'local':
                year = file.split('_')[1].split('.')[0]
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
            # 숫자 형변환 및 전체 평균 중단율 계산
            for col in df_cleaned.columns[2:-1]:
                df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')
            
            df_cleaned['전체_중단율'] = (df_cleaned['초등_중단자수'] + df_cleaned['중등_중단자수'] + df_cleaned['고등_중단자수']) / \
                                     (df_cleaned['초등_학생수'] + df_cleaned['중등_학생수'] + df_cleaned['고등_학생수']) * 100
            all_data.append(df_cleaned)
        except:
            continue
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

# 데이터 준비
uploaded_files = st.sidebar.file_uploader("추가 CSV 업로드", accept_multiple_files=True)
df = load_data(uploaded_files)
seoul_geo = get_seoul_geojson()

if not df.empty:
    st.title("🗺️ 서울시 자치구별 학업중단율 지도")

    # 상단 컨트롤러
    c1, c2 = st.columns(2)
    with c1:
        selected_year = st.selectbox("연도 선택", sorted(df['연도'].unique(), reverse=True))
    with c2:
        # '전체' 옵션 추가
        school_level = st.radio("학교급 선택", ["전체", "초등", "중등", "고등"], horizontal=True)

    # 데이터 필터링 (소계 제외)
    map_df = df[(df['연도'] == selected_year) & (df['자치구별(2)'] != '소계')].copy()
    
    # 표시할 컬럼 결정
    target_col = '전체_중단율' if school_level == "전체" else f"{school_level}_중단율"
    
    # --- 지도 생성 ---
    fig = px.choropleth_mapbox(
        map_df,
        geojson=seoul_geo,
        locations='자치구별(2)',
        featureidkey="properties.name",
        color=target_col,
        color_continuous_scale="YlOrRd", # 노랑->빨강 색상표
        range_color=(0, map_df[target_col].max()),
        mapbox_style="carto-positron",
        zoom=10,
        center={"lat": 37.5665, "lon": 126.9780},
        opacity=0.7,
        labels={target_col: '중단율(%)'},
        hover_data={'자치구별(2)': True, target_col: ':.2f'}
    )
    
    # 지도 위에 자치구 이름 표시 (Text layer 추가)
    # 실제 구현시 텍스트 레이어는 scatter_mapbox를 겹쳐서 사용함
    
    fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, title=f"{selected_year}년 {school_level} 학업중단율 분포")
    st.plotly_chart(fig, use_container_width=True)

    # --- 색상 설명 ---
    st.info(f"""
    **💡 지도 색상 의미 안내:**
    * **진한 빨간색**: 해당 지역의 {school_level} 학업중단율이 상대적으로 **매우 높음**을 의미합니다.
    * **연한 노란색**: 해당 지역의 {school_level} 학업중단율이 상대적으로 **낮음**을 의미합니다.
    * **회색**: 데이터가 존재하지 않는 지역입니다.
    * *현재 화면의 중단율 범위: {map_df[target_col].min():.2f}% ~ {map_df[target_col].max():.2f}%*
    """)

    st.divider()
    # 하단 데이터 표
    st.subheader("상세 데이터 표")
    st.dataframe(map_df[['자치구별(2)', '초등_중단율', '중등_중단율', '고등_중단율', '전체_중단율']], use_container_width=True)
