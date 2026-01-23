import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import glob

# 페이지 설정
st.set_page_config(layout="wide", page_title="서울시 학업중단 알리미", page_icon="🏫")

# 데이터 로드 함수 (위치 기반 추출로 오류 방지)
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
            # 위치 기반 추출 (1:자치구, 4:초등율, 7:중등율, 10:고등율)
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

# --- 사이드바: 설명 및 예쁜 아이콘 설정 ---
with st.sidebar:
    st.title("🏫 서울시 학업중단 알리미")
    st.markdown("""
    **본 사이트는 서울시 교육청 데이터를 기반으로 자치구별 학업중단 현황을 분석합니다.**
    
    * **추이 분석:** 10년 이상의 흐름 파악
    * **지역 비교:** 자치구별 격차 시각화
    * **심층 탐색:** 학교급별 맞춤형 데이터 탐색
    
    ---
    """)
    
    st.subheader("🎯 분석 타겟 설정")
    # 이모지 아이콘을 활용한 라디오 버튼
    level_options = {
        "👶 초등학교": "초등학교",
        "👦 중학교": "중학교",
        "🧑 고등학교": "고등학교",
        "📊 전체 평균": "전체 평균"
    }
    selected_display = st.radio("학교급을 선택하세요", list(level_options.keys()), index=3)
    level = level_options[selected_display]
    
    st.divider()
    uploaded = st.file_uploader("추가 데이터 업로드 (CSV)", accept_multiple_files=True)

# --- 메인 화면 시작 ---
df = load_data(uploaded)

if df is not None:
    # 데이터 처리 및 명칭 통일
    if level == "전체 평균":
        df['학업중단율'] = df[['초등학교', '중학교', '고등학교']].mean(axis=1).round(2)
    else:
        df['학업중단율'] = df[level].round(2)

    # 1. 상단: 연도별 학업중단 추이
    st.header("📈 연도별 학업중단 추이")
    trend_df = df[df['자치구'].str.contains('소계', na=False)].sort_values('연도')
    
    # 간략 해석 (가장 최신 연도 기준)
    latest_year = trend_df['연도'].iloc[-1]
    latest_val = trend_df['학업중단율'].iloc[-1]
    prev_val = trend_df['학업중단율'].iloc[-2] if len(trend_df) > 1 else latest_val
    trend_txt = "상승" if latest_val > prev_val else "하락"
    
    st.markdown(f"**💡 분석 결과:** {latest_year}년 서울시 전체 평균 중단율은 **{latest_val}%**로, 전년 대비 소폭 **{trend_txt}**하는 양상을 보이고 있습니다.")
    
    fig_line = px.line(trend_df, x='연도', y='학업중단율', markers=True, 
                      line_shape='spline', color_discrete_sequence=['#0083B0'], text='학업중단율')
    fig_line.update_traces(textposition="top center")
    fig_line.update_layout(hovermode="x unified", plot_bgcolor='rgba(0,0,0,0)', yaxis_title="중단율 (%)")
    st.plotly_chart(fig_line, use_container_width=True)

    st.divider()

    # 2. 중단: 지역별 상세 분포
    st.header("🗺️ 지역별 상세 분포")
    selected_year = st.select_slider("데이터 기준 연도 선택", options=sorted(df['연도'].unique()), value=max(df['연도']))
    
    map_df = df[(df['연도'] == selected_year) & (~df['자치구'].str.contains('소계', na=False))].copy()
    
    # 지역별 해석
    top_district = map_df.sort_values('학업중단율', ascending=False).iloc[0]
    st.markdown(f"**💡 분석 결과:** {selected_year}년에는 **{top_district['자치구']}** 지역의 중단율이 **{top_district['학업중단율']}%**로 가장 높게 기록되었습니다.")

    col1, col2 = st.columns([2, 1])
    with col1:
        geo = get_geojson()
        fig_map = px.choropleth_mapbox(
            map_df, geojson=geo, locations='자치구', featureidkey="properties.name",
            color='학업중단율', color_continuous_scale="GnBu",
            mapbox_style="carto-positron", zoom=9.5, 
            center={"lat": 37.5665, "lon": 126.9780},
            opacity=0.8, labels={'학업중단율': '중단율(%)'}
        )
        # 지도 위에 자치구 이름이 뜨도록 설정 (hover 시)
        fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig_map, use_container_width=True)
    
    with col2:
        st.write(f"**🏆 {selected_year}년 {level} 순위**")
        rank_df = map_df[['자치구', '학업중단율']].sort_values('학업중단율', ascending=False).reset_index(drop=True)
        rank_df.index = rank_df.index + 1 # 순위를 1부터 시작하게 변경
        st.dataframe(rank_df, use_container_width=True, height=400,
                     column_config={"학업중단율": st.column_config.NumberColumn("학업중단율 (%)", format="%.2f")})

    st.divider()

    # 3. 하단: 히트맵 타임라인
    st.header("🌡️ 자치구별 학업중단율 히트맵")
    st.markdown("**💡 분석 결과:** 자치구별 장기 추세를 통해 특정 지역의 교육 환경 변화를 한눈에 파악할 수 있습니다.")
    
    heatmap_data = df[~df['자치구'].str.contains('소계', na=False)]
    pivot_df = heatmap_data.pivot(index='자치구', columns='연도', values='학업중단율').sort_index(ascending=False)

    fig_heat = px.imshow(pivot_df, color_continuous_scale="GnBu", aspect="auto")
    fig_heat.update_xaxes(side="top")
    st.plotly_chart
