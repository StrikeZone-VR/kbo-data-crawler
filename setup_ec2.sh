#!/bin/bash
# EC2에서 KBO 크롤러를 설정하고 실행하는 스크립트이다.
# 이 스크립트는 다음 작업을 수행힘:
# 1. 시스템 패키지 설치: Python, unzip, wget, cron 등 필수 패키지를 설치
# 2. Git 설치: 프로젝트 클론을 위한 Git 설치
# 3. Python 패키지 설치: requirements.txt에 정의된 Python 라이브러리를 설치
# 4. Chrome 설치: 최신 버전의 Google Chrome을 설치
# 5. ChromeDriver 설치: Chrome 버전에 맞는 ChromeDriver를 다운로드하고 설치
# 6. 환경 변수 설정: .env 파일을 생성하여 데이터베이스 및 크롬 드라이버 경로를 설정
# 7. 크론잡 설정: 매일 자정에 main.py를 실행하도록 크론잡을 설정

# 1. 시스템 패키지 설치
echo "시스템 패키지 설치 중..."
apt-get update
apt-get install -y python3-pip unzip wget cron

# 2. Git 설치
echo "Git 설치 중..."
if ! command -v git &> /dev/null
then
    apt-get install -y git
else
    echo "Git이 이미 설치되어 있습니다."
fi

# 3. Python 패키지 설치
echo "Python 패키지 설치 중..."
pip3 install --upgrade pip
pip3 install -r requirements.txt

# 4. Chrome 설치
echo "Chrome 설치 중..."
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
sudo apt --fix-broken install -y

# 5. ChromeDriver 설치
echo "ChromeDriver 설치 중..."
CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d. -f1)
wget -q "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}" -O chromedriver_version.txt
CHROMEDRIVER_VERSION=$(cat chromedriver_version.txt)
wget -q "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" -O chromedriver_linux64.zip
unzip -q chromedriver_linux64.zip -d /usr/local/bin/
chmod +x /usr/local/bin/chromedriver
rm chromedriver_linux64.zip chromedriver_version.txt

# 6. .env 파일 설정
echo "환경 변수 파일 설정 중..."
cat > .env << EOF
CHROMEDRIVER_PATH=/usr/local/bin/chromedriver
HEADLESS=True

# AWS RDS 설정 - 아래 값들을 실제 RDS 정보로 변경할 것
DB_HOST=your-rds-endpoint.rds.amazonaws.com
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your-secure-password
DB_NAME=StrikeZone_VR
EOF

# 7. 크론잡 설정 (매일 자정에 실행)
echo "크론잡 설정 중..."
CRON_JOB="0 0 * * * cd $(pwd) && python3 main.py >> $(pwd)/crawler.log 2>&1"
(crontab -l 2>/dev/null || echo "") | grep -v "main.py" | { cat; echo "$CRON_JOB"; } | crontab -

echo "설치 완료! 크론잡이 설정되었음"
echo "수동으로 실행하려면: python3 main.py"
echo "로그 파일: $(pwd)/crawler.log"
