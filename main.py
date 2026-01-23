import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import glob

# 1. GeoJSON 로드 (자치구 경계 및 중심 좌표용)
@st.cache_data
def get_seoul_geojson():
    url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/juso/2015/json/seoul_municipalities_geo_simple.json"
    return requests.get(url).json()

# 2. 자치구별 중심 좌표 (이름 표시용)
@st.cache_data
def get_district_centers():
    # 주요 자치구 위경도 좌표 (이름을 지도에 박기 위함)
    centers = {
        '종로구': [37.5730, 126.9794], '중구': [37.5641, 126.9979], '용산구': [37.5326, 126.9904],
        '성동구': [37.5633, 127.0371], '광진구': [37.5385, 127.0822], '동대문구': [37.5744, 127.0400],
        '중랑구': [37.6065, 127.0927], '성북구': [37.5891, 127.0182], '강북구': [37.6396, 127.0257],
        '도봉구': [37.6688, 127.0471], '노원구': [37.6542, 127.0568], '은평구': [37.6027, 126.9291],
        '서대문구': [37.5791, 126.9368], '마포구': [37.5661, 126.9016], '양천구': [37.5106, 126.8665],
        '강서구': [37.5509, 126.8495], '구로구': [37.4954, 126.8581], '금천구': [37.4565, 126.8954],
        '영등포구': [37.5263, 126.8962], '동작구': [37.5124, 126.9395], '관악구': [37.4784, 126.9513],
        '서초구': [37.4837, 127.0324], '강남구': [37.4959, 127.0664], '송파구': [37.5145, 127.1061],
        '강동구': [37.5302, 127.1238]
    }
    return pd.DataFrame([{'name': k, 'lat': v[0], 'lon': v[1]} for k, v in centers.items()])

# [데이터 로드 부분은 이전과 동일하므로 생략하거나 기존 로직 유지]
# ... (load_data 함수 생략) ...

# --- 지도 시각화 부분 수정 ---
def draw_map(map_df, target_col, school_level, selected_year):
    seoul_geo = get_seoul_geojson()
    centers_df = get_district_centers()
    
    # 1. 배경 경계 및 색상 (Choropleth)
    fig = px.choropleth_mapbox(
        map_df, geojson=seoul_geo, locations='자치구별(2)', featureidkey="properties.name",
        color=target_col, color_continuous_scale="Reds", opacity=0.6,
        mapbox_style="carto-positron", zoom=10, center={"lat": 37.565, "lon": 126.985}
    )

    # 2. 지도 위에 이름 쓰기 (Scatter Mapbox 레이어 추가)
    fig.add_trace(go.Scattermapbox(
        lat=centers_df['lat'],
        lon=centers_df['lon'],
        mode='text',
        text=centers_df['name'],
        textfont={'size': 12, 'color': 'black'},
        showlegend=False,
        hoverinfo='skip'
    ))

    fig.update_layout(margin={"r":0,"t":50,"l":0,"b":0}, title=f"<b>{selected_year}년 {school_level} 학업중단율</b>")
    st.plotly_chart(fig, use_container_width=True)

# 하단 가이드 텍스트 (문제가 되었던 부분 수정)
st.markdown(f"""
### 🎨 지도 색상 가이드 ({school_level} 기준)
- **짙은 빨간색**: 중단율이 상대적으로 **높음**
- **연한 노란색/흰색**: 중단율이 상대적으로 **낮음**
- **글자**: 각 자치구의 위치와 이름을 나타냅니다.
""")
