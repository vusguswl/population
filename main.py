# 2-2. GeoJSON 로드 (requests 활용)
# Commit 페이지 URL 대신 파일의 Raw URL / 지점 URL을 정확하게 사용해야 합니다.
geojson_url = "https://raw.githubusercontent.com/vusguswl/population/bbe9dde463bdbe8592e6b85569fdc4c4d2905338/sigungu.geojson"

res = requests.get(geojson_url)
# HTTP 요청 성공 여부 확인 (404/500 에러 발생 시 예외 발생)
res.raise_for_status()

try:
    geojson_data = res.json()
except Exception as e:
    st.error("GeoJSON 데이터를 JSON으로 해석하지 못했습니다. URL을 확인해 주세요.")
    st.stop()
