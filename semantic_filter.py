# 시맨틱 필터링 모듈
# TF-IDF 기반 유사도 검색으로 정밀한 지원사업 매칭

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# TF-IDF 벡터라이저 (한국어 단어 단위 분석)
_vectorizer = None


def get_vectorizer():
    """TF-IDF 벡터라이저 (싱글톤 패턴)"""
    global _vectorizer
    if _vectorizer is None:
        _vectorizer = TfidfVectorizer(
            analyzer='char_wb',
            ngram_range=(2, 4),
            max_features=10000
        )
    return _vectorizer


def create_program_text(program):
    """지원사업 정보를 하나의 텍스트로 결합"""
    parts = [
        program.get("title", ""),
        program.get("description", ""),
        program.get("target", ""),
        program.get("category", ""),
        program.get("agency", "")
    ]
    return " ".join(filter(None, parts))


def extract_keywords(user_description):
    """사용자 설명에서 핵심 키워드 추출"""
    # 불용어 (검색에 의미 없는 단어)
    stopwords = {"저는", "저", "나는", "나", "있는", "하는", "있어요", "합니다", "해요",
                 "싶어요", "싶습니다", "있습니다", "입니다", "에서", "으로", "이고",
                 "하고", "그리고", "또한", "위해", "통해", "대한", "관한", "에게",
                 "지원사업", "지원", "사업", "소상공인"}

    # 단어 분리 및 필터링
    words = user_description.replace(",", " ").replace(".", " ").split()
    keywords = []
    for word in words:
        word = word.strip()
        if len(word) >= 2 and word not in stopwords:
            keywords.append(word)

    return keywords


def check_keyword_match(keywords, title, description, target=""):
    """제목이나 내용에 키워드가 포함되어 있는지 확인"""
    title_lower = (title or "").lower()
    desc_lower = (description or "").lower()
    target_lower = (target or "").lower()

    # 전체 텍스트 (제목 + 내용 + 지원대상)
    full_text = f"{title_lower} {desc_lower} {target_lower}"

    matched = []
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in full_text:
            matched.append(kw)

    return matched


# 지역 키워드 목록 (우선순위 판별용)
REGION_KEYWORDS = {
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
    "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
    "전라북도", "전라남도", "경상북도", "경상남도", "충청북도", "충청남도",
    "강원도", "경기도", "제주도", "제주특별자치도"
}


def is_region_keyword(keyword):
    """키워드가 지역 관련인지 확인"""
    return keyword in REGION_KEYWORDS


def check_region_match(region_keyword, title, description, target):
    """지역 매칭 여부 확인 (전국 포함)"""
    full_text = f"{title or ''} {description or ''} {target or ''}".lower()
    region_lower = region_keyword.lower()

    # 해당 지역이 포함되어 있거나, "전국" 대상인 경우 매칭
    if region_lower in full_text:
        return True
    if "전국" in full_text:
        return True

    return False


def filter_by_similarity(user_description, programs, top_n=30, min_score=0.2, match_all=False):
    """
    TF-IDF 유사도 기반으로 지원사업 필터링
    (키워드 정확 매칭 우선)

    Args:
        user_description: 사용자가 입력한 자연어 설명
        programs: 지원사업 리스트
        top_n: 반환할 최대 개수 (기본 30개, None이면 제한 없음)
        min_score: 최소 유사도 점수 (0~1)
        match_all: True면 모든 키워드가 매칭되어야 함 (AND 로직)

    Returns:
        list: 유사도 순으로 정렬된 지원사업 리스트 (score 포함)
    """
    if not programs or not user_description:
        if top_n:
            return programs[:top_n] if programs else []
        return programs if programs else []

    # 사용자 입력에서 키워드 추출
    keywords = extract_keywords(user_description)

    # 지원사업 텍스트 생성
    program_texts = [create_program_text(p) for p in programs]

    # TF-IDF 유사도 계산
    vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), max_features=10000)
    all_texts = [user_description] + program_texts
    tfidf_matrix = vectorizer.fit_transform(all_texts)
    similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]

    # 유사도 점수와 키워드 매칭 정보 추가
    exact_match_programs = []  # 키워드가 정확히 포함된 결과
    similar_programs = []       # 의미상 유사한 결과

    for i, (program, score) in enumerate(zip(programs, similarities)):
        program_copy = program.copy()
        program_copy["similarity_score"] = float(score)

        # 키워드 매칭 확인 (제목, 내용, 지원대상 모두 검색)
        matched_keywords = check_keyword_match(
            keywords,
            program.get("title", ""),
            program.get("description", ""),
            program.get("target", "")
        )

        if match_all:
            # 매칭 개수순 정렬 모드: 하나라도 매칭되면 포함, 많이 매칭된 순으로 정렬
            if matched_keywords:
                # 지역 키워드 확인
                region_keywords_in_search = [kw for kw in keywords if is_region_keyword(kw)]
                region_matched = False

                # 지역 키워드가 있으면 지역 매칭 체크
                if region_keywords_in_search:
                    for region_kw in region_keywords_in_search:
                        if check_region_match(
                            region_kw,
                            program.get("title", ""),
                            program.get("description", ""),
                            program.get("target", "")
                        ):
                            region_matched = True
                            break
                else:
                    # 지역 키워드가 없으면 지역 매칭 안 따짐
                    region_matched = True

                # 지역이 매칭되지 않으면 제외 (다른 지역 지원사업은 의미 없음)
                if not region_matched:
                    continue

                # 매칭 개수에 비례한 가산점 (최대 0.5점)
                bonus = min(len(matched_keywords) * 0.1, 0.5)
                program_copy["similarity_score"] = min(float(score) + bonus, 1.0)
                program_copy["matched_keywords"] = matched_keywords
                program_copy["matched_count"] = len(matched_keywords)
                program_copy["total_keywords"] = len(keywords)
                program_copy["is_exact_match"] = len(matched_keywords) == len(keywords)  # 전체 매칭 여부
                program_copy["region_matched"] = region_matched
                exact_match_programs.append(program_copy)
            # 키워드 매칭이 하나도 없으면 제외 (관련 없는 결과 필터링)
        else:
            # OR 로직: 하나라도 매칭되면 OK (기존 로직)
            if matched_keywords:
                # 키워드 정확 매칭: 가산점 부여 (최대 0.3점)
                bonus = min(len(matched_keywords) * 0.1, 0.3)
                program_copy["similarity_score"] = min(float(score) + bonus, 1.0)
                program_copy["matched_keywords"] = matched_keywords
                program_copy["matched_count"] = len(matched_keywords)
                program_copy["is_exact_match"] = True
                exact_match_programs.append(program_copy)
            elif score >= min_score:
                program_copy["is_exact_match"] = False
                program_copy["matched_count"] = 0
                similar_programs.append(program_copy)

    # 정확 매칭 결과를 매칭 개수 > 유사도 순으로 정렬
    exact_match_programs.sort(key=lambda x: (-x.get("matched_count", 0), -x["similarity_score"]))

    # 유사 결과도 유사도 높은 순으로 정렬
    similar_programs.sort(key=lambda x: x["similarity_score"], reverse=True)

    # 정확 매칭 결과를 우선 배치
    result = exact_match_programs + similar_programs

    if top_n:
        return result[:top_n]
    return result


def get_relevance_explanation(user_description, program):
    """
    프로그램이 사용자에게 왜 관련있는지 간단한 설명 생성
    (LLM 없이 키워드 매칭 기반)
    """
    user_words = set(user_description.lower().split())
    program_text = create_program_text(program).lower()

    matched_keywords = []
    important_keywords = ["자금", "지원", "창업", "마케팅", "온라인", "디지털",
                         "교육", "컨설팅", "수출", "기술", "인력", "청년", "중소기업"]

    for keyword in important_keywords:
        if keyword in user_description and keyword in program_text:
            matched_keywords.append(keyword)

    if matched_keywords:
        return f"매칭: {', '.join(matched_keywords[:3])}"
    return ""
