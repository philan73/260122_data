with c_info:
        st.markdown(f"#### 🔎 {sel_year}년 {level_label} 상세 리포트")
        selected_dist = st.selectbox("자치구 상세 조회", ["전체 요약"] + sorted(map_df['자치구'].tolist()))
        
        if selected_dist != "전체 요약":
            d = map_df[map_df['자치구'] == selected_dist].iloc[0]
            
            # 1. 진단 상태 뱃지
            st.markdown(f"**진단 결과: {d['상태']}**")
            
            # 2. 세 가지 핵심 지표 (학생수, 중단자수, 중단율)
            # 가로 균형을 위해 3컬럼으로 배치하거나, 가독성을 위해 2단 배치를 사용합니다.
            m_col1, m_col2 = st.columns(2)
            m_col1.metric("전체 학생 수", f"{int(d['학생수']):,}명")
            m_col1.metric("학업 중단자 수", f"{int(d['중단자수']):,}명")
            m_col2.metric("학업 중단율", f"{d['학업중단율']}%")
            
            # 시각적 보조 지표 (게이지 바)
            st.write("위기 임계치 대비 현황")
            st.progress(min(d['학업중단율']/2.5, 1.0))
            
        else:
            # 전체 요약 시 서울시 소계 데이터 활용
            total_info = df[(df['연도'] == sel_year) & (df['자치구'] == '소계')].iloc[0]
            st.success(f"**서울시 {level_label} 전체 요약**")
            m_col1, m_col2 = st.columns(2)
            m_col1.metric("서울 전체 학생", f"{int(total_info['학생수']):,}명")
            m_col1.metric("서울 전체 중단자", f"{int(total_info['중단자수']):,}명")
            m_col2.metric("평균 중단율", f"{total_info['학업중단율']}%")

        st.divider()
        st.write(f"**📋 {level_label} 자치구별 현황 목록**")
        # 목록에서도 학생수와 중단자수를 확인할 수 있도록 컬럼 추가 가능
        disp_df = map_df[['자치구', '학생수', '중단자수', '학업중단율', '상태']].sort_values('학업중단율', ascending=False).reset_index(drop=True)
        st.dataframe(disp_df, use_container_width=True, height=280)
