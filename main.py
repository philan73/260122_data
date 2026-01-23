import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import glob

# 1. 페이지 설정
st.set_page_config(layout="wide", page_title="서울시 학업중단 알리미", page_icon="🏫")

# 2. 데이터 로드 및 전처리
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
            df_refined = df_raw[[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]].copy()
            df_refined.columns = ['자치구', '초등_학생', '초등_중단', '초등_율', '중등_학생', '중등_중단', '중등_율', '고등_학생', '고등_중단', '고등_율']
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

DISTRICT_COORDS = {
    '종로구': [37.58, 126.98], '중구': [37.56, 126.99], '용산구': [37.53, 126.98], '성동구': [37.55, 127.04], 
    '광진구': [37.54, 127.08], '동대문구': [37.58, 127.05], '중랑구': [37.59, 127.09], '성북구': [37.60, 127.02], 
    '강북구': [37.63, 127.02], '도봉구': [37.66, 127.04], '노원구': [37.65, 127.07], '은평구': [37.61, 126.92], 
    '서대문구': [37.58, 126.93], '마포구': [37.56, 126.91], '양천구': [37.52, 126.85], '강서구': [37.56, 126.82], 
    '구로구': [37.49, 126.85], '금천구': [37.46, 126.90], '영등포구': [37.52, 126.91], '동작구': [37.50, 126.95], 
    '관악구': [37.47, 126.95], '서초구': [37.47, 127.03], '강남구': [37.49, 127.06], '송파구': [37.50, 127.11], '강동구': [37.55, 127.14]
}

# --- 상단 헤더 ---
t_col1, t_col2 = st.columns([1, 1])
with t_col2:
    st.title("🏫 서울시 학업중단 알리미")
    st.markdown("> **데이터 기반 교육 안전망 모니터링**: 지역별 위기 수준을 진단하고 집중 관리 구역을 제안합니다.")

# --- 사이드바 ---
with st.sidebar:
    st.subheader("🎯 분석 설정")
    level_dict = {"👶 초등학교": "초등", "👦 중학교": "중등", "🧑 고등학교": "고등", "📊 전체 평균": "전체"}
    sel_level_raw = st.radio("학교급 선택", list(level_dict.keys()), index=3)
    type_key = level_dict[sel_level_raw]; level_label = sel_level_raw.split(" ")[1]
    uploaded = st.file_uploader("CSV 데이터 추가", accept_multiple_files=True)

df = load_data(uploaded)

if df is not None:
    # 데이터 가공
    if type_key == "전체":
        df['학생수'] = df[['초등_학생', '중등_학생', '고등_학생']].sum(axis=1)
        df['중단자수'] = df[['초등_중단', '중등_중단', '고등_중단']].sum(axis=1)
        df['학업중단율'] = (df['중단자수'] / df['학생수'] * 100).round(2)
    else:
        df['학생수'] = df[f'{type_key}_학생']; df['중단자수'] = df[f'{type_key}_중단']; df['학업중단율'] = df[f'{type_key}_율'].round(2)

    avg_val = df[df['자치구'] == '소계']['학업중단율'].mean()
    danger_threshold = avg_val * 1.5

    # --- 섹션 1: 학업중단율 추이 (가독성 개선 부분) ---
    st.header(f"📈 {level_label} 학업중단율 추이")
    trend_df = df[df['자치구'] == '소계'].sort_values('연도').copy()
    trend_df['표시율'] = trend_df['학업중단율'].apply(lambda x: f"{x:.2f}%") # 숫자 뒤 % 붙이기

    fig_line = px.line(trend_df, x='연도', y='학업중단율', markers=True, 
                       text='표시율') # 텍스트로 표시율 사용
    
    # 텍스트 스타일 및 위치 조정
    fig_line.update_traces(
        textposition="top center", 
        textfont=dict(size=14, color="black", family="Arial Black"),
        line_color="#0083B0",
        marker=dict(size=10)
    )
    
    # Y축 여백 확보 및 장기 평균선 추가
    fig_line.update_layout(
        yaxis=dict(range=[trend_df['학업중단율'].min() * 0.8, trend_df['학업중단율'].max() * 1.2]),
        margin=dict(t=50)
    )
    fig_line.add_hline(y=avg_val, line_dash="dash", line_color="orange", 
                       annotation_text=f"서울시 장기 평균 ({avg_val:.2f}%)", 
                       annotation_position="bottom right")
    
    st.plotly_chart(fig_line, use_container_width=True)

    st.divider()

    # 섹션 2: 자치구별 분석
    st.header(f"🗺️ 자치구별 {level_label} 학업중단율 분석")
    years = sorted(df['연도'].unique(), reverse=True)
    sel_year = st.selectbox("📅 분석 연도를 선택하세요", options=years, index=0)
    
    map_df = df[(df['연도'] == sel_year) & (df['자치구'] != '소계')].copy()
    map_df['상태'] = map_df['학업중단율'].apply(lambda x: "🔴 위기" if x >= danger_threshold else ("🟡 주의" if x >= avg_val else "🟢 안정"))

    # 위기 지역 요약
    danger_zones = map_df[map_df['상태'] == "🔴 위기"].sort_values('학업중단율', ascending=False).head(3)
    if not danger_zones.empty:
        st.subheader(f"🚨 {sel_year}년 집중 관리 권고 지역")
        cols = st.columns(len(danger_zones))
        for i, (idx, row) in enumerate(danger_zones.iterrows()):
            cols[i].warning(f"**{row['자치구']}**\n\n중단율: {row['학업중단율']}%")
    else:
        st.success(f"✅ {sel_year}년에는 '위기' 단계의 자치구가 없습니다.")

    c_map, c_info = st.columns([1.5, 1])
    with c_map:
        geo = get_geojson()
        fig_map = px.choropleth_mapbox(
            map_df, geojson=geo, locations='자치구', featureidkey="properties.name",
            color='학업중단율', color_continuous_scale="GnBu", range_color=[0, 2.5],
            mapbox_style="carto-positron", zoom=9.3, center={"lat": 37.5665, "lon": 126.9780},
            opacity=0.5, labels={'학업중단율': '중단율(%)'}
        )
        lats, lons, names, sizes = [], [], [], []
        for name, coords in DISTRICT_COORDS.items():
            row = map_df[map_df['자치구'] == name].iloc[0]
            lats.append(coords[0]); lons.append(coords[1]); names.append(name)
            sizes.append(row['중단자수'])
        
        fig_map.add_trace(go.Scattermapbox(
            lat=lats, lon=lons, mode='markers+text',
            marker=go.scattermapbox.Marker(size=[s/max(sizes + [1])*40 for s in sizes], color='red', opacity=0.35),
            text=names, textfont=dict(size=10, color="black"), hoverinfo='none'
        ))
        fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=550)
        st.plotly_chart(fig_map, use_container_width=True)

    with c_info:
        st.markdown(f"#### 🔎 {sel_year}년 상세 리포트")
        selected_dist = st.selectbox("자치구 상세 조회", ["전체 요약"] + sorted(map_df['자치구'].tolist()))
        if selected_dist != "전체 요약":
            d = map_df[map_df['자치구'] == selected_dist].iloc[0]
            st.markdown(f"**진단 결과: {d['상태']}**")
            m1, m2 = st.columns(2)
            m1.metric("전체 학생 수", f"{int(d['학생수']):,}명"); m1.metric("학업 중단자 수", f"{int(d['중단자수']):,}명")
            m2.metric("학업 중단율", f"{d['학업중단율']}%")
        else:
            total_info = df[(df['연도'] == sel_year) & (df['자치구'] == '소계')].iloc[0]
            st.success(f"**서울시 전체 평균**"); m1, m2 = st.columns(2)
            m1.metric("서울 전체 학생", f"{int(total_info['학생수']):,}명"); m1.metric("서울 전체 중단자", f"{int(total_info['중단자수']):,}명")
            m2.metric("평균 중단율", f"{total_info['학업중단율']}%")
        st.divider()
        st.dataframe(map_df[['자치구', '학생수', '중단자수', '학업중단율', '상태']].sort_values('학업중단율', ascending=False), use_container_width=True, height=250)

    st.divider()
    st.header(f"🌡️ 자치구별 {level_label} 중단율 타임라인")
    pivot_df = df[df['자치구'] != '소계'].pivot(index='자치구', columns='연도', values='학업중단율').sort_index(ascending=False)
    st.plotly_chart(px.imshow(pivot_df, color_continuous_scale="GnBu", aspect="auto"), use_container_width=True)
else:
    st.info("CSV 데이터를 업로드하여 분석을 시작하세요.")
