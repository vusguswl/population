import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="우리 동네 인구 피라미드", page_icon="👨‍👩‍👧‍👦", layout="centered"
)

st.title("👨‍👩‍👧‍👦 우리 동네 인구 피라미드")
st.caption(
    "원하는 지역을 선택하여 연령별 남녀 인구 구성을 확인해 보세요! 따뜻하고 한눈에 보기 쉬운 그래프로 제공됩니다."
)


# 2. 데이터 불러오기 (캐싱을 적용하여 앱 속도 최적화)
@st.cache_data
def load_data():
    # 데이터 URL 지정
    url = "https://github.com/vusguswl/population/blob/main/population_ts_yearly_gender.zip?raw=true"

    # pandas로 zip 파일 직접 읽기 (GitHub raw 주소 활용)
    df = pd.read_csv(url, compression="zip")

    # 가장 최신 연도 데이터만 추출
    latest_year = df["연도"].max()
    df_latest = df[df["연도"] == latest_year].copy()

    return df_latest, latest_year


# 데이터 로딩 상태 표시
with st.spinner("최신 인구 데이터를 불러오는 중입니다..."):
    df, latest_year = load_data()

st.success(f"기준 연도: **{latest_year}년** 최신 데이터가 반영되었습니다.")
st.markdown("---")


# 3. 드롭다운 연동 (시도 -> 시군구 -> 동)
col1, col2, col3 = st.columns(3)

with col1:
    sido_list = sorted(df["시도"].dropna().unique())
    selected_sido = st.selectbox("시·도 선택", sido_list)

# 선택한 시도에 해당하는 시군구 목록 필터링
filtered_sigungu = df[df["시도"] == selected_sido]

with col2:
    sigungu_list = sorted(filtered_sigungu["시군구"].dropna().unique())
    selected_sigungu = st.selectbox("시·군·구 선택", sigungu_list)

# 선택한 시군구에 해당하는 동 목록 필터링
filtered_dong = filtered_sigungu[filtered_sigungu["시군구"] == selected_sigungu]

with col3:
    dong_list = sorted(filtered_dong["동"].dropna().unique())
    selected_dong = st.selectbox("읍·면·동 선택", dong_list)


# 4. 선택한 지역의 데이터 추출 및 정제
target_row = filtered_dong[filtered_dong["동"] == selected_dong]

if not target_row.empty:
    row = target_row.iloc[0]

    # 나이 카테고리 순서 정의 (0세부터 100세 이상까지 순서 고정)
    age_labels = [f"{i}세" for i in range(100)] + ["100세 이상"]

    # 남성 및 여성 인구 데이터 추출
    male_pop = [row[f"남_{age}"] for age in age_labels]
    female_pop = [row[f"여_{age}"] for age in age_labels]

    # 남성 인구수는 왼쪽 배치를 위해 음수(-)로 변환
    male_pop_neg = [-val for val in male_pop]

    # 5. Plotly 인구 피라미드 그래프 생성
    fig = go.Figure()

    # 남성 막대 그래프 (왼쪽, 따뜻한 톤의 파란색/코발트)
    fig.add_trace(
        go.Bar(
            y=age_labels,
            x=male_pop_neg,
            name="남성",
            orientation="h",
            marker=dict(color="#5B8FF9"),
            customdata=male_pop,  # 툴팁에 보여줄 양수 원래 값
            hovertemplate="<b>%{y}</b> 남성 인구: %{customdata:,}명<extra></extra>",
        )
    )

    # 여성 막대 그래프 (오른쪽, 따뜻한 톤의 붉은색/산호색)
    fig.add_trace(
        go.Bar(
            y=age_labels,
            x=female_pop,
            name="여성",
            orientation="h",
            marker=dict(color="#F6866A"),
            hovertemplate="<b>%{y}</b> 여성 인구: %{x:,}명<extra></extra>",
        )
    )

    # 그래프 레이아웃 스타일 설정
    fig.update_layout(
        title=f"<b>{selected_sido} {selected_sigungu} {selected_dong}</b> 인구 피라미드",
        title_font_size=18,
        barmode="overlay",  # 양쪽으로 갈라지는 막대 배치
        bargap=0.1,
        xaxis=dict(
            title="인구수 (명)",
            tickformat=",",  # 천 단위 쉼표 표기
            # x축 눈금에 음수가 아닌 양수로 표시되도록 콜백 처리
            tickvals=[-max(male_pop + female_pop), 0, max(male_pop + female_pop)],
            ticktext=[
                f"{max(male_pop + female_pop):,}",
                "0",
                f"{max(male_pop + female_pop):,}",
            ],
        ),
        yaxis=dict(
            title="연령대",
            type="category",  # 세로축을 범주형(category)으로 설정
            categoryorder="array",  # 입력한 나이 배열 순서 그대로 유지
            categoryarray=age_labels,  # 0세(맨 아래) ~ 100세 이상(맨 위)
        ),
        legend=dict(x=0.8, y=1.05, orientation="h"),
        height=700,
        margin=dict(l=60, r=60, t=80, b=50),
        template="plotly_white",
    )

    # Streamlit 화면에 그래프 출력
    st.plotly_chart(fig, use_container_width=True)

    # 하단 요약 정보
    total_male = sum(male_pop)
    total_female = sum(female_pop)
    total_pop = total_male + total_female

    m_col, f_col, t_col = st.columns(3)
    m_col.metric("총 남성 인구", f"{total_male:,} 명")
    f_col.metric("총 여성 인구", f"{total_female:,} 명")
    t_col.metric("전체 인구수", f"{total_pop:,} 명")

else:
    st.warning("선택한 지역의 인구 데이터가 없습니다.")
