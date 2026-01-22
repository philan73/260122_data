import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="서울 기온 분석 앱", layout="wide")

# 데이터 로드 및 전처리 함수
@st.cache_data
def load_and_clean_data(file_source):
    # 인코딩은 공공데이터 표준인 cp949 사용
    df = pd.read_csv(file_source, encoding='cp949')
    
    # 날짜 데이터 정제 (탭 문자 제거 및 변환)
    df['날짜'] = df['날짜'].astype(str).str.replace('\t', '').str.strip()
    df['날짜'] = pd.to_datetime(df['날짜'])
    
    # 분석용 파생 변수
    df['year'] = df['날짜'].dt.year
    df['month_day'] = df['날짜'].dt.strftime('%m-%d')
    return df

# 사이드바 설정
st.sidebar.title("데이터 설정")
uploaded_file = st.sidebar.file_uploader("추가 기온 데이터 업로드 (CSV)", type="csv")

# 데이터 로드 로직
if uploaded_file is not None:
    df = load_and_clean_data(uploaded_file)
    st.sidebar.success("사용자 데이터를 적용했습니다.")
else:
    try:
        df = load_and_clean_data('ta_20260122174530.csv')
        st.sidebar.info("기본 시스템 데이터를 사용 중입니다.")
    except Exception as e:
        st.error(f"데이터를 찾을 수 없습니다. 파일을 업로드해주세요.")
        st.stop()

# 메인 섹션 1: 날짜 비교 분석
st.title("🌡️ 서울 기온 역사 비교기")

# 날짜 선택 (기본값: 데이터셋의 가장 최근 날짜)
latest_date = df['날짜'].max().date()
selected_date = st.date_input("비교하고 싶은 날짜를 선택하세요", latest_date)
target_md = selected_date.strftime('%m-%d')

# 동일 날짜(월-일) 역대 데이터 필터링 (결측치 제외)
historical_same_day = df[df['month_day'] == target_md].dropna(subset=['평균기온(℃)'])

if not historical_same_day.empty:
    avg_temp = historical_same_day['평균기온(℃)'].mean()
    target_row = historical_same_day[historical_same_day['year'] == selected_date.year]
    
    col1, col2 = st.columns(2)
    if not target_row.empty:
        current_temp = target_row['평균기온(℃)'].values[0]
        diff = current_temp - avg_temp
        col1.metric(f"{selected_date.year}년 당일 기온", f"{current_temp} ℃")
        col2.metric("역대 평균 대비", f"{round(diff, 2)} ℃", delta=round(diff, 2))
        
        status = "더웠습니다" if diff > 0 else "추웠습니다"
        st.info(f"📅 **{selected_date.year}년 {target_md}**는 역대 평균({round(avg_temp, 2)}℃)보다 **{abs(round(diff, 2))}℃ 더 {status}.**")
    else:
        st.warning(f"{selected_date.year}년 데이터가 없습니다. 역대 추이를 확인하세요.")

    # 역대 같은 날짜 기온 그래프
    fig = px.line(historical_same_day, x='year', y='평균기온(℃)', markers=True, 
                  title=f"역대 {target_md} 평균 기온 변화 (1907-2025)")
    fig.add_hline(y=avg_temp, line_dash="dash", line_color="red", annotation_text="전체 평균")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# 메인 섹션 2: 수능 시험날 분석 (1994~2025)
st.header("🎓 역대 수능 시험날 기온 분석")

# 1994학년도(1993년 시행) ~ 2025학년도 수능 날짜 리스트
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
    st.write("수능 시험날 최저 기온을 통해 '수능 한파'를 분석합니다.")
    
    # 수능일 최저기온 시각화
    fig_sn = px.bar(sn_df, x='날짜', y='최저기온(℃)', color='최저기온(℃)', 
                    color_continuous_scale='IceFire', title="역대 수능일 최저기온 추이")
    st.plotly_chart(fig_sn, use_container_width=True)
    
    # 가장 추웠던 날 정보
    coldest_day = sn_df.loc[sn_df['최저기온(℃)'].idxmin()]
    st.error(f"❄️ 역대 가장 추웠던 수능일: **{coldest_day['날짜'].date()} ({coldest_day['최저기온(℃)']}℃)**")
