# BizFinder - 소상공인 지원사업 매칭 프로그램
# 메인 Streamlit 앱

import streamlit as st

from config import REGIONS, BUSINESS_TYPES, AGE_GROUPS, SUPPORT_CATEGORIES, BUSINESS_EXPERIENCE
from api_client import fetch_all_programs, build_search_keywords, get_api_status, get_dummy_data
from filters import apply_all_filters
from utils import calculate_dday, get_status_badge, get_dday_text, get_card_html

# 페이지 설정
st.set_page_config(
    page_title="BizFinder - 소상공인 지원사업 찾기",
    page_icon="🔍",
    layout="wide"
)

# 커스텀 CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
    }
    .result-count {
        font-size: 1.2rem;
        font-weight: bold;
        color: #333;
        margin-bottom: 1rem;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if "search_results" not in st.session_state:
    st.session_state.search_results = None
if "searched" not in st.session_state:
    st.session_state.searched = False

# 헤더 영역
st.title("🔍 BizFinder")
st.subheader("나에게 딱 맞는 소상공인 지원사업을 찾아보세요")
st.divider()

# 사이드바 - 검색 조건
with st.sidebar:
    st.header("📋 내 정보 입력")

    # 1) 연령대
    age_options = ["선택 안함"] + list(AGE_GROUPS.keys())
    age_group = st.radio("연령대", age_options, index=0)

    st.divider()

    # 2) 지역 - 시/도
    sido_options = ["전국"] + list(REGIONS.keys())
    region_sido = st.selectbox("지역 (시/도)", sido_options, index=0)

    # 3) 지역 - 시/군/구 (동적 변경)
    if region_sido != "전국":
        sigungu_options = ["전체"] + REGIONS.get(region_sido, [])
        region_sigungu = st.selectbox("지역 (시/군/구)", sigungu_options, index=0)
    else:
        region_sigungu = None

    st.divider()

    # 4) 업종
    business_options = ["선택 안함"] + BUSINESS_TYPES
    business_type = st.selectbox("업종", business_options, index=0)

    # 5) 사업 경력
    experience_options = ["선택 안함"] + BUSINESS_EXPERIENCE
    business_experience = st.selectbox("사업 경력", experience_options, index=0)

    st.divider()

    # 6) 관심 분야 (복수 선택)
    categories = st.multiselect("관심 분야 (복수 선택 가능)", SUPPORT_CATEGORIES)

    # 7) 접수 상태
    status_options = {
        "접수 중만 보기": "active",
        "접수 예정 포함": "upcoming",
        "전체": "all"
    }
    status_label = st.radio("접수 상태", list(status_options.keys()), index=0)
    status = status_options[status_label]

    st.divider()

    # 검색 버튼
    search_clicked = st.button("🔍 검색하기", type="primary", use_container_width=True)

# 메인 영역 - 결과 표시
if search_clicked:
    # 필터 조건 구성
    filters_dict = {
        "age_group": age_group if age_group != "선택 안함" else None,
        "region_sido": region_sido if region_sido != "전국" else None,
        "region_sigungu": region_sigungu if region_sigungu and region_sigungu != "전체" else None,
        "business_type": business_type if business_type != "선택 안함" else None,
        "categories": categories if categories else None,
        "status": status
    }

    with st.spinner("지원사업을 검색하고 있습니다..."):
        # API 상태 확인
        if get_api_status():
            # 검색 키워드 생성
            keywords = build_search_keywords(filters_dict)
            # API 호출
            programs = fetch_all_programs(keywords)
        else:
            st.warning("API 연결이 불안정합니다. 테스트 데이터로 표시합니다.")
            programs = get_dummy_data()

        # 필터링 적용
        filtered_programs = apply_all_filters(programs, filters_dict)

        # 결과 저장
        st.session_state.search_results = filtered_programs
        st.session_state.searched = True

# 결과 표시
if st.session_state.searched:
    results = st.session_state.search_results

    if results:
        # 결과 건수 및 정렬 옵션
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success(f"검색 결과: 총 **{len(results)}건**의 지원사업을 찾았습니다.")
        with col2:
            sort_option = st.selectbox(
                "정렬",
                ["마감 임박순", "최신 등록순", "가나다순"],
                label_visibility="collapsed"
            )

        # 정렬 적용
        if sort_option == "가나다순":
            results = sorted(results, key=lambda x: x.get("title", ""))
        elif sort_option == "최신 등록순":
            results = sorted(results, key=lambda x: x.get("start_date", ""), reverse=True)
        # 마감 임박순은 기본값 (이미 정렬됨)

        st.divider()

        # 카드 형태로 결과 표시
        for program in results:
            # D-day 및 상태 계산
            dday = calculate_dday(program.get("end_date", ""))
            status_badge = get_status_badge(
                program.get("start_date", ""),
                program.get("end_date", "")
            )
            dday_text, dday_color = get_dday_text(dday)

            # 카드 HTML 생성 및 표시
            card_html = get_card_html(program, dday, status_badge, dday_text, dday_color)
            st.markdown(card_html, unsafe_allow_html=True)

    else:
        st.info("🔍 검색 조건에 맞는 지원사업이 없습니다.")
        st.write("조건을 완화해서 다시 검색해보세요.")
        tips = [
            "- 지역을 '전국'으로 변경해보세요",
            "- 연령대를 '선택 안함'으로 변경해보세요",
            "- 접수 상태를 '전체'로 변경해보세요"
        ]
        for tip in tips:
            st.write(tip)

else:
    # 검색 전 안내 문구
    st.info("👈 좌측에서 조건을 선택하고 **검색 버튼**을 눌러주세요.")

    # 사용 안내
    with st.expander("💡 사용 방법"):
        st.markdown("""
        **BizFinder**는 소상공인을 위한 맞춤형 지원사업 검색 서비스입니다.

        **검색 방법:**
        1. 좌측 사이드바에서 **연령대, 지역, 업종** 등 조건을 선택하세요
        2. **검색하기** 버튼을 클릭하세요
        3. 검색 결과에서 관심 있는 지원사업의 **상세보기**를 클릭하세요

        **팁:**
        - 조건을 적게 선택할수록 더 많은 결과가 나옵니다
        - 마감이 임박한 사업은 🟠 표시로 강조됩니다
        """)

    # API 상태 표시
    with st.expander("ℹ️ 시스템 정보"):
        if get_api_status():
            st.success("✅ 기업마당 API 연결 정상")
        else:
            st.warning("⚠️ API 키가 설정되지 않았거나 연결에 문제가 있습니다.")
            st.write("`.env` 파일에 API 키를 입력해주세요:")
            st.code("BIZINFO_API_KEY=발급받은키", language="bash")
            st.write("API 키 발급: https://www.bizinfo.go.kr → API 목록 → 사용신청")

# 푸터
st.divider()
st.caption("데이터 출처: 기업마당(bizinfo.go.kr) | 본 서비스는 참고용이며, 정확한 내용은 해당 기관에 문의하세요.")
