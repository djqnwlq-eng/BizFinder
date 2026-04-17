# 지원사업 찾기 - 소상공인 지원사업 매칭 프로그램
# 메인 Streamlit 앱

import streamlit as st

from config import REGIONS, BUSINESS_TYPES, AGE_GROUPS, SUPPORT_CATEGORIES, BUSINESS_EXPERIENCE
from api_client import get_api_status, get_dummy_data, fetch_all_pages, fetch_all_programs
from utils import calculate_dday, get_status_badge, get_dday_text, get_card_html
from semantic_filter import filter_by_similarity
from gemini_client import get_gemini_status, extract_keywords, recommend_programs

# 페이지 설정
st.set_page_config(
    page_title="지원사업 찾기",
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
if "is_checkbox_mode" not in st.session_state:
    st.session_state.is_checkbox_mode = False
if "is_gemini_mode" not in st.session_state:
    st.session_state.is_gemini_mode = False

# 헤더 영역
st.markdown("""
<div style="display: flex; align-items: baseline; gap: 12px;">
    <h1 style="margin: 0;">🔍 지원사업 찾기</h1>
    <span style="color: #888; font-size: 14px;">Developed by 동행 세무회계사무소</span>
</div>
""", unsafe_allow_html=True)
st.subheader("나에게 딱 맞는 소상공인 지원사업을 찾아보세요")
st.divider()

# 사이드바 - 검색 조건
with st.sidebar:
    # Gemini API 키 입력
    with st.expander("🔑 AI 기능 설정 (Gemini API 키 필요)", expanded=not get_gemini_status()):
        gemini_key_input = st.text_input(
            "Gemini API 키",
            type="password",
            value=st.session_state.get("gemini_api_key", ""),
            placeholder="여기에 발급받은 키를 붙여넣으세요"
        )
        st.session_state.gemini_api_key = gemini_key_input

        if get_gemini_status():
            st.success("AI 연결 완료", icon="✅")
        else:
            st.caption("⚠️ AI 맞춤 추천을 사용하려면 키가 필요합니다.")

        st.markdown("---")
        st.markdown("##### 📖 Gemini API 키 발급 방법 (30초 소요, 무료)")
        st.markdown(
            """
            **1단계.** 아래 버튼을 눌러 Google AI Studio로 이동합니다.

            **2단계.** Google 계정으로 로그인합니다. (구글 ID가 없으면 회원가입)

            **3단계.** 화면의 **`+ Create API key`** 또는 **`API 키 만들기`** 버튼을 클릭합니다.

            **4단계.** 생성된 긴 문자열(예: `AIzaSy...`)을 복사합니다.

            **5단계.** 위 입력창에 붙여넣기(`Ctrl+V` 또는 `Cmd+V`)합니다.
            """
        )
        st.markdown(
            '<a href="https://aistudio.google.com/apikey" target="_blank" '
            'style="display:inline-block; padding:8px 16px; background-color:#4285F4; '
            'color:white; text-decoration:none; border-radius:6px; font-weight:bold;">'
            '👉 Google AI Studio에서 키 발급받기</a>',
            unsafe_allow_html=True
        )
        st.caption("💡 발급받은 키는 본인만 알 수 있도록 안전하게 보관하세요.")

    st.divider()

    st.header("📋 내 정보 입력")

    # 자유 설명 (항상 표시)
    free_description = st.text_area(
        "💬 내 상황 설명 (필수)",
        placeholder="예: 서울에서 카페를 운영하는 30대입니다. 매출이 줄어서 운영자금이 필요하고, 온라인 마케팅도 배우고 싶어요.",
        height=150,
        help="자유롭게 상황을 설명하면 AI가 맞춤 지원사업을 찾아드립니다. 상세 조건과 함께 입력하면 더 정확한 결과를 얻을 수 있습니다."
    )

    st.divider()

    # 상세 조건 (항상 표시)
    st.subheader("📌 상세 조건 (필수)")

    # 1) 연령대
    age_options = ["선택 안함"] + list(AGE_GROUPS.keys())
    age_group = st.radio("연령대", age_options, index=0)

    st.divider()

    # 2) 지역 - 시/도만
    sido_options = ["전국"] + list(REGIONS.keys())
    region_sido = st.selectbox("지역 (시/도)", sido_options, index=0)

    st.divider()

    # 3) 업종
    business_options = ["선택 안함"] + BUSINESS_TYPES
    business_type = st.selectbox("업종", business_options, index=0)

    # 4) 사업 경력
    experience_options = ["선택 안함"] + BUSINESS_EXPERIENCE
    business_experience = st.selectbox("사업 경력", experience_options, index=0)

    st.divider()

    # 5) 접수 상태
    status_options = {
        "접수 중만 보기": "active",
        "접수 예정 포함": "upcoming",
        "전체": "all"
    }
    status_label = st.radio("접수 상태", list(status_options.keys()), index=2)
    status = status_options[status_label]

    # 제거된 항목의 기본값
    free_keyword = None
    region_sigungu = None
    categories = []

    st.divider()

    # 검색 버튼 - 상황 설명 + 상세 조건 전부 입력해야 활성화
    has_description_input = bool(free_description and free_description.strip())
    has_all_conditions = (
        age_group != "선택 안함" and
        business_type != "선택 안함" and
        business_experience != "선택 안함"
    )
    can_search = has_description_input and has_all_conditions

    search_clicked = st.button("🔍 검색하기", type="primary", use_container_width=True, disabled=not can_search)

# 메인 영역 - 결과 표시
if search_clicked:
    # 필터 조건 구성
    filters_dict = {
        "free_description": free_description.strip() if free_description else None,
        "age_group": age_group if age_group != "선택 안함" else None,
        "region_sido": region_sido if region_sido != "전국" else None,
        "business_type": business_type if business_type != "선택 안함" else None,
        "status": status
    }

    # 자유 설명 + 상세 조건을 합쳐서 검색 텍스트 생성
    description_parts = []
    if filters_dict.get("free_description"):
        description_parts.append(filters_dict["free_description"])
    if filters_dict.get("age_group"):
        description_parts.append(filters_dict["age_group"])
    if filters_dict.get("region_sido"):
        description_parts.append(filters_dict["region_sido"])
    if filters_dict.get("business_type"):
        description_parts.append(filters_dict["business_type"])

    combined_description = " ".join(description_parts) if description_parts else ""

    # Gemini 사용 가능 여부
    has_gemini = get_gemini_status() and get_api_status()
    has_description = bool(combined_description.strip())

    # 상단 문구
    st.caption("💬 지원사업은 활용하되, 의존하지 마세요.")

    if has_gemini and has_description:
        # === Gemini + 기업마당 API 연동 모드 ===
        filtered_programs = []

        # 1단계: Gemini가 키워드 확장
        with st.spinner("AI가 검색 키워드를 분석하고 있습니다..."):
            keywords = extract_keywords(combined_description)

        if keywords:
            st.info(f"AI 추출 키워드: {', '.join(keywords)}")

            # 2단계: 키워드별로 기업마당 API 검색
            with st.spinner(f"기업마당에서 {len(keywords)}개 키워드로 검색 중..."):
                programs = fetch_all_programs(keywords)

            if programs:
                # 3단계: Gemini가 최종 추천
                with st.spinner(f"AI가 {len(programs)}건의 지원사업을 분석하고 있습니다..."):
                    if len(programs) > 100:
                        programs = filter_by_similarity(
                            combined_description,
                            programs,
                            top_n=100,
                            min_score=0.1
                        )

                    recommended = recommend_programs(
                        combined_description,
                        programs
                    )

                if recommended:
                    filtered_programs = recommended
                else:
                    st.warning("AI 추천 분석에 실패하여 키워드 매칭 결과를 표시합니다.")
                    filtered_programs = filter_by_similarity(
                        combined_description, programs, top_n=30, min_score=0.2
                    )
            else:
                st.warning("검색 결과가 없습니다. 다른 표현으로 시도해보세요.")
        else:
            st.warning("AI 키워드 분석에 실패하여 기본 검색을 실행합니다.")
            programs = fetch_all_pages(keyword="소상공인", max_pages=10)
            filtered_programs = filter_by_similarity(
                combined_description, programs, top_n=30, min_score=0.2
            )

        # 접수 상태 필터링
        if filters_dict.get("status") == "active":
            filtered_programs = [p for p in filtered_programs
                                 if not p.get("end_date") or
                                 calculate_dday(p.get("end_date", "")) is None or
                                 calculate_dday(p.get("end_date", "")) >= 0]

        st.session_state.show_similarity = True
        st.session_state.is_gemini_mode = True
        st.session_state.is_checkbox_mode = False

    elif has_description:
        # === TF-IDF 폴백 모드 (Gemini 키 없을 때) ===
        if not get_gemini_status():
            st.warning("Gemini API 키가 입력되지 않아 기본 검색으로 실행합니다. 좌측 상단 'AI 기능 설정'에서 키를 입력하면 AI 맞춤 추천이 가능합니다.")

        with st.spinner("지원사업을 검색하고 있습니다..."):
            if get_api_status():
                programs = fetch_all_pages(keyword="소상공인", max_pages=10)
            else:
                st.warning("기업마당 API 연결이 불안정합니다. 테스트 데이터로 표시합니다.")
                programs = get_dummy_data()

            search_description = combined_description + " 지원사업"
            filtered_programs = filter_by_similarity(
                search_description, programs,
                top_n=None, min_score=0.2, match_all=True
            )

            if filters_dict.get("status") == "active":
                filtered_programs = [p for p in filtered_programs
                                     if not p.get("end_date") or
                                     calculate_dday(p.get("end_date", "")) is None or
                                     calculate_dday(p.get("end_date", "")) >= 0]

        st.session_state.show_similarity = True
        st.session_state.is_gemini_mode = False
        st.session_state.is_checkbox_mode = True

    else:
        # === 아무 조건도 입력하지 않은 경우 ===
        st.warning("상황 설명 또는 상세 조건을 하나 이상 입력해주세요.")
        filtered_programs = []
        st.session_state.show_similarity = False
        st.session_state.is_gemini_mode = False
        st.session_state.is_checkbox_mode = False

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
            if st.session_state.get("is_gemini_mode"):
                # Gemini AI 추천 모드
                high_count = sum(1 for r in results if r.get("gemini_relevance") == "high")
                st.success(f"AI 추천 결과: **{len(results)}건** (강력 추천 **{high_count}건**)")
            elif st.session_state.get("show_similarity"):
                # 정확 매칭과 유사 결과 구분
                exact_count = sum(1 for r in results if r.get("is_exact_match"))
                similar_count = len(results) - exact_count

                if st.session_state.get("is_checkbox_mode"):
                    # 체크란 모드: 매칭 개수순 결과
                    total_count = len(results)
                    if total_count > 0:
                        if exact_count > 0:
                            st.success(f"검색 결과: **{total_count}건** (전체 매칭 **{exact_count}건**, 부분 매칭 {total_count - exact_count}건)")
                        else:
                            st.info(f"검색 결과: **{total_count}건** (부분 매칭 - 키워드가 많이 일치하는 순으로 정렬)")
                    else:
                        st.warning("매칭되는 결과가 없습니다. 조건을 줄여서 다시 검색해보세요.")
                else:
                    # 자유 설명 모드 (TF-IDF 폴백): OR 매칭 결과
                    if exact_count > 0:
                        st.success(f"검색 결과: **{len(results)}건** (키워드 정확 매칭 **{exact_count}건**, 유사 결과 {similar_count}건)")
                    elif similar_count > 0:
                        st.warning(f"입력하신 키워드가 제목/내용에 정확히 포함된 결과가 없습니다. 의미상 유사한 **{similar_count}건**을 표시합니다.")
                    else:
                        st.info("검색 결과가 없습니다.")
            else:
                st.success(f"검색 결과: 총 **{len(results)}건**의 지원사업을 찾았습니다.")
        with col2:
            if st.session_state.get("is_gemini_mode"):
                # Gemini 모드: AI 추천순 우선
                sort_option = st.selectbox(
                    "정렬",
                    ["AI 추천순", "마감 임박순", "가나다순"],
                    label_visibility="collapsed"
                )
            elif st.session_state.get("is_checkbox_mode"):
                # 체크란 모드: 매칭 결과순 우선
                sort_option = st.selectbox(
                    "정렬",
                    ["매칭순", "마감 임박순", "가나다순"],
                    label_visibility="collapsed"
                )
            elif st.session_state.get("show_similarity"):
                sort_option = st.selectbox(
                    "정렬",
                    ["관련도순", "마감 임박순", "가나다순"],
                    label_visibility="collapsed"
                )
            else:
                sort_option = st.selectbox(
                    "정렬",
                    ["마감 임박순", "최신 등록순", "가나다순"],
                    label_visibility="collapsed"
                )

        # 정렬 적용
        if sort_option == "AI 추천순":
            # Gemini가 보내준 순서 유지 (이미 적합도순)
            relevance_order = {"high": 0, "medium": 1, "low": 2}
            results = sorted(
                results,
                key=lambda x: relevance_order.get(x.get("gemini_relevance", "low"), 2)
            )
        elif sort_option == "가나다순":
            results = sorted(results, key=lambda x: x.get("title", ""))
        elif sort_option == "최신 등록순":
            results = sorted(results, key=lambda x: x.get("start_date", ""), reverse=True)
        elif sort_option == "관련도순":
            # 키워드 정확 매칭 우선, 그 다음 유사도순
            results = sorted(
                results,
                key=lambda x: (
                    0 if x.get("is_exact_match") else 1,  # 정확 매칭 먼저
                    -x.get("similarity_score", 0)         # 유사도 높은 순
                )
            )
        elif sort_option == "매칭순":
            # 매칭 개수 > 유사도 순
            results = sorted(
                results,
                key=lambda x: (
                    -x.get("matched_count", 0),           # 매칭 개수 많은 순
                    -x.get("similarity_score", 0)         # 유사도 높은 순
                )
            )
        elif sort_option == "마감 임박순":
            # D-day 기준 정렬 (마감 임박한 것부터)
            results = sorted(
                results,
                key=lambda x: (
                    calculate_dday(x.get("end_date", "")) if calculate_dday(x.get("end_date", "")) is not None else 9999
                )
            )
        # 기본값: 정렬 없이 현재 순서 유지

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
        **지원사업 찾기**는 소상공인을 위한 맞춤형 지원사업 검색 서비스입니다.

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
            st.success("기업마당 API 연결 정상")
        else:
            st.warning("기업마당 API 키가 설정되지 않았거나 연결에 문제가 있습니다.")
            st.write("`.env` 파일에 API 키를 입력해주세요:")
            st.code("BIZINFO_API_KEY=발급받은키", language="bash")
            st.write("API 키 발급: https://www.bizinfo.go.kr → API 목록 → 사용신청")

        if get_gemini_status():
            st.success("Gemini AI 연결 정상 (자유 설명 모드에서 AI 추천 사용 가능)")
        else:
            st.warning("Gemini API 키가 설정되지 않았습니다. 좌측 사이드바에서 API 키를 입력해주세요.")

# 푸터
st.divider()
st.caption("데이터 출처: 기업마당(bizinfo.go.kr) | 본 서비스는 참고용이며, 정확한 내용은 해당 기관에 문의하세요.")
