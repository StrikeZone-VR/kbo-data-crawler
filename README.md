# KBO 데이터 크롤러

KBO 공식 홈페이지에서 타자, 투수, 팀 순위 데이터를 자동으로 수집하여 PostgreSQL 데이터베이스에 저장하는 크롤링 도구이다.

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://python.org)
[![Selenium](https://img.shields.io/badge/Selenium-4.11+-green.svg)](https://selenium.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13.0+-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-orange.svg)](#license)

## 📊 주요 기능

- **⚾ 종합 데이터 수집**: 타자, 투수, 팀 순위를 모두 수집
- **💾 자동 DB 저장**: PostgreSQL 데이터베이스에 자동 저장 (UPSERT 로직)
- **� 증분 업데이트**: 데이터가 변경된 경우에만 업데이트
- **🛡️ 크롤링 보안 준수**: robots.txt 준수 및 요청 간 적절한 지연 시간 적용
- **💻 AWS ec2 배포 확장**: EC2/RDS 환경에서 쉽게 실행 가능한 설정 스크립트 포함

## 🚀 빠른 시작

### 환경 설정

```bash
# 필요한 패키지 설치
pip install -r requirements.txt

# .env 파일 설정 (예시)
DB_HOST=localhost
DB_NAME=StrikeZone_VR
DB_USER=postgres
DB_PASSWORD=DB_password
DB_PORT=5432
```

### 실행 방법

```bash
# 데이터베이스 연결 테스트
python test_db_conn.py

# 전체 크롤링 파이프라인 실행
python main.py
```

## 🏗️ 프로젝트 구조

```
├── main.py         # 메인 실행 파일
├── crawler.py      # 웹 크롤링 모듈
├── db.py           # 데이터베이스 연결 및 저장 모듈
├── .env            # 환경 변수 설정 파일 (gitignore에 포함됨)
├── requirements.txt # 필요한 Python패키지 목록
└── setup_ec2.sh    # EC2 배포용 설정 스크립트
```

## 🖥️ EC2/RDS 배포 가이드

1. EC2 인스턴스에 레포지토리 clone 및 환경 설정

```bash
git clone <repository_url>
cd kbo-crawler
chmod +x setup_ec2.sh
sudo ./setup_ec2.sh
```

2. PostgreSQL RDS 연결 정보 설정

```bash
# .env 파일 수정
DB_HOST=your-rds-endpoint.rds.amazonaws.com
DB_NAME=StrikeZone_VR
DB_USER=postgres
DB_PASSWORD=DB_password
DB_PORT=5432
```

3. 크론잡 설정 (매일 자정에 주기적으로 실행)

```bash
crontab -e
# 아래 내용 추가
0 0 * * * cd /path/to/kbo-crawler && /usr/bin/python3 main.py >> /path/to/kbo-crawler/cron.log 2>&1
```

## 📋 데이터 스키마

크롤링된 데이터는 다음 세 개의 테이블로 저장:

1. **hitters** - 타자 통계
2. **pitchers** - 투수 통계
3. **team_rankings** - 팀 순위 정보

각 테이블은 복합 키(player_name, team, year 또는 team, year)를 사용하여 중복 방지
