import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="전국 시군구 고령화 단계구분도",
    page_icon="🗺️",
    layout="wide",
)

st.title("🗺️ 2026년 전국 시군구 고령화 단계구분도")
st.caption(
    "2026년 최신 읍·면·동 인구 데이터를 시군구 단위(코드 5자리)로 집계하여 고령화율(65세 이상 비율, %)을 단계구분도로 나타냅니다."
)


# 2. 데이터 및 GeoJSON 캐싱 로드
@st.cache_data
def load_data():
    # 2-1. 인구 데이터 로드 (zip CSV)
    pop_url = "https://github.com/vusguswl/population/blob/main/population_ts_yearly_gender.zip?raw=true"
    df = pd.read_csv(pop_url, compression="zip")

    # 2026년 데이터만 추출
    df_2026 = df[df["연도"] == 2026].copy()

    # 동 코드를 5자리 문자열(시군구 코드)로 변환
    # 코드가 숫자/문자열 상관없이 안정적으로 5자리가 되도록 처리
    df_2026["코드_str"] = df_2026["코드"].astype(str).str.zfill(8)
    df_2026["sigungu_code"] = df_2026["코드_str"].str[:5]

    # '계_'로 시작하는 나이별 인구 열 찾기 (0세 ~ 100세 이상)
    total_age_cols = [c for c in df_2026.columns if c.startswith("계_")]

    # 65세 이상 인구 열 선별 ('계_65세' ~ '계_100세 이상')
    # age_labels 리스트를 정확히 매칭
    age_65_plus_labels = [f"계_{i}세" for i in range(65, 100)] + ["계_100세 이상"]
    elderly_cols = [c for c in total_age_cols if c in age_65_plus_labels]

    # 시군구별 전체 인구수 및 65세 이상 인구수 합산
    # '계_' 열만 합산하므로 남_·여_ 열은 이중 계산되지 않음
    df_2026["tot_pop"] = df_2026[total_age_cols].sum(axis=1)
    df_2026["elderly_pop"] = df_2026[elderly_cols].sum(axis=1)

    sigungu_df = (
        df_2026.groupby("sigungu_code", as_index=False)[
            ["tot_pop", "elderly_pop"]
        ]
        .sum()
    )

    # 시군구별 고령화율(%) 계산
    sigungu_df["elderly_ratio"] = (
        sigungu_df["elderly_pop"] / sigungu_df["tot_pop"]
    ) * 100
    sigungu_df["elderly_ratio"] = sigungu_df["elderly_ratio"].round(1)

    # 2-2. GeoJSON 로드 (requests 활용)
    geojson_url = "https://raw.githubusercontent.com/vusguswl/population/bbe9dde463bdbe8592e6b85569fdc4c4d2905338/sigungu.geojson"
    res = requests.get(geojson_url)
    geojson_data = res.json()

    # GeoJSON 내 '코드' 속성도 5자리 문자열로 고정
    for feature in geojson_data["features"]:
        code_val = str(feature["properties"]["코드"]).zfill(5)
        feature["properties"]["코드"] = code_val

    return sigungu_df, geojson_data


# 데이터 로딩 실행
with st.spinner("2026년 인구 데이터 및 시군구 경계 지도를 불러오는 중입니다..."):
    sigungu_df, geojson_data = load_data()


# 3. Plotly Choropleth Mapbox 생성
# 배경 타일 없이 경계선과 색상 표현을 위해 Mapbox 스타일 'white-bg' 지정
fig = px.choropleth_mapbox(
    sigungu_df,
    geojson=geojson_data,
    locations="sigungu_code",
    featureidkey="properties.코드",
    color="elderly_ratio",
    color_continuous_scale="Reds",  # 고령화율이 높을수록 진한 붉은색
    range_color=(sigungu_df["elderly_ratio"].min(), sigungu_df["elderly_ratio"].max()),
    mapbox_style="white-bg",
    zoom=6.2,
    center={"lat": 35.9, "lon": 127.8},  # 대한민국 중심 좌표
    opacity=0.85,
    hover_name="sigungu_code",  # hover_data 속성과 함께 사용
    hover_data={"sigungu_code": False, "elderly_ratio": ":.1f"},
    labels={"elderly_ratio": "고령화율 (%)"},
)

# GeoJSON 속성('시군구', '시도')을 호버 툴팁에 연결 및 스타일 가공
# 지도 레이아웃 가공: 배경 타일 비활성화, 경계선 세밀 표현
fig.update_traces(
    marker_line_width=0.5,
    marker_line_color="#444444",
    # 호버 시 GeoJSON의 '시도', '시군구'와 고령화율(%)이 명확히 보이도록 설정
    hovertemplate="<b>%{properties.시도} %{properties.시군구}</b><br>고령화율: <b>%{z:.1f}%</b><extra></extra>",
)

fig.update_layout(
    margin={"r": 0, "t": 40, "l": 0, "b": 0},
    height=750,
    coloraxis_colorbar=dict(
        title="고령화율 (%)",
        ticksuffix="%",
        len=0.8,
    ),
)

# 4. 앱 화면 출력
st.plotly_chart(fig, use_container_width=True)

# 전국 핵심 요약 지표
col1, col2, col3 = st.columns(3)
col1.metric("전국 평균 고령화율", f"{sigungu_df['elderly_ratio'].mean():.1f}%")
col2.metric(
    "최고 고령화 지역 비율", f"{sigungu_df['elderly_ratio'].max():.1f}%"
)
col3.metric(
    "최저 고령화 지역 비율", f"{sigungu_df['elderly_ratio'].min():.1f}%"
)
