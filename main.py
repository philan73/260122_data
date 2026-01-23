import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import glob

# 페이지 설정
st.set_page_config(layout="wide", page_title="서울시 학업중단 알리미", page_icon="🏫")

# 데이터 로드 및 전처리 (학생수, 중단자수 포함)
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
            
            # 컬럼 인덱스 매핑: 1:자치구, 2:초등학생수, 3:초등중단자, 4:초등율, 5:중학생수, 6:중중단자, 7:중율, 8:고학생수, 9:고중단자, 10:고율
            df_refined = df_raw[[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]].copy()
            df_refined.columns = [
                '자치구', '초등_학생수', '초등_중단자', '초등_중단율', 
                '중등_학생수', '중등_중단자', '중등_중단율', 
                '고등_학생수', '고등_중단자', '고등_중단율'
            ]
            for col in df_refined.columns[1:]:
                df_refined[col] = pd.to_numeric(df_refined[col], errors='coerce')
            
            df_refined['연도'] = int(year_val)
            all_dfs.append(df_refined)
        except: continue
    return pd.concat(all_dfs, ignore_index=True) if all_dfs else None

@st.cache_data
def get_geojson():
    url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json"
    return requests.get(url).json()

# 자치구 중심 좌표 (지도 위 라벨용)
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

# --- 레이아웃: 헤더 ---
h_col1, h_col2 = st.columns([1, 1])
with h_col2:
    st.title("🏫 서울시 학업중단 알리미")
    st.markdown("> **교육 환경 모니터링 시스템**: 자치구별 학업 중단 현황을 분석합니다.")

# --- 사이드바 ---
with st.sidebar:
    st.subheader("🎯 분석 설정")
    level_dict = {"👶 초등학교": "초등", "👦 중학교": "중등", "🧑 고등학교": "고등", "📊 전체 평균": "전체"}
    sel_level_name = st.radio("학교급 선택", list(level_dict.keys()), index=3)
    type_key = level_dict[sel_level_name]
    # 학교급 이름만 추출 (예: 초등학교)
    level_label = sel_level_name.split(" ")[1] 
    uploaded = st.file_uploader("CSV 추가", accept_multiple_files=True)

df = load_data(uploaded)

if df is not None:
    # 선택 학교급 데이터 가공
    if type_key == "전체":
        df['학생수'] = df[['초등_학생수', '중등_학생수', '고등_학생수']].sum(axis=1)
        df['중단자수'] = df[['초등_중단자', '중등_중단자', '고등_중단자']].sum(axis=1)
        df['학업중단율'] = (df['중단자수'] / df['학생수'] * 100).round(2)
    else:
        df['학생수'] = df[f'{type_key}_학생수']
        df['중단자수'] = df[f'{type_key}_중단자']
        df['학업중단율'] = df[f'{type_key}_중단율'].round(2)

    # 1. 추이
    st.header(f"📈 연도별 {level_label} 중단율 추이")
    trend_df = df[df['자치구'] == '소계'].sort_values('연도')
    st.info(f"💡 현재 **{level_label}** 데이터를 조회 중입니다. 최신 서울시 평균 중단율은 **{trend_df['학업중단율'].iloc[-1]}%**입니다.")
    fig_line = px.line(trend_df, x='연도', y='학업중단율', markers=True, line_shape='spline', text='학업중단율')
    fig_line.update_traces(textposition="top center", line_color="#0083B0")
    st.plotly_chart(fig_line, use_container_width=True)

    st.divider()

    # 2. 지도 및 상세 지표
    st.header(f"🗺️ {level_label} 지역별 상세 분포")
    years = sorted(df['연도'].unique())
    sel_year = st.select_slider("📅 조회 연도 선택", options=years, value=max(years))
    
    map_df = df[(df['연도'] == sel_year) & (df['자치구'] != '소계')].copy()

    col1, col2 = st.columns([1.5, 1])
    with col1:
        geo = get_geojson()
        fig_map = px.choropleth_mapbox(
            map_df, geojson=geo, locations='자치구', featureidkey="properties.name",
            color='학업중단율', color_continuous_scale="GnBu",
            mapbox_style="carto-positron", zoom=9.3, center={"lat": 37.5665, "lon": 126.9780},
            opacity=0.6, labels={'학업중단율': '중단율(%)'}
        )
        lats, lons, names = [], [], []
        for name, coords in DISTRICT_COORDS.items():
            lats.append(coords[0]); lons.append(coords[1]); names.append(name)
        fig_map.add_trace(go.Scattermapbox(lat=lats, lon=lons, mode='text', text=names, textfont=dict(size=10, color="#444"), hoverinfo='none'))
        fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        st.write(f"📍 **지도를 클릭하거나 우측 메뉴에서 {level_label} 상세 수치를 확인하세요.**")
        st.plotly_chart(fig_map, use_container_width=True)

    with col2:
        selected_dist = st.selectbox("🔍 상세 정보 확인 자치구", ["선택하세요"] + sorted(map_df['자치구'].tolist()))
        
        if selected_dist != "선택하세요":
            dist_info = map_df[map_df['자치구'] == selected_dist].iloc[0]
            st.subheader(f"🏠 {selected_dist} {level_label} 지표")
            c1, c2 = st.columns(2)
            c1.metric(f"{level_label} 학생 수", f"{int(dist_info['학생수']):,}명")
            c1.metric(f"{level_label} 중단자 수", f"{int(dist_info['중단자수']):,}명")
            c2.metric("학업 중단율", f"{dist_info['학업중단율']}%")
            st.write("---")
            st.write(f"**📋 {sel_year}년 {level_label} 현황 목록**")
        else:
            st.write(f"**📋 {sel_year}년 자치구별 {level_label} 현황**")
            
        rank_df = map_df[['자치구', '학업중단율']].sort_values('학업중단율', ascending=False).reset_index(drop=True)
        rank_df.index += 1
        st.dataframe(rank_df, use_container_width=True, height=350, column_config={"학업중단율": st.column_config.NumberColumn(f"{level_label} 중단율(%)", format="%.2f")})

    st.divider()

    # 3. 히트맵
    st.header(f"🌡️ 자치구별 {level_label} 중단율 히트맵")
    st.warning(f"💡 색상이 짙을수록 해당 연도/지역의 **{level_label}** 중단율이 상대적으로 높음을 의미합니다.")
    heatmap_data = df[df['자치구'] != '소계']
    pivot_df = heatmap_data.pivot(index='자치구', columns='연도', values='학업중단율').sort_index(ascending=False)
    fig_heat = px.imshow(pivot_df, color_continuous_scale="GnBu", aspect="auto")
    st.plotly_chart(fig_heat, use_container_width=True)

else:
    st.info("데이터 로딩 중...")
