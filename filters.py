# 필터링 로직 모듈
# API 응답 데이터를 사용자 조건에 맞게 필터링

from datetime import datetime
from config import AGE_GROUPS, REGIONS


def filter_by_age(programs, age_group):
    """
    연령대 기준 필터링

    Args:
        programs: 지원사업 리스트
        age_group: 선택한 연령대 (예: "청년 (만 19~34세)")

    Returns:
        list: 필터링된 지원사업 리스트
    """
    if not age_group or age_group == "선택 안함":
        return programs

    keywords = AGE_GROUPS.get(age_group, [])
    if not keywords:
        return programs

    filtered = []
    for program in programs:
        target = program.get("target", "").lower()
        description = program.get("description", "").lower()
        combined_text = f"{target} {description}"

        # 키워드가 포함되어 있거나, 연령 제한이 명시되지 않은 경우
        has_age_keyword = any(kw.lower() in combined_text for kw in keywords)
        has_any_age_restriction = any(
            any(kw.lower() in combined_text for kw in age_keywords)
            for age_keywords in AGE_GROUPS.values()
        )

        if has_age_keyword or not has_any_age_restriction:
            filtered.append(program)

    return filtered


def filter_by_region(programs, sido, sigungu=None):
    """
    지역 기준 필터링

    Args:
        programs: 지원사업 리스트
        sido: 시/도 (예: "전북특별자치도")
        sigungu: 시/군/구 (예: "군산시")

    Returns:
        list: 필터링된 지원사업 리스트
    """
    if not sido or sido == "전국":
        return programs

    filtered = []
    for program in programs:
        target = program.get("target", "")
        description = program.get("description", "")
        combined_text = f"{target} {description}"

        # 전국 대상 사업은 포함
        if "전국" in combined_text:
            filtered.append(program)
            continue

        # 지역 제한이 없는 경우 포함
        has_any_region = any(
            region in combined_text
            for region in REGIONS.keys()
        )
        if not has_any_region:
            filtered.append(program)
            continue

        # 시/도 매칭
        if sido in combined_text:
            # 시/군/구까지 선택한 경우 추가 확인
            if sigungu and sigungu != "전체":
                if sigungu in combined_text or sido in combined_text:
                    filtered.append(program)
            else:
                filtered.append(program)

    return filtered


def filter_by_business_type(programs, business_type):
    """
    업종 기준 필터링

    Args:
        programs: 지원사업 리스트
        business_type: 선택한 업종

    Returns:
        list: 필터링된 지원사업 리스트
    """
    if not business_type or business_type == "선택 안함":
        return programs

    # 업종 관련 키워드 확장
    business_keywords = {
        "도소매업": ["도소매", "소매", "판매", "유통", "상점"],
        "음식점업": ["음식점", "식당", "요식업", "외식", "카페", "베이커리"],
        "숙박업": ["숙박", "호텔", "펜션", "모텔", "민박"],
        "제조업": ["제조", "생산", "공장"],
        "서비스업": ["서비스", "미용", "세탁", "수리"],
        "건설업": ["건설", "건축", "인테리어"],
        "운수업": ["운수", "운송", "물류", "택배", "택시"],
        "교육서비스업": ["교육", "학원", "학습"],
        "보건업": ["보건", "의료", "병원", "약국", "의원"],
        "예술/스포츠/여가": ["예술", "스포츠", "여가", "문화", "레저"],
        "정보통신업": ["정보통신", "IT", "소프트웨어", "인터넷"],
        "농림어업": ["농업", "어업", "축산", "임업", "농림"],
        "기타": []
    }

    keywords = business_keywords.get(business_type, [business_type])

    filtered = []
    for program in programs:
        target = program.get("target", "")
        description = program.get("description", "")
        combined_text = f"{target} {description}"

        # 업종 키워드가 포함되어 있거나, 업종 제한이 없는 경우
        has_business_keyword = any(kw in combined_text for kw in keywords)
        has_any_business_restriction = any(
            any(kw in combined_text for kw in kws)
            for kws in business_keywords.values() if kws
        )

        if has_business_keyword or not has_any_business_restriction:
            filtered.append(program)

    return filtered


def filter_by_category(programs, categories):
    """
    분야 기준 필터링 (복수 선택 가능)

    Args:
        programs: 지원사업 리스트
        categories: 선택한 분야 리스트 (예: ["금융", "창업"])

    Returns:
        list: 필터링된 지원사업 리스트
    """
    if not categories:
        return programs

    filtered = []
    for program in programs:
        category = program.get("category", "")
        if any(cat in category for cat in categories):
            filtered.append(program)
        elif not category:  # 분야가 명시되지 않은 경우 포함
            filtered.append(program)

    return filtered


def filter_by_status(programs, status="active"):
    """
    접수 상태 기준 필터링

    Args:
        programs: 지원사업 리스트
        status: "active" (접수 중), "upcoming" (접수 예정), "all" (전체)

    Returns:
        list: 필터링된 지원사업 리스트
    """
    if status == "all":
        return programs

    today = datetime.now().date()
    filtered = []

    for program in programs:
        start_date = parse_date(program.get("start_date", ""))
        end_date = parse_date(program.get("end_date", ""))

        if not end_date:
            # 날짜 정보가 없으면 포함
            filtered.append(program)
            continue

        if status == "active":
            # 접수 중: 시작일 <= 오늘 <= 종료일
            start_ok = start_date is None or start_date <= today
            end_ok = end_date >= today
            if start_ok and end_ok:
                filtered.append(program)
        elif status == "upcoming":
            # 접수 예정: 오늘 < 시작일
            if start_date and start_date > today:
                filtered.append(program)

    return filtered


def parse_date(date_str):
    """
    다양한 형식의 날짜 문자열을 파싱

    Args:
        date_str: 날짜 문자열

    Returns:
        datetime.date 또는 None
    """
    if not date_str:
        return None

    date_str = date_str.strip()
    formats = [
        "%Y-%m-%d",
        "%Y.%m.%d",
        "%Y/%m/%d",
        "%Y%m%d"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    return None


def apply_all_filters(programs, filters_dict):
    """
    모든 필터를 순차적으로 적용하는 통합 함수

    Args:
        programs: 지원사업 리스트
        filters_dict: 필터 조건 딕셔너리
            - age_group: 연령대
            - region_sido: 시/도
            - region_sigungu: 시/군/구
            - business_type: 업종
            - categories: 분야 리스트
            - status: 접수 상태

    Returns:
        list: 필터링 및 정렬된 지원사업 리스트
    """
    result = programs

    # 연령대 필터
    if filters_dict.get("age_group"):
        result = filter_by_age(result, filters_dict["age_group"])

    # 지역 필터
    if filters_dict.get("region_sido"):
        result = filter_by_region(
            result,
            filters_dict["region_sido"],
            filters_dict.get("region_sigungu")
        )

    # 업종 필터
    if filters_dict.get("business_type"):
        result = filter_by_business_type(result, filters_dict["business_type"])

    # 분야 필터
    if filters_dict.get("categories"):
        result = filter_by_category(result, filters_dict["categories"])

    # 접수 상태 필터
    status = filters_dict.get("status", "active")
    result = filter_by_status(result, status)

    # 마감일 임박순으로 정렬
    result = sort_by_deadline(result)

    return result


def sort_by_deadline(programs):
    """
    마감일 임박순으로 정렬

    Args:
        programs: 지원사업 리스트

    Returns:
        list: 정렬된 리스트
    """
    def get_sort_key(program):
        end_date = parse_date(program.get("end_date", ""))
        if end_date:
            return end_date
        # 날짜가 없으면 맨 뒤로
        return datetime.max.date()

    return sorted(programs, key=get_sort_key)
