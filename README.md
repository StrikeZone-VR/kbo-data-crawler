# KBO 타자 기록 크롤러

KBO 공식 홈페이지에서 2025시즌 타자 기록을 자동으로 수집하는 Python 크롤링 도구입니다.


[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://python.org)
[![Selenium](https://img.shields.io/badge/Selenium-4.11+-green.svg)](https://selenium.dev)
[![License](https://img.shields.io/badge/License-Educational-orange.svg)](#license)


## 📊 주요 기능

- **🎯 2025시즌 현재 데이터**: 최신 KBO 리그 타자 기록 수집
- **⚾ 전체 10개 팀**: LG, 한화, 롯데, SSG, KIA, KT, NC, 삼성, 두산, 키움
- **🛡️ robots.txt 준수**: 웹사이트 크롤링 정책을 자동으로 확인하고 준수
- **⏰ 서버 부하 방지**: 요청 간 2초 대기로 안전한 크롤링
- **📈 데이터 분석**: 홈런왕 순위 등 간단한 분석 도구 포함


## ⚠️ 사용 시 주의사항

- 이 도구는 교육/연구 목적으로만 사용해야 합니다
- KBO 공식 홈페이지의 robots.txt를 준수합니다
- 과도한 요청을 방지하기 위해 적절한 지연시간을 설정했습니다
- 상업적 사용을 금지합니다

## 🚀 사용법

```bash
pip install -r requirements.txt
python main.py        # 크롤링 실행
python homerun.py     # 홈런 분석
```

## 📊 수집 데이터

2020-2025년 KBO 타자 기본 기록 (타율, 홈런, 타점 등)

## 📄 라이선스

개인 학습/연구 목적으로만 사용 가능합니다.
