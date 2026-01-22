import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="서울 기온 분석 데이터 센터", layout="wide")

# 데이터 로드 및 전처리 함수
@st.cache_data
def load_and_clean_data(file_path_or_buffer):
    # 인코딩은 공공데이터 표준인 cp949 사용
    df = pd.read_csv(file_path_or_buffer, encoding='cp949')
    
    # 1. 날짜 데이터 정제 (탭 문자 제거 및 데이트타임 변환)
    df['날짜'] = df['날짜'].astype(str).str.replace('\t', '').str.strip()
    df['날짜'] = pd.to_datetime(df['날짜'])
    
    # 2. 분석을 위한 파생 변수 생성
    df['year'] = df['날짜'].dt.year
    df['month_day'] = df['날짜'].dt.strftime('%m-%d')
    
    # 3. 결측치 확인 (최저기온이 없는 날은 분석에서 제외하기 위해 기록)
    # 별도의 보간법보다는 실제 기록된 데이터만 사용하는 것이 정확함
    return df

# --- 사이드바: 데이터 업로드 ---
st.sidebar.title("데이터 설정")
uploaded_file = st.sidebar.file_uploader("추가 기온 데이터 업로드 (CSV)", type="csv")

# 데이터 로드 로직
if uploaded_file is not None:
    df = load_and_clean_data(uploaded_file)
    st.sidebar.success("사용자 데이터를 성공적으로 불러왔습니다.")
else:
    try:
        df = load_and_clean_data('ta_20260122174530.csv')
        st.sidebar.info("기본 시스템 데이터를 사용 중입니다.")
    except:
        st.error("데이터 파일을 찾을 수 없습니다. CSV 파일을 업로드해주세요.")
        st.stop()

# --- 메인 화면: 기온 비교 분석 ---
st.title("🌡️ 서울 기온 역사 비교기")
st.markdown("특정 날짜의 기온을 역대 같은 날짜들의 기록과 비교합니다.")

# 날짜 선택 (기본값: 데이터셋의 가장 최근 날짜)
latest_date = df['날짜'].max().date()
selected_date = st.date_input("비교하고 싶은 날짜를 선택하세요", latest_date)
target_md = selected_date.strftime('%m-%d')

# 동일 날짜(월-일) 역대 데이터 필터링 (결측치 제외)
historical_same_day = df[df['month_day'] == target_md].dropna(subset=['평균기온(℃)'])

if not historical_same_day.empty:
    # 통계 계산
    avg_temp = historical_same_day['평균기온(℃)'].mean()
    max_temp_ever = historical_same_day['평균기온(℃)'].max()
    min_temp_ever = historical_same_day['평균기온(℃)'].min()
    
    # 선택한 날의 기온 (데이터가 없을 경우 대비)
    target_row = historical_same_day[historical_same_day['year'] == selected_date.year]
    
    if not target_row.empty:
        current_temp = target_row['평균기온(℃)'].values[0]
        diff = current_temp - avg_temp
        
        # 메트릭 표시
        col1, col2, col3 = st.columns(3)
        col1.metric(f"{selected_date.year}년 기온", f"{current_temp} ℃")
        col2.metric("역대 평균 대비", f"{round(diff, 2)} ℃", delta=round(diff, 2))
        col3.metric("역대 최고/최저", f"{max_temp_ever}℃ / {min_temp_ever}℃")
        
        # 강조 텍스트
        status = "더웠습니다" if diff > 0 else "추웠습니다"
        st.info(f"📅 **{selected_date.year}년 {target_md}**는 역대 평균({round(avg_temp, 2)}℃)보다 **{abs(round(diff, 2))}℃ 더 {status}.**")
    else:
        st.warning(f"{selected_date.year}년 {target_md}의 데이터가 존재하지 않습니다. 아래 차트에서 역대 기록을 확인하세요.")

    # 시각화: 역대 같은 날짜 기온 추이
    st.subheader(f"역대 {target_md} 기온 변화 그래프")
    fig = px.line(historical_same_day, x='year', y='평균기온(℃)', 
                  markers=True, title=f"1907년~2025년 {target_md} 평균 기온 추이")
    # 평균선 추가
    fig.add_hline(y=avg_temp, line_dash="dash", line_color="red", annotation_text="역대 평균")
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("선택한 날짜에 대한 과거 기록이 데이터에 없습니다.")

---

# --- 섹션: 수능 시험날 분석 ---
st.header("🎓 역대 수능 시험날 기온 분석")

# 수능일 데이터 (1994학년도~2025학년도)
suneung_dates = [
    "1993-11-17", "1994-11-23", "1995-11-22", "1996-11-13", "1997-11-19", 
    "1998-11-18", "1999-11-17", "2000-11-15", "2001-11-07", "2002-11-06",
    "2003-11-05", "2004-11-17", "2005-11-23", "2006-11-16", "2007-11-15",
    "2008-11-13", "2009-11-12", "2010-11-18", "2011-11-10", "2012-11-08",
    "2013-11-07", "2014-11-13", "2015-11-12", "2016-11-17", "2017-11-23",
    "2018-11-15", "2019-11-14", "2020-12-03", "2021-11-18", "2022-11-17",
    "2023-11-16", "2024-11-14", "2025-11-13"
]
suneung_dates = pd.to_datetime(suneung_dates)
sn_df = df[df['날짜'].isin(suneung_dates)].copy()

if not sn_df.empty:
    st.write("수능 한파가 실제로 있었을까요? 역대 수능일 최저 기온을 확인해 보세요.")
    
    # 수능일 최저기온 차트
    fig_sn = px.bar(sn_df, x='날짜', y='최저기온(℃)', 
                    color='최저기온(℃)', color_continuous_scale='Bluered_r',
                    text_auto=True, title="역대 수능 시험일 최저기온 기록")
    st.plotly_chart(fig_sn, use_container_width=True)
    
    # 통계 요약
    coldest_sn = sn_df.loc[sn_df['최저기온(℃)'].idxmin()]
    st.success(f"📌 가장 추웠던 수능일: **{coldest_sn['날짜'].date()} ({coldest_sn['최저기온(℃)']}℃)**")
