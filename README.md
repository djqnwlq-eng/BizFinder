# BizFinder - 소상공인 지원사업 매칭 프로그램

소상공인을 위한 맞춤형 정부 지원사업 검색 서비스입니다.

## 기능

- 연령대, 지역, 업종별 지원사업 검색
- 실시간 기업마당 API 연동
- 마감일 기준 D-day 표시

## 설치 방법

```bash
pip install -r requirements.txt
```

## 실행 방법

```bash
streamlit run app.py
```

## API 키 설정

`.env` 파일에 기업마당 API 키를 입력하세요:

```
BIZINFO_API_KEY=발급받은키
```

API 키 발급: https://www.bizinfo.go.kr → API 목록 → 사용신청
