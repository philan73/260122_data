import streamlit as st
import pandas as pd
import plotly.express as px
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

# --- 메인 화면 시작 ---
st.title("🏫 서울시 학업중단 알리미")

with st.sidebar:
    st.header("⚙️ 분석 설정")
    uploaded = st.file_uploader("CSV 추가 업로드", accept_multiple_files=True)
    level = st.selectbox("학교급 선택", ["전체 평균", "초등학교", "중학교", "고등학교"], index=0)

df = load_data(uploaded)

if df is not None:
    # 데이터 처리
    if level == "전체 평균":
        df['target'] = df[['초등학교', '중학교', '고등학교']].mean(axis=1)
    else:
        df['target'] = df[level]

    # --- 1. 상단: 연도별 학업중단 추이 ---
    st.subheader(f"📈 연도별 학업중단 추이 ({level})")
    trend_df = df[df['자치구'].str.contains('소계', na=False)].sort_values('연도')
    fig_line = px.line(trend_df, x='연도', y='target', markers=True, 
                      line_shape='spline', color_discrete_sequence=['#2E7D32']) # 차분한 녹색 톤
    fig_line.update_layout(hovermode="x unified", plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_line, use_container_width=True)

    st.divider()

    # --- 2. 중단: 지역별 상세 분포 (지도) ---
    st.subheader("🗺️ 지역별 상세 분포")
    years = sorted(df['연도'].unique())
    selected_year = st.select_slider("확인할 연도를 선택하세요", options=years, value=max(years))
    
    map_df = df[(df['연도'] == selected_year) & (~df['자치구'].str.contains('소계', na=False))]
    
    col1, col2 = st.columns([2, 1])
    with col1:
        geo = get_geojson()
        fig_map = px.choropleth_mapbox(
            map_df, geojson=geo, locations='자치구', featureidkey="properties.name",
            color='target', color_continuous_scale="YlGnBu", # 차분한 청록색 톤
            mapbox_style="carto-positron", zoom=9.5, 
            center={"lat": 37.5665, "lon": 126.9780},
            opacity=0.7, labels={'target': '중단율(%)'}
        )
        fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig_map, use_container_width=True)
    
    with col2:
        st.write(f"**{selected_year}년 {level} 순위**")
        st.dataframe(map_df[['자치구', 'target']].sort_values('target', ascending=False), hide_index=True, use_container_width=True)

    st.divider()

    # --- 3. 하단: 자치구별 히트맵 타임라인 ---
    st.subheader("🌡️ 자치구별 학업중단율 히트맵 타임라인")
    st.markdown("과거부터 현재까지 각 자치구의 변화를 한눈에 비교합니다.")
    
    heatmap_data = df[~df['자치구'].str.contains('소계', na=False)]
    pivot_df = heatmap_data.pivot(index='자치구', columns='연도', values='target').sort_index(ascending=False)

    fig_heat = px.imshow(
        pivot_df,
        labels=dict(x="연도", y="자치구", color="중단율(%)"),
        x=pivot_df.columns, y=pivot_df.index,
        color_continuous_scale="GnBu", # Green-Blue 톤으로 눈을 편안하게
        aspect="auto"
    )
    fig_heat.update_xaxes(side="top")
    st.plotly_chart(fig_heat, use_container_width=True)

else:
    st.info("데이터를 업로드하거나 파일 경로를 확인해주세요.")
