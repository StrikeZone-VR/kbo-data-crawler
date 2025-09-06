#!/bin/bash
# EC2에서 KBO 크롤러를 설정하고 실행하는 스크립트 (개선된 버전)
#
# 이 스크립트는 다음 작업을 수행합니다:
# 1. 시스템 패키지 설치: Python 가상환경, unzip, wget, cron 등 필수 패키지를 설치합니다.
# 2. Python 가상환경 설정 및 패키지 설치: requirements.txt에 정의된 Python 라이브러리를 안전한 가상환경 내에 설치합니다.
# 3. Chrome 설치: 의존성 문제를 자동으로 해결하며 최신 버전의 Google Chrome을 설치합니다.
# 4. ChromeDriver 설치: 설치된 Chrome 버전에 정확히 맞는 ChromeDriver를 안정적인 방식으로 다운로드하고 설치합니다.
# 5. 환경 변수 설정: .env 파일을 생성하여 데이터베이스 및 크롬 드라이버 경로를 설정합니다.
# 6. 크론잡 설정: 매일 자정에 가상환경의 Python을 사용하여 main.py를 실행하도록 크론잡을 설정합니다.

# -- 스크립트 실행 중 오류가 발생하면 즉시 중단 --
set -e

# 1. 시스템 패키지 설치
echo "✅ 1. 시스템 패키지 설치 중..."
sudo apt-get update
# python3-venv는 가상환경 생성을 위해 필수입니다.
sudo apt-get install -y python3-pip python3-venv unzip wget cron jq

# 2. Python 가상환경 설정 및 패키지 설치
echo "✅ 2. Python 가상환경 설정 및 패키지 설치 중..."
# 기존 가상환경이 있다면 삭제하여 깨끗한 상태에서 시작
rm -rf venv
# 가상환경 생성
python3 -m venv venv
# 가상환경 활성화
source venv/bin/activate
# 가상환경 내의 pip로 패키지 설치 (sudo 불필요)
pip install --upgrade pip
pip install -r requirements.txt
# 작업 완료 후 가상환경 비활성화
deactivate
echo "   ... Python 패키지 설치 완료!"

# 3. Chrome 설치
echo "✅ 3. Chrome 설치 중..."
wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
# dpkg로 설치 시도 후, 의존성 문제가 발생하면 --fix-broken install로 자동 해결
sudo dpkg -i google-chrome-stable_current_amd64.deb || sudo apt-get -f install -y
rm google-chrome-stable_current_amd64.deb
echo "   ... Chrome 설치 완료!"

# 4. ChromeDriver 설치 (더 안정적인 최신 방식으로 변경)
echo "✅ 4. ChromeDriver 설치 중..."
# 설치된 크롬의 전체 버전을 가져옵니다 (예: 128.0.6613.84)
CHROME_VERSION=$(google-chrome --version | grep -oP '(\d+\.\d+\.\d+\.\d+)')
# 구글의 공식 JSON 엔드포인트에서 내 크롬 버전에 맞는 드라이버 다운로드 URL을 찾습니다.
CHROMEDRIVER_URL=$(wget -qO- "https://googlechromelabs.github.io/chrome-for-testing/latest-stable-versions-with-downloads.json" | jq -r ".versions[] | select(.version==\"$CHROME_VERSION\") | .downloads.chromedriver[] | select(.platform==\"linux64\") | .url")

if [ -z "$CHROMEDRIVER_URL" ]; then
    echo "❌ 현재 크롬 버전에 맞는 ChromeDriver를 찾을 수 없습니다. 스크립트를 확인해주세요."
    exit 1
fi

mkdir -p drivers
wget -q "$CHROMEDRIVER_URL" -O drivers/chromedriver.zip
# 압축 해제 후 chromedriver 실행 파일만 drivers 폴더로 이동
unzip -q drivers/chromedriver.zip -d drivers/
mv drivers/chromedriver-linux64/chromedriver drivers/
chmod +x drivers/chromedriver
# 불필요한 파일 및 폴더 삭제
rm drivers/chromedriver.zip
rm -rf drivers/chromedriver-linux64
echo "   ... ChromeDriver 설치 완료!"

# 5. .env 파일 설정
echo "✅ 5. 환경 변수 파일 설정 중..."
# 프로젝트 디렉토리의 절대 경로를 가져와 .env 파일에 기록
PROJECT_DIR=$(pwd)
cat > .env << EOF
CHROMEDRIVER_PATH=$PROJECT_DIR/drivers/chromedriver
HEADLESS=True

# AWS RDS 설정 - 아래 값들을 실제 RDS 정보로 변경할 것
PGHOST=your-rds-endpoint.rds.amazonaws.com
PGPORT=5432
PGUSER=postgres
PGPASSWORD=your-secure-password
PGDATABASE=StrikeZone_VR
EOF
echo "   ... .env 파일 생성 완료!"

# 6. 크론잡 설정 (가상환경을 사용하도록 수정)
echo "✅ 6. 크론잡 설정 중..."
# 프로젝트 디렉토리 및 실행 파일의 절대 경로 지정
PROJECT_DIR=$(pwd)
PYTHON_EXEC="$PROJECT_DIR/venv/bin/python"
MAIN_PY_PATH="$PROJECT_DIR/main.py"
LOG_FILE="$PROJECT_DIR/crawler.log"

# 기존에 등록된 main.py 크론잡이 있다면 삭제
(crontab -l 2>/dev/null | grep -v "$MAIN_PY_PATH" || true) | crontab -

# 새 크론잡 추가 (가상환경의 파이썬을 사용)
CRON_JOB="0 0 * * * $PYTHON_EXEC $MAIN_PY_PATH >> $LOG_FILE 2>&1"
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
echo "   ... 크론잡 설정 완료!"

echo -e "\n🎉 모든 설정이 성공적으로 완료되었습니다!"
echo "   - 수동으로 실행하려면: source venv/bin/activate && python main.py"
echo "   - 로그 파일 위치: $LOG_FILE"