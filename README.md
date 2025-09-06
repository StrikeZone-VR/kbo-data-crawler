# KBO 데이터 크롤러

KBO 공식 홈페이지에서 타자, 투수, 팀 순위 데이터를 자동으로 수집하여 PostgreSQL 데이터베이스에 저장하는 웹 크롤링 프로젝트이다.

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://python.org)
[![Selenium](https://img.shields.io/badge/Selenium-4.11+-green.svg)](https://selenium.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13.0+-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-orange.svg)](#license)

## 📊 주요 기능

- **⚾ 종합 데이터 수집**: 타자, 투수, 팀 순위를 모두 수집
- **💾 자동 DB 저장**: PostgreSQL 데이터베이스에 자동 저장 (UPSERT 로직)
- **📈 증분 업데이트**: 데이터가 변경된 경우에만 업데이트
- **🛡️ 크롤링 보안 준수**: robots.txt 준수 및 요청 간 적절한 지연 시간 적용
- **💻 AWS EC2 배포 확장**: EC2/RDS 환경에서 쉽게 실행 가능한 설정 스크립트 포함

<br>

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

<br>

## 🏗️ 프로젝트 구조

```
├── main.py         # 메인 실행 파일
├── crawler.py      # 웹 크롤링 모듈
├── db.py           # 데이터베이스 연결 및 저장 모듈
├── .env            # 환경 변수 설정 파일 (gitignore에 포함됨)
├── requirements.txt # 필요한 Python패키지 목록
└── setup_ec2.sh    # EC2 배포용 설정 스크립트
```

<br>

## 🖥️ EC2/RDS 배포 가이드

이 프로젝트는 AWS EC2 인스턴스에서 실행되며, PostgreSQL RDS와 연동하여 크롤링 데이터를 저장한다. EC2에서 크론잡을 통해 매일 자정마다 크롤링 작업을 자동화하고 최신 상태로 유지한다.

### 배포 및 설정 절차

1. **EC2 인스턴스에 레포지토리 클론 및 환경 설정**

```bash
git clone <repository_url>
cd kbo-crawler
chmod +x setup_ec2.sh
sudo ./setup_ec2.sh
```

2. **PostgreSQL RDS 연결 정보 설정**

```bash
# .env 파일 수정
DB_HOST=RDS 엔드포인트
DB_NAME=''
DB_USER=''
DB_PASSWORD=''
DB_PORT=5432
```

3. **크론잡 설정 (자동 실행)**

`setup_ec2.sh` 스크립트는 크론잡을 자동으로 설정한다. 매일 자정에 `main.py`가 실행되어 데이터를 수집하고 데이터베이스를 최신 상태로 유지한다.

```bash
# 크론잡 확인
crontab -l
```

<br>

## ⚠️ 주의 사항

`setup_ec2.sh` 스크립트는 Python과 Git이 사전에 설치되어 있다고 가정한다.  
따라서, EC2 인스턴스에 Python과 Git이 설치되어 있지 않다면, 아래 명령어를 사용하여 수동으로 설치해야 한다:

```bash
# Git 설치
sudo apt-get update
sudo apt-get install -y git

# Python 설치
sudo apt-get install -y python3 python-is-python3
```

설치 후, `setup_ec2.sh` 스크립트를 실행

<br>

## 📋 데이터 스키마

크롤링된 데이터는 다음 세 개의 테이블로 저장된다:

1. **hitters** - 타자 통계
2. **pitchers** - 투수 통계
3. **team_rankings** - 팀 순위 정보

각 테이블은 복합 키(player_name, team, year 또는 team, year)를 사용하여 중복을 방지한다.

<br>

## 📖 부록: Private AWS RDS 연결 구성

본 프로젝트는 AWS 프리티어 환경에서의 비용 효율성을 고려하여 RDS 데이터베이스의 퍼블릭 액세스를 비활성화하는 것을 표준 구성으로 채택하였다.   

이로 인해 외부 호스트에서의 직접적인 데이터베이스 접근이 제한된다.  

로컬 개발 환경(DBeaver, pgAdmin 등)에서 VPC 내의 Private RDS 인스턴스로 안전하게 연결하기 위한 상세한 기술 가이드는 아래의 별도 문서를 참조한다.  

* **[가이드 문서: Private RDS 연결 구성 방법 (SSH 터널링)](./rdsConnection.md)**  


