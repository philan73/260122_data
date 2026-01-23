import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import glob

# 페이지 설정
st.set_page_config(layout="wide", page_title="서울시 학업중단 알리미", page_icon="🏫")

# 1. 데이터 로드 및 전처리
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

# 자치구 좌표 데이터
DISTRICT_COORDS = {
    '종로구': [37.58, 126.98], '중구': [37.56, 126.99], '용산구': [37.53, 126.98], '성동구': [37.55, 127.04], 
    '광진구': [37.54, 127.08], '동대문구': [37.58, 127.05], '중랑구': [37.59, 127.09], '성북구': [37.60, 127.02], 
    '강북구': [37.63, 127.02], '도봉구': [37.66, 127.04], '노원구': [37.65, 127.07], '은평구': [37.61, 126.92], 
    '서대문구': [37.58, 126.93], '마포구': [37.56, 126.91], '양천구': [37.52, 126.85], '강서구': [37.56, 126.82], 
    '구로구': [37.49, 126.85], '금천구': [37.46, 126.90], '영등포구': [37.52, 126.91], '동작구': [37.50, 126.95], 
    '관악구': [37.47, 126.95], '서초구': [37.47, 127.03], '강남구': [37.49, 127.06], '송파구': [37.50, 127.11], '강동구': [37.55, 127.14]
}

# --- 레이아웃: 우측 최상단 제목 ---
t_col1, t_col2 = st.columns([1, 1])
with t_col2:
    st.title("🏫 서울시 학업중단 알리미")
    st.markdown("> **데이터 기반 위기 모니터링**: 서울시 평균을 기준으로 자치구별 위험 징후를 진단합니다.")

# --- 사이드바 ---
with st.sidebar:
    st.subheader("🎯 분석 설정")
    level_dict = {"👶 초등학교": "초등", "👦 중학교": "중등", "🧑 고등학교": "고등", "📊 전체 평균": "전체"}
    sel_level_raw = st.radio("학교급 선택", list(level_dict.keys()), index=3)
    type_key = level_dict[sel_level_raw]
    level_label = sel_level_raw.split(" ")[1]
    uploaded = st.file_uploader("CSV 추가 업로드", accept_multiple_files=True)

df = load_data(uploaded)

if df is not None:
    # 2. 데이터 가공 및 위기 기준 설정
    if type_key == "전체":
        df['학생수'] = df[['초등_학생', '중등_학생', '고등_학생']].sum(axis=1)
        df['중단자수'] = df[['초등_중단', '중등_중단', '고등_중단']].sum(axis=1)
        df['학업중단율'] = (df['중단자수'] / df['학생수'] * 100).round(2)
    else:
        df['학생수'] = df[f'{type_key}_학생']
        df['중단자수'] = df[f'{type_key}_중단']
        df['학업중단율'] = df[f'{type_key}_율'].round(2)

    avg_val = df[df['자치구'] == '소계']['학업중단율'].mean()
    danger_threshold = avg_val * 1.5

    # 3. 연도별 추이
    st.header(f"📈 서울시 {level_label} 중단율 추이")
    trend_df = df[df['자치구'] == '소계'].sort_values('연도')
    fig_line = px.line(trend_df, x='연도', y='학업중단율', markers=True, text='학업중단율')
    fig_line.add_hline(y=avg_val, line_dash="dash", line_color="orange", annotation_text="서울시 장기 평균")
    st.plotly_chart(fig_line, use_container_width=True)

    st.divider()

    # 4. 지도 및 상세 분석
    st.header(f"🗺️ {level_label} 지역별 위기 징후 분석")
    years = sorted(df['연도'].unique())
    sel_year = st.select_slider("📅 분석 연도 선택", options=years, value=max(years))
    
    map_df = df[(df['연도'] == sel_year) & (df['자치구'] != '소계')].copy()
    map_df['상태'] = map_df['학업중단율'].apply(lambda x: "🔴 위기" if x >= danger_threshold else ("🟡 주의" if x >= avg_val else "🟢 안정"))

    c_map, c_info = st.columns([1.5, 1])
    with c_map:
        geo = get_geojson()
        # 배경 지도 (중단율)
        fig_map = px.choropleth_mapbox(
            map_df, geojson=geo, locations='자치구', featureidkey="properties.name",
            color='학업중단율', color_continuous_scale="GnBu", range_color=[0, 2.5],
            mapbox_style="carto-positron", zoom=9.3, center={"lat": 37.5665, "lon": 126.9780},
            opacity=0.5
        )
        # 버블 레이어 (중단자 수)
        lats, lons, names, sizes = [], [], [], []
        for name, coords in DISTRICT_COORDS.items():
            row = map_df[map_df['자치구'] == name].iloc[0]
            lats.append(coords[0]); lons.append(coords[1]); names.append(name)
            sizes.append(row['중단자수'])
        
        fig_map.add_trace(go.Scattermapbox(
            lat=lats, lon=lons, mode='markers+text',
            marker=go.scattermapbox.Marker(size=[s/max(sizes)*40 for s in sizes], color='red', opacity=0.35),
            text=names, textfont=dict(size=10, color="black"), hoverinfo='none'
        ))
        fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=550)
        st.plotly_chart(fig_map, use_container_width=True)

        # --- 💡 지도 하단 보완 설명 (요청 사항) ---
        st.info("""
        **🔍 지도 읽는 법**
        * **색상(파란색):** 진할수록 학생 대비 중단 비중이 높은 지역입니다. (0~2.5% 고정 기준)
        * **붉은 원:** 크기가 클수록 실제로 학업을 중단한 **학생 수**가 많음을 의미합니다.
        * **진단 기준:** 서울시 평균보다 1.5배 높으면 **🔴위기**, 평균을 상회하면 **🟡주의**로 분류합니다.
        """)

    with c_info:
        st.markdown(f"#### 🔎 {sel_year}년 상세 리포트")
        selected_dist = st.selectbox("자치구 상세 조회", ["전체 요약"] + sorted(map_df['자치구'].tolist()))
        
        if selected_dist != "전체 요약":
            d = map_df[map_df['자치구'] == selected_dist].iloc[0]
            st.metric("진단 상태", d['상태'])
            m_col1, m_col2 = st.columns(2)
            m_col1.metric("중단율", f"{d['학업중단율']}%")
            m_col2.metric("중단자 수", f"{int(d['중단자수']):,}명")
            st.progress(min(d['학업중단율']/2.5, 1.0))
        else:
            st.success("지도를 클릭하거나 목록에서 자치구를 선택하여 상세 진단 결과를 확인하세요.")

        st.divider()
        st.write(f"**📋 {level_label} 상태 목록**")
        st.dataframe(map_df[['자치구', '학업중단율', '상태']].sort_values('학업중단율', ascending=False).reset_index(drop=True), use_container_width=True, height=280)

    st.divider()
    # 5. 히트맵 (타임라인)
    st.header("🌡️ 자치구별 학업중단율 타임라인")
    pivot_df = df[df['자치구'] != '소계'].pivot(index='자치구', columns='연도', values='학업중단율').sort_index(ascending=False)
    st.plotly_chart(px.imshow(pivot_df, color_continuous_scale="GnBu", aspect="auto"), use_container_width=True)

else:
    st.info("데이터를 업로드해 주세요.")
