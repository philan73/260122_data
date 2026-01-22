import streamlit as st
import pandas as pd
import plotly.express as px

# 페이지 설정
st.set_page_config(page_title="학업중단율 분석 대시보드", layout="wide")

# 데이터 로드 및 전처리 함수
@st.cache_data
def load_and_preprocess(file):
    # 상단 3개 행이 헤더이므로 이를 조합하여 읽기
    df_raw = pd.read_csv(file, encoding='utf-8') # 파일에 따라 cp949일 경우 변경
    
    # 헤더 정리 로직
    # 0번 행: 연도, 1번 행: 학교급, 2번 행: 지표명
    headers = df_raw.iloc[:2] 
    data = df_raw.iloc[3:].copy()
    
    # 분석을 위한 데이터 재구조화 (Wide to Long)
    # 현재 데이터는 2024년 고정이나, 향후 여러 연도가 들어올 것을 대비하여 설계
    processed_list = []
    
    schools = ['초등학교', '중학교', '고등학교']
    for school in schools:
        # 각 학교급별 '학업중단자수 (명)' 컬럼 인덱스 찾기
        col_name = f"{school}_중단자" # 임시 구분
        # 실제 데이터 구조에 맞게 슬라이싱 (초: 3, 중: 6, 고: 9 컬럼 근처)
        start_idx = 3 if school == '초등학교' else (6 if school == '중학교' else 9)
        
        temp_df = data[['자치구별(2)']].copy()
        temp_df['학교급'] = school
        temp_df['중단자수'] = pd.to_numeric(data.iloc[:, start_idx], errors='coerce')
        temp_df['학생수'] = pd.to_numeric(data.iloc[:, start_idx-1], errors='coerce')
        temp_df['연도'] = 2024 # 현재 데이터 기준 연도 추출
        processed_list.append(temp_df)
        
    final_df = pd.concat(processed_list, ignore_index=True)
    return final_df

# 사이드바
st.sidebar.title("데이터 업로드")
uploaded_file = st.sidebar.file_uploader("CSV 파일을 업로드하세요", type="csv")

if uploaded_file:
    df = load_and_preprocess(uploaded_file)
    st.sidebar.success("새 데이터를 로드했습니다.")
else:
    # 기본 파일 로드 (제공하신 파일명)
    try:
        df = load_and_preprocess('학업중단율_20260122203740.csv')
        st.sidebar.info("기본 데이터를 사용 중입니다.")
    except:
        st.sidebar.warning("기본 파일을 찾을 수 없습니다.")
        st.stop()

# 메인 화면
st.title("🎓 서울시 자치구별 학업중단 현황 분석")

# 1. 전체 학업중단자 추이 (Plotly)
st.header("📈 학업중단자 수 변화 추이")
# 합계(소계) 데이터만 필터링
summary_df = df[df['자치구별(2)'] == '소계'].groupby(['연도', '학교급'])['중단자수'].sum().reset_index()

fig = px.bar(summary_df, x='연도', y='중단자수', color='학교급',
             barmode='group', title="연도별/학교급별 전체 학업중단자 수",
             labels={'중단자수': '중단자 수 (명)'}, text_auto=True)
st.plotly_chart(fig, use_container_width=True)

# 2. 지역별/학교급별 비교 표
st.header("📊 지역별 상세 비교")

# 자치구 선택 (소계 제외)
districts = df[df['자치구별(2)'] != '소계']['자치구별(2)'].unique()
selected_districts = st.multiselect("비교할 자치구를 선택하세요", districts, default=districts[:5])

if selected_districts:
    comparison_df = df[df['자치구별(2)'].isin(selected_districts)]
    
    # 표 형태 변환 (Pivot)
    table_df = comparison_df.pivot_table(
        index='자치구별(2)', 
        columns='학교급', 
        values='중단자수', 
        aggfunc='sum'
    ).reset_index()
    
    st.subheader("자치구별 학교급 중단자 수")
    st.table(table_df)

    # 인터랙티브 지도/차트 추가 (지역별 비교)
    fig2 = px.sunburst(comparison_df, path=['자치구별(2)', '학교급'], values='중단자수',
                      title="지역 및 학교급별 비중 분석")
    st.plotly_chart(fig2, use_container_width=True)
