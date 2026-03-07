# Gemini API 클라이언트 모듈
# 자유 설명 모드에서 키워드 확장 + 최종 추천 담당

import os
import json
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from google import genai


def get_gemini_key():
    """Gemini API 키를 가져오는 함수"""
    # 1순위: 사용자가 웹 화면에서 입력한 키 (세션)
    session_key = st.session_state.get("gemini_api_key", "")
    if session_key and session_key.strip():
        return session_key.strip()

    # 2순위: Streamlit secrets (Cloud 배포용)
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        if api_key and api_key != "여기에키입력":
            return api_key
    except (KeyError, FileNotFoundError):
        pass

    # 3순위: 환경변수 (.env 로컬 개발용)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "여기에키입력":
        return None
    return api_key


def get_gemini_status():
    """Gemini API 연결 상태 확인"""
    return get_gemini_key() is not None


def _get_client():
    """Gemini 클라이언트 인스턴스 반환"""
    api_key = get_gemini_key()
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def _parse_json_response(text):
    """Gemini 응답에서 JSON을 추출하여 파싱"""
    text = text.strip()
    # 마크다운 코드블록 제거
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return json.loads(text)


def extract_keywords(user_description):
    """
    사용자 자유 설명에서 검색 키워드를 확장 추출

    Args:
        user_description: 사용자가 입력한 상황 설명

    Returns:
        list: 검색 키워드 리스트 (5~8개), 실패 시 None
    """
    client = _get_client()
    if not client:
        return None

    prompt = f"""당신은 소상공인 지원사업 검색 전문가입니다.
사용자의 상황 설명을 읽고, 기업마당(bizinfo.go.kr)에서 검색할 키워드를 추출해주세요.

핵심 규칙:
1. 사용자가 언급한 모든 니즈를 빠짐없이 키워드로 변환하세요. 하나도 누락하면 안 됩니다.
2. 각 니즈마다 반드시 2개 이상의 키워드를 생성하세요:
   - 사용자가 쓴 원래 표현 그대로 (예: "상세페이지")
   - 정부 지원사업에서 쓰는 공식 표현 (예: "콘텐츠 제작 지원", "온라인 판로")
3. 동의어/유사어를 반드시 포함하세요 (예: 빵집 → 베이커리, 외식업)
4. 지역이 언급되면 "소상공인 [지역]" 형태로 포함하세요
5. 최소 5개, 최대 15개의 키워드를 생성하세요
6. 반드시 JSON 배열 형식으로만 응답하세요 (다른 텍스트 없이)

사용자 설명: "{user_description}"

응답 예시 (상세페이지+자금+채용이 니즈인 경우):
["상세페이지 제작", "콘텐츠 제작 지원", "온라인 판로 지원", "자금지원", "소상공인 대출", "정책자금", "고용지원", "채용 지원금", "일자리 창출"]"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        keywords = _parse_json_response(response.text)
        if isinstance(keywords, list) and len(keywords) >= 1:
            return keywords[:15]
    except Exception as e:
        print(f"Gemini 키워드 추출 오류: {e}")

    return None


def recommend_programs(user_description, programs):
    """
    사용자 상황과 후보 지원사업을 비교하여 최종 추천

    Args:
        user_description: 사용자 상황 설명
        programs: 후보 지원사업 리스트 (dict)

    Returns:
        list: 추천 결과 리스트 (gemini_reason, gemini_relevance 포함), 실패 시 None
    """
    client = _get_client()
    if not client:
        return None

    # 후보 사업 목록을 텍스트로 변환 (토큰 절약)
    programs_text = ""
    for i, p in enumerate(programs):
        title = p.get("title", "")
        target = p.get("target", "")
        description = p.get("description", "")
        category = p.get("category", "")
        if len(description) > 200:
            description = description[:200] + "..."
        programs_text += f"\n[{i}] 제목: {title}\n    분야: {category}\n    대상: {target}\n    내용: {description}\n"

    prompt = f"""당신은 소상공인 지원사업 매칭 전문가입니다.
사용자의 상황과 후보 지원사업 목록을 비교하여, 가장 적합한 사업을 추천해주세요.

사용자 상황:
"{user_description}"

후보 지원사업 목록:
{programs_text}

규칙:
1. 사용자 상황에 맞는 사업만 추천하세요 (관련 없는 것은 제외)
2. 적합도가 높은 순서대로 정렬하세요
3. 각 사업마다 "왜 이 사람에게 맞는지" 추천 이유를 1~2문장으로 작성하세요
4. 추천 이유는 사용자의 구체적 상황과 연결지어 설명하세요
5. 반드시 아래 JSON 배열 형식으로만 응답하세요 (다른 텍스트 없이)

응답 형식:
[
  {{"index": 0, "reason": "추천 이유", "relevance": "high"}},
  {{"index": 2, "reason": "추천 이유", "relevance": "medium"}}
]

relevance 값: "high" (강력 추천), "medium" (관련 있음), "low" (참고용)"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        recommendations = _parse_json_response(response.text)
        if not isinstance(recommendations, list):
            return None

        # 추천 결과를 원본 프로그램 데이터와 병합
        result = []
        for rec in recommendations:
            idx = rec.get("index")
            if idx is not None and 0 <= idx < len(programs):
                program = programs[idx].copy()
                program["gemini_reason"] = rec.get("reason", "")
                program["gemini_relevance"] = rec.get("relevance", "medium")
                result.append(program)

        return result if result else None

    except Exception as e:
        print(f"Gemini 추천 오류: {e}")

    return None
