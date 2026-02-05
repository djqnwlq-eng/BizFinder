# API 호출 모듈
# 기업마당(Bizinfo) API와 통신하는 함수들

import os
import time
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

# API 기본 설정
API_URL = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
API_BASE_URL = "https://www.bizinfo.go.kr"


def get_api_key():
    """환경변수에서 API 키를 가져오는 함수"""
    api_key = os.getenv("BIZINFO_API_KEY")
    if not api_key or api_key == "여기에키입력":
        return None
    return api_key


def fetch_support_programs(keyword="", category="", page=1, page_size=20):
    """
    지원사업 목록을 가져오는 함수

    Args:
        keyword: 검색 키워드 (예: "청년", "소상공인")
        category: 분야 필터
        page: 페이지 번호
        page_size: 한 페이지당 결과 수

    Returns:
        list: 지원사업 딕셔너리 리스트
    """
    api_key = get_api_key()
    if not api_key:
        print("API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")
        return []

    params = {
        "crtfcKey": api_key,
        "dataType": "json",
        "pageNo": page,
        "numOfRows": page_size,
        "keyword": keyword
    }

    if category:
        params["bizPbancCtgy"] = category

    try:
        response = requests.get(API_URL, params=params, timeout=10)
        response.raise_for_status()

        # JSON 응답 처리
        try:
            data = response.json()
            return parse_json_response(data)
        except:
            # XML 응답 처리
            return parse_xml_response(response.text)

    except requests.exceptions.Timeout:
        print("API 요청 시간 초과")
        return []
    except requests.exceptions.RequestException as e:
        print(f"API 호출 오류: {e}")
        return []


def parse_json_response(data):
    """JSON 응답을 파싱하는 함수"""
    programs = []

    try:
        # 기업마당 API 응답 구조에 맞게 파싱
        items = data.get("jsonArray", [])
        if not items:
            items = data.get("response", {}).get("body", {}).get("items", [])

        for item in items:
            # 링크 처리 - 상대 경로면 기본 URL 추가
            link = item.get("detailUrl", item.get("link", item.get("pblancUrl", "")))
            if link and link.startswith("/"):
                link = API_BASE_URL + link

            program = {
                "title": item.get("pblancNm", item.get("title", "")),
                "target": item.get("jrsdInsttNm", item.get("target", "")),
                "agency": item.get("excInsttNm", item.get("agency", "")),
                "category": item.get("bizPbancCtgy", item.get("category", "")),
                "start_date": item.get("reqstBeginEndDe", item.get("startDate", "")).split("~")[0].strip() if "~" in item.get("reqstBeginEndDe", "") else item.get("pbancRcptBgngDt", ""),
                "end_date": item.get("reqstBeginEndDe", item.get("endDate", "")).split("~")[-1].strip() if "~" in item.get("reqstBeginEndDe", "") else item.get("pbancRcptEndDt", ""),
                "link": link,
                "description": item.get("bsnsSumryCn", item.get("description", ""))
            }
            programs.append(program)
    except Exception as e:
        print(f"JSON 파싱 오류: {e}")

    return programs


def parse_xml_response(xml_text):
    """XML 응답을 파싱하는 함수"""
    programs = []

    try:
        root = ET.fromstring(xml_text)
        items = root.findall(".//item")

        for item in items:
            # 링크 처리 - 상대 경로면 기본 URL 추가
            link = get_xml_text(item, "detailUrl") or get_xml_text(item, "pblancUrl") or get_xml_text(item, "link")
            if link and link.startswith("/"):
                link = API_BASE_URL + link

            program = {
                "title": get_xml_text(item, "pblancNm") or get_xml_text(item, "title"),
                "target": get_xml_text(item, "jrsdInsttNm") or get_xml_text(item, "target"),
                "agency": get_xml_text(item, "excInsttNm") or get_xml_text(item, "agency"),
                "category": get_xml_text(item, "bizPbancCtgy") or get_xml_text(item, "category"),
                "start_date": get_xml_text(item, "pbancRcptBgngDt") or get_xml_text(item, "startDate"),
                "end_date": get_xml_text(item, "pbancRcptEndDt") or get_xml_text(item, "endDate"),
                "link": link,
                "description": get_xml_text(item, "bsnsSumryCn") or get_xml_text(item, "description")
            }
            programs.append(program)
    except ET.ParseError as e:
        print(f"XML 파싱 오류: {e}")

    return programs


def get_xml_text(element, tag):
    """XML 요소에서 텍스트를 안전하게 가져오는 함수"""
    found = element.find(tag)
    return found.text if found is not None and found.text else ""


def fetch_all_programs(keywords_list, category=""):
    """
    여러 키워드로 반복 호출해서 결과를 합치는 함수

    Args:
        keywords_list: 검색할 키워드 리스트
        category: 분야 필터

    Returns:
        list: 중복 제거된 지원사업 리스트
    """
    all_programs = []
    seen_titles = set()

    for keyword in keywords_list:
        programs = fetch_support_programs(keyword=keyword, category=category)

        for program in programs:
            title = program.get("title", "")
            if title and title not in seen_titles:
                seen_titles.add(title)
                all_programs.append(program)

        # API 서버 부담 방지를 위한 딜레이
        time.sleep(0.5)

    return all_programs


def get_api_status():
    """
    API 연결 상태 확인용 함수

    Returns:
        bool: API 연결 가능 여부
    """
    api_key = get_api_key()
    if not api_key:
        return False

    try:
        params = {
            "crtfcKey": api_key,
            "dataType": "json",
            "pageNo": 1,
            "numOfRows": 1
        }
        response = requests.get(API_URL, params=params, timeout=5)
        if response.status_code != 200:
            return False

        # 응답 내용에서 에러 체크
        data = response.json()
        if "reqErr" in data:
            print(f"API 오류: {data['reqErr']}")
            return False

        return True
    except:
        return False


def build_search_keywords(filters_dict):
    """
    사용자 선택 조건을 기반으로 검색 키워드 조합을 생성하는 함수

    Args:
        filters_dict: 사용자 선택 필터 딕셔너리

    Returns:
        list: 검색할 키워드 리스트 (최대 4개)
    """
    keywords = []

    # 1순위: 연령대
    age_group = filters_dict.get("age_group")
    if age_group and age_group != "선택 안함":
        if "청년" in age_group:
            keywords.append("청년")
        elif "중장년" in age_group:
            keywords.append("중장년")
        elif "시니어" in age_group:
            keywords.append("시니어")

    # 2순위: 업종
    business_type = filters_dict.get("business_type")
    if business_type and business_type != "선택 안함":
        keywords.append(business_type)

    # 3순위: 지역
    region = filters_dict.get("region_sido")
    if region and region != "전국":
        keywords.append(f"소상공인 {region}")

    # 기본 키워드 (아무 조건도 없을 때)
    if not keywords:
        keywords.append("소상공인")

    # 최대 4개로 제한
    return keywords[:4]


def get_dummy_data():
    """
    API 연결 실패 시 테스트용 더미 데이터
    주의: API 키가 유효하지 않아 테스트 데이터를 표시합니다.

    Returns:
        list: 더미 지원사업 리스트
    """
    # 기업마당 검색 페이지 기본 URL
    search_url = "https://www.bizinfo.go.kr/web/lay1/bbs/S1T122C128/AS/74/list.do"

    return [
        {
            "title": "[테스트] 소상공인 경영안정자금 지원사업",
            "target": "매출 감소 소상공인, 청년 사업자",
            "agency": "중소벤처기업부",
            "category": "금융",
            "start_date": "2026-01-15",
            "end_date": "2026-02-28",
            "link": f"{search_url}?srchPblancNm=경영안정자금",
            "description": "[테스트 데이터] API 키를 설정하면 실제 지원사업이 표시됩니다."
        },
        {
            "title": "[테스트] 청년 소상공인 창업지원 프로그램",
            "target": "만 39세 이하 청년 예비창업자",
            "agency": "소상공인시장진흥공단",
            "category": "창업",
            "start_date": "2026-02-01",
            "end_date": "2026-03-15",
            "link": f"{search_url}?srchPblancNm=청년창업",
            "description": "[테스트 데이터] API 키를 설정하면 실제 지원사업이 표시됩니다."
        },
        {
            "title": "[테스트] 소상공인 디지털 전환 지원사업",
            "target": "전국 소상공인",
            "agency": "중소벤처기업부",
            "category": "기술",
            "start_date": "2026-02-10",
            "end_date": "2026-04-30",
            "link": f"{search_url}?srchPblancNm=디지털",
            "description": "[테스트 데이터] API 키를 설정하면 실제 지원사업이 표시됩니다."
        },
        {
            "title": "[테스트] 시니어 창업 아카데미",
            "target": "만 60세 이상 시니어 예비창업자",
            "agency": "소상공인시장진흥공단",
            "category": "창업",
            "start_date": "2026-03-01",
            "end_date": "2026-05-31",
            "link": f"{search_url}?srchPblancNm=시니어",
            "description": "[테스트 데이터] API 키를 설정하면 실제 지원사업이 표시됩니다."
        }
    ]
