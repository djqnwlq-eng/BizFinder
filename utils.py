# 유틸리티 함수 모듈
# D-day 계산, 상태 뱃지, 날짜 포맷 등

import re
from datetime import datetime


def strip_html_tags(text):
    """HTML 태그 제거"""
    if not text:
        return ""
    # HTML 태그 제거
    clean = re.sub(r'<[^>]+>', ' ', str(text))
    # 연속 공백 정리
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()


def calculate_dday(end_date_str):
    """
    마감일까지 남은 일수 계산

    Args:
        end_date_str: 마감일 문자열

    Returns:
        int: 남은 일수 (양수: 남은 일수, 음수: 지난 일수, None: 파싱 실패)
    """
    end_date = parse_date(end_date_str)
    if not end_date:
        return None

    today = datetime.now().date()
    delta = (end_date - today).days
    return delta


def get_status_badge(start_date_str, end_date_str):
    """
    접수 상태에 따른 뱃지 HTML 반환

    Args:
        start_date_str: 시작일 문자열
        end_date_str: 마감일 문자열

    Returns:
        tuple: (상태 텍스트, 배경색, 텍스트 색)
    """
    today = datetime.now().date()
    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)

    if not end_date:
        return ("📋 확인필요", "#gray", "#fff")

    dday = (end_date - today).days

    # 마감
    if dday < 0:
        return ("🔴 마감", "#ff4b4b", "#fff")

    # 마감 임박 (7일 이내)
    if dday <= 7:
        return ("🟠 마감임박", "#ffa500", "#fff")

    # 접수 예정
    if start_date and start_date > today:
        return ("🟡 접수예정", "#ffd700", "#333")

    # 접수 중
    return ("🟢 접수중", "#00c853", "#fff")


def format_date(date_str):
    """
    날짜 형식을 "2026.01.15" 형태로 통일

    Args:
        date_str: 날짜 문자열

    Returns:
        str: 포맷된 날짜 문자열
    """
    date = parse_date(date_str)
    if not date:
        return date_str or "-"
    return date.strftime("%Y.%m.%d")


def get_dday_text(dday):
    """
    D-day 텍스트 변환

    Args:
        dday: 남은 일수

    Returns:
        tuple: (D-day 텍스트, 색상)
    """
    if dday is None:
        return ("-", "#666")

    if dday < 0:
        return ("마감", "#ff4b4b")
    elif dday == 0:
        return ("D-Day", "#ff4b4b")
    elif dday <= 7:
        return (f"D-{dday}", "#ff4b4b")
    elif dday <= 14:
        return (f"D-{dday}", "#ffa500")
    else:
        return (f"D-{dday}", "#666")


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

    date_str = str(date_str).strip()
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


def get_card_html(program, dday, status_badge, dday_text, dday_color):
    """지원사업 카드 HTML 생성"""
    status_text, status_bg, status_color = status_badge

    title = strip_html_tags(program.get("title", "제목 없음"))
    agency = strip_html_tags(program.get("agency", "-"))
    category = strip_html_tags(program.get("category", "-"))
    start_date = format_date(program.get("start_date", ""))
    end_date = format_date(program.get("end_date", ""))
    target = strip_html_tags(program.get("target", "-"))
    description = strip_html_tags(program.get("description", "-"))
    link = program.get("link", "")
    similarity_score = program.get("similarity_score")
    gemini_reason = program.get("gemini_reason")
    gemini_relevance = program.get("gemini_relevance")

    if len(description) > 150:
        description = description[:150] + "..."

    link_html = ""
    if link:
        link_html = f'<div style="margin-top: 16px; text-align: center;"><a href="{link}" target="_blank" style="display: inline-block; padding: 10px 24px; background: #FF6B35; color: white; text-decoration: none; border-radius: 8px; font-weight: 500;">📄 상세보기</a></div>'

    # Gemini 추천 이유 (있을 경우만)
    gemini_html = ""
    if gemini_reason:
        relevance_styles = {
            "high": ("background: #1976d2", "AI 강력 추천"),
            "medium": ("background: #ff9800", "AI 추천"),
            "low": ("background: #666", "AI 참고"),
        }
        style, label = relevance_styles.get(gemini_relevance, ("background: #666", "AI 추천"))
        gemini_html = f'<div style="margin-top: 12px; padding: 12px; background: #e3f2fd; border-radius: 8px; border-left: 4px solid #1976d2; color: #333; font-size: 13px; line-height: 1.6;"><span style="{style}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; margin-right: 8px;">{label}</span>{gemini_reason}</div>'

    # 유사도 점수 뱃지 (있을 경우만)
    similarity_html = ""
    if similarity_score is not None:
        score_pct = int(similarity_score * 100)
        is_exact_match = program.get("is_exact_match", False)
        matched_keywords = program.get("matched_keywords", [])

        if is_exact_match and matched_keywords:
            # 전체 매칭: 키워드 표시 (파란색)
            total_keywords = program.get("total_keywords", len(matched_keywords))
            matched_count = len(matched_keywords)
            kw_text = ", ".join(matched_keywords[:3])
            if total_keywords > 1:
                similarity_html = f'<span style="background: #1976d2; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 500;">✅ {matched_count}/{total_keywords} 매칭: {kw_text}</span>'
            else:
                similarity_html = f'<span style="background: #1976d2; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 500;">✅ 키워드 매칭: {kw_text}</span>'
        elif matched_keywords:
            # 부분 매칭: 주황색
            total_keywords = program.get("total_keywords", len(matched_keywords))
            matched_count = len(matched_keywords)
            kw_text = ", ".join(matched_keywords[:3])
            similarity_html = f'<span style="background: #ff9800; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 500;">🔸 {matched_count}/{total_keywords} 매칭: {kw_text}</span>'
        else:
            # 유사 결과
            if score_pct >= 70:
                score_color = "#00c853"
            elif score_pct >= 50:
                score_color = "#ffa500"
            else:
                score_color = "#666"
            similarity_html = f'<span style="background: {score_color}; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 500;">🔍 유사도 {score_pct}%</span>'

    card_html = f'''<div style="background: white; border-radius: 12px; padding: 20px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border: 1px solid #eee;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
<div style="display: flex; gap: 8px; align-items: center;">
{similarity_html}
<span style="background: {status_bg}; color: {status_color}; padding: 4px 10px; border-radius: 20px; font-size: 13px; font-weight: 500;">{status_text}</span>
<span style="color: {dday_color}; font-weight: bold; font-size: 14px;">{dday_text}</span>
</div>
<span style="background: #f0f0f0; color: #666; padding: 4px 10px; border-radius: 20px; font-size: 12px;">{category}</span>
</div>
<h3 style="margin: 0 0 12px 0; font-size: 18px; color: #333; line-height: 1.4;">📌 {title}</h3>
<div style="color: #666; font-size: 14px; line-height: 1.8;">
<div>🏛️ <strong>소관기관:</strong> {agency}</div>
<div>📅 <strong>신청기간:</strong> {start_date} ~ {end_date}</div>
<div>👥 <strong>지원대상:</strong> {target}</div>
</div>
<div style="margin-top: 12px; padding: 12px; background: #f8f9fa; border-radius: 8px; color: #555; font-size: 13px; line-height: 1.6;">{description}</div>
{gemini_html}
{link_html}
</div>'''

    return card_html
