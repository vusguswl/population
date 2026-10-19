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
    df_2026["코드_str"] = df_2026["코드"].astype(str).str.zfill(8)
    df_2026["sigungu_code"] = df_2026["코드_str"].str[:5]

    # '계_'로 시작하는 나이별 인구 열 찾기 (0세 ~ 100세 이상)
    total_age_cols = [c for c in df_2026.columns if c.startswith("계_")]

    # 65세 이상 인구 열 선별 ('계_65세' ~ '계_100세 이상')
    age_65_plus_labels = [f"계_{i}세" for i in range(65, 100)] + ["계_100세 이상"]
    elderly_cols = [c for c in total_age_cols if c in age_65_plus_labels]

    # 시군구별 전체 인구수 및 65세 이상 인구수 합산
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

    # 시도/시군구 명칭 맵핑용 지표 추출
    name_map = (
        df_2026.groupby("sigungu_code")
        .agg({"시도": "first", "시군구": "first"})
        .reset_index()
    )
    sigungu_df = pd.merge(sigungu_df, name_map, on="sigungu_code", how="left")

    # 2-2. GeoJSON 가져오기 (GitHub commit raw, API, 대체 CDN 다중 접근)
    geojson_urls = [
        "https://raw.githubusercontent.com/vusguswl/population/bbe9dde463bdbe8592e6b85569fdc4c4d2905338/sigungu.geojson",
        "https://raw.githubusercontent.com/vusguswl/population/main/sigungu.geojson",
        "https://cdn.jsdelivr.net/gh/vusguswl/population@main/sigungu.geojson",
        "https://southkorea-geojson.github.io/southkorea-maps/kostat/2013/json/skorea_municipalities_2013_geo.json",  # 대한민국 시군구 표준 GeoJSON (Fallback)
    ]

    headers = {"User-Agent": "Mozilla/5.0"}
    geojson_data = None

    for url in geojson_urls:
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if "features" in data:
                    geojson_data = data
                    break
        except Exception:
            continue

    if geojson_data is None:
        raise Exception(
            "GeoJSON 데이터를 다운로드할 수 없습니다. 인터넷 연결 및 URL 상태를 확인해 주세요."
        )

    # GeoJSON 내 '코드' 속성 정제 및 5자리 규격화
    for feature in geojson_data["features"]:
        props = feature["properties"]
        # 속성명이 '코드', 'code', 'SIG_CD' 등 다양할 수 있어 대응
        code_val = (
            props.get("코드")
            or props.get("code")
             ancient
            or props.get("SIG_CD")
            or ""
        )
        code_val = str(code_val).zfill(5)[:5]
        props["코드"] = code_val

        # 시도, 시군구 이름 보완
        if "시도" not in props and "sidoname" in props:
            props["시도"] = props["sidoname"]
        if "시군구" not in props and "name" in props:
            props["시군구"] = props["name"]

    return sigungu_df, geojson_data


# 데이터 로딩 실행
try:
    with st.spinner(
        "2026년 인구 데이터 및 시군구 경계 지도를 불러오는 중입니다..."
    ):
        sigungu_df, geojson_data = load_data()
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()


# 3. Plotly Choropleth Mapbox 생성
fig = px.choropleth_mapbox(
    sigungu_df,
    geojson=geojson_data,
    locations="sigungu_code",
    featureidkey="properties.코드",
    color="elderly_ratio",
    color_continuous_scale="Reds",
    range_color=(
        sigungu_df["elderly_ratio"].min(),
        sigungu_df["elderly_ratio"].max(),
    ),
    mapbox_style="white-bg",
    zoom=6.2,
    center={"lat": 35.9, "lon": 127.8},
    opacity=0.85,
    hover_name="sigungu_code",
    hover_data={
        "sigungu_code": False,
        "시도": True,
        "시군구": True,
        "elderly_ratio": ":.1f",
    },
    labels={"elderly_ratio": "고령화율 (%)"},
)

# 호버 툴팁 스타일 가공 (시도, 시군구 이름 및 고령화율 표시)
fig.update_traces(
    marker_line_width=0.5,
    marker_line_color="#444444",
    hovertemplate="<b>%{customdata[0]} %{customdata[1]}</b><br>고령화율: <b>%{z:.1f}%</b><extra></extra>",
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

# 4. 화면 출력
st.plotly_chart(fig, use_container_width=True)

# 주요 핵심 지표 카드
col1, col2, col3 = st.columns(3)
col1.metric("전국 평균 고령화율", f"{sigungu_df['elderly_ratio'].mean():.1f}%")
col2.metric(
    "최고 고령화 지역 비율", f"{sigungu_df['elderly_ratio'].max():.1f}%"
)
col3.metric(
    "최저 고령화 지역 비율", f"{sigungu_df['elderly_ratio'].min():.1f}%"
)
