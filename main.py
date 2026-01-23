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

# --- 사이드바: 예쁜 학교급 선택 아이콘 ---
with st.sidebar:
    st.subheader("🎯 분석 학교급 선택")
    level_options = {
        "👶 초등학교": "초등학교",
        "👦 중학교": "중학교",
        "🧑 고등학교": "고등학교",
        "📊 전체 평균": "전체 평균"
    }
    selected_display = st.radio("아이콘을 클릭하여 선택하세요", list(level_options.keys()), index=3)
    level = level_options[selected_display]
    
    st.divider()
    st.info("데이터 업로드 시 '학업중단율_YYYY.csv' 형식을 유지해주세요.")
    uploaded = st.file_uploader("파일 추가", accept_multiple_files=True)

# 데이터 준비
df = load_data(uploaded)

if df is not None:
    # 데이터 처리 및 명칭 통일
    if level == "전체 평균":
        df['학업중단율'] = df[['초등학교', '중학교', '고등학교']].mean(axis=1).round(2)
    else:
        df['학업중단율'] = df[level].round(2)

    # --- 메인 헤더: 오른쪽 상단 설명 배치 ---
    head_col1, head_col2 = st.columns([1, 1.2])
    with head_col2:
        st.title("🏫 서울시 학업중단 알리미")
        st.markdown("""
        이 대시보드는 서울시 교육청의 공공데이터를 기반으로 합니다.  
        연도별 추이와 지역별 격차를 분석하여 **교육 환경 개선을 위한 인사이트**를 제공합니다.
        """)

    st.divider()

    # 1. 상단: 추이 그래프 및 해석
    st.header("📈 연도별 학업중단 추이")
    trend_df = df[df['자치구'].str.contains('소계', na=False)].sort_values('연도')
    latest_val = trend_df['학업중단율'].iloc[-1]
    st.markdown(f"**💡 분석 결과:** 최근 연도 서울시 평균 학업중단율은 **{latest_val:.2f}%**로 집계되었습니다. 전반적인 흐름을 확인하세요.")
    
    fig_line = px.line(trend_df, x='연도', y='학업중단율', markers=True, 
                      line_shape='spline', color_discrete_sequence=['#0083B0'], text='학업중단율')
    fig_line.update_traces(textposition="top center", texttemplate='%{text:.2f}%')
    st.plotly_chart(fig_line, use_container_width=True)

    st.divider()

    # 2. 중단: 지도 및 순위
    st.header("🗺️ 지역별 상세 분포")
    years = sorted(df['연도'].unique())
    selected_year = st.select_slider("데이터 기준 연도", options=years, value=max(years))
    
    map_df = df[(df['연도'] == selected_year) & (~df['자치구'].str.contains('소계', na=False))].copy()
    top_dist = map_df.sort_values('학업중단율', ascending=False).iloc[0]
    st.markdown(f"**💡 분석 결과:** {selected_year}년 기준, **{top_dist['자치구']}** 지역이 **{top_dist['학업중단율']:.2f}%**로 가장 높은 중단율을 보였습니다.")

    col1, col2 = st.columns([2, 1])
    with col1:
        geo = get_geojson()
        fig_map = px.choropleth_mapbox(
            map_df, geojson=geo, locations='자치구', featureidkey="properties.name",
            color='학업중단율', color_continuous_scale="GnBu",
            mapbox_style="carto-positron", zoom=9.5, 
            center={"lat": 37.5665, "lon": 126.9780},
            opacity=0.8, labels={'학업중단율': '중단율(%)'},
            hover_name='자치구'
        )
        # 지도 위에 자치구 이름 고정 (Scattermapbox 활용)
        # (주의: 이 기능은 좌표 데이터가 필요하므로 호버 이름으로 대체하거나 고정 레이어를 추가할 수 있습니다)
        fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig_map, use_container_width=True)
    
    with col2:
        st.write(f"**🏆 {selected_year}년 {level} 순위**")
        rank_df = map_df[['자치구', '학업중단율']].sort_values('학업중단율', ascending=False).reset_index(drop=True)
        rank_df.index = rank_df.index + 1 # 1위부터 시작
        rank_df.index.name = "순위"
        st.dataframe(rank_df, use_container_width=True, height=400,
                     column_config={"학업중단율": st.column_config.NumberColumn("학업중단율 (%)", format="%.2f")})

    st.divider()

    # 3. 하단: 히트맵
    st.header("🌡️ 자치구별 학업중단율 히트맵")
    st.markdown("**💡 분석 결과:** 자치구별 장기 흐름을 시각화하여 특정 시기나 지역의 변화를 한눈에 비교할 수 있습니다.")
    heatmap_data = df[~df['자치구'].str.contains('소계', na=False)]
    pivot_df = heatmap_data.pivot(index='자치구', columns='연도', values='학업중단율').sort_index(ascending=False)
    fig_heat = px.imshow(pivot_df, color_continuous_scale="GnBu", aspect="auto")
    fig_heat.update_xaxes(side="top")
    st.plotly_chart(fig_heat, use_container_width=True)

else:
    st.info("데이터를 업로드해 주세요.")
