import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import glob

# 페이지 설정
st.set_page_config(layout="wide", page_title="서울시 학업중단 알리미", page_icon="🏫")

# 데이터 로드 함수
@st.cache_data
def load_data(uploaded_files):
    all_dfs = []
    base_files = glob.glob("학업중단율_*.csv")
    file_list = uploaded_files if uploaded_files else base_files

    for f in file_list:
        try:
            fname = f.name if hasattr(f, 'name') else f
            year_val = fname.split('_')[1].split('.')[0]
            df_raw = pd.read_csv(f, skiprows=3, header=None)
            df_refined = df_raw[[1, 4, 7, 10]].copy()
            df_refined.columns = ['자치구', '초등학교', '중학교', '고등학교']
            for col in ['초등학교', '중학교', '고등학교']:
                df_refined[col] = pd.to_numeric(df_refined[col], errors='coerce')
            df_refined['연도'] = int(year_val)
            all_dfs.append(df_refined)
        except: continue
    return pd.concat(all_dfs, ignore_index=True) if all_dfs else None

@st.cache_data
def get_geojson():
    url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json"
    return requests.get(url).json()

# 자치구별 중심 좌표 (지도 위 이름 표기용)
DISTRICT_COORDS = {
    '종로구': [37.58, 126.98], '중구': [37.56, 126.99], '용산구': [37.53, 126.98],
    '성동구': [37.55, 127.04], '광진구': [37.54, 127.08], '동대문구': [37.58, 127.05],
    '중랑구': [37.59, 127.09], '성북구': [37.60, 127.02], '강북구': [37.63, 127.02],
    '도봉구': [37.66, 127.04], '노원구': [37.65, 127.07], '은평구': [37.61, 126.92],
    '서대문구': [37.58, 126.93], '마포구': [37.56, 126.91], '양천구': [37.52, 126.85],
    '강서구': [37.56, 126.82], '구로구': [37.49, 126.85], '금천구': [37.46, 126.90],
    '영등포구': [37.52, 126.91], '동작구': [37.50, 126.95], '관악구': [37.47, 126.95],
    '서초구': [37.47, 127.03], '강남구': [37.49, 127.06], '송파구': [37.50, 127.11], '강동구': [37.55, 127.14]
}

# --- 레이아웃: 최상단 우측 제목 및 설명 ---
header_col1, header_col2 = st.columns([1, 1])
with header_col2:
    st.title("🏫 서울시 학업중단 알리미")
    st.markdown("> **본 서비스는 서울시 공공데이터를 기반으로 학업중단 현황을 분석하여 교육 정책의 기초 자료를 제공합니다.**")

# --- 사이드바: 학교급 선택 ---
with st.sidebar:
    st.subheader("🎯 분석 타겟 설정")
    level_options = {"👶 초등학교": "초등학교", "👦 중학교": "중학교", "🧑 고등학교": "고등학교", "📊 전체 평균": "전체 평균"}
    selected_display = st.radio("학교급 아이콘 선택", list(level_options.keys()), index=3)
    level = level_options[selected_display]
    st.divider()
    uploaded = st.file_uploader("CSV 데이터 추가", accept_multiple_files=True)

df = load_data(uploaded)

if df is not None:
    df['학업중단율'] = df[['초등학교', '중학교', '고등학교']].mean(axis=1).round(2) if level == "전체 평균" else df[level].round(2)

    # 1. 연도별 추이
    st.header("📈 연도별 학업중단 추이")
    trend_df = df[df['자치구'].str.contains('소계', na=False)].sort_values('연도')
    st.info(f"💡 **해석:** 최근 {trend_df['연도'].iloc[-1]}년 서울시 평균 중단율은 {trend_df['학업중단율'].iloc[-1]:.2f}%입니다.")
    fig_line = px.line(trend_df, x='연도', y='학업중단율', markers=True, line_shape='spline', text='학업중단율')
    fig_line.update_traces(textposition="top center", line_color="#0083B0")
    st.plotly_chart(fig_line, use_container_width=True)

    st.divider()

    # 2. 지역별 분포 (연도 선택 및 지도)
    st.header("🗺️ 지역별 상세 분포")
    years = sorted(df['연도'].unique())
    selected_year = st.select_slider("📅 데이터 기준 연도를 선택하세요", options=years, value=max(years))
    
    map_df = df[(df['연도'] == selected_year) & (~df['자치구'].str.contains('소계', na=False))].copy()
    
    col1, col2 = st.columns([2, 1])
    with col1:
        geo = get_geojson()
        # 기본 지도 레이어
        fig_map = px.choropleth_mapbox(
            map_df, geojson=geo, locations='자치구', featureidkey="properties.name",
            color='학업중단율', color_continuous_scale="GnBu",
            mapbox_style="carto-positron", zoom=9.4, center={"lat": 37.5665, "lon": 126.9780},
            opacity=0.6, labels={'학업중단율': '중단율(%)'}
        )
        
        # 지도 위에 자치구 이름 추가 레이어
        lats, lons, names = [], [], []
        for name, coords in DISTRICT_COORDS.items():
            lats.append(coords[0]); lons.append(coords[1]); names.append(name)
        
        fig_map.add_trace(go.Scattermapbox(
            lat=lats, lon=lons, mode='text',
            text=names, textfont=dict(size=11, color="black"),
            hoverinfo='none', showlegend=False
        ))
        fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig_map, use_container_width=True)
    
    with col2:
        st.write(f"**📍 {selected_year}년 학업중단율 순위**")
        rank_df = map_df[['자치구', '학업중단율']].sort_values('학업중단율', ascending=False).reset_index(drop=True)
        rank_df.index = rank_df.index + 1
        rank_df.index.name = "순위"
        st.dataframe(rank_df, use_container_width=True, height=450,
                     column_config={"학업중단율": st.column_config.NumberColumn("학업중단율 (%)", format="%.2f")})

    st.divider()

    # 3. 히트맵
    st.header("🌡️ 자치구별 학업중단율 히트맵")
    st.warning("💡 **해석:** 색상이 짙은 파란색에 가까울수록 해당 연도/지역의 중단율이 상대적으로 높음을 의미합니다.")
    heatmap_data = df[~df['자치구'].str.contains('소계', na=False)]
    pivot_df = heatmap_data.pivot(index='자치구', columns='연도', values='학업중단율').sort_index(ascending=False)
    fig_heat = px.imshow(pivot_df, color_continuous_scale="GnBu", aspect="auto")
    st.plotly_chart(fig_heat, use_container_width=True)

else:
    st.info("데이터를 업로드해 주세요.")
