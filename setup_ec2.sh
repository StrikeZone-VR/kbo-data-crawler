#!/bin/bash
# EC2에서 KBO 크롤러 설정 및 실행하는 스크립트
# 사용법: sudo bash setup_ec2.sh

# 1. 필요한 패키지 설치
echo "시스템 패키지 설치 중..."
apt-get update
apt-get install -y python3-pip python3-venv unzip wget cron

# 2. Python 가상환경 설정
echo "Python 가상환경 설정 중..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. Chrome 및 ChromeDriver 설치
echo "Chrome 및 ChromeDriver 설치 중..."
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list
apt-get update
apt-get install -y google-chrome-stable

# ChromeDriver 버전 확인 및 설치
CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d. -f1)
mkdir -p drivers
wget -q "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}" -O drivers/chromedriver_version.txt
CHROMEDRIVER_VERSION=$(cat drivers/chromedriver_version.txt)
wget -q "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" -O drivers/chromedriver.zip
unzip -q drivers/chromedriver.zip -d drivers/
chmod +x drivers/chromedriver
rm drivers/chromedriver.zip drivers/chromedriver_version.txt

# 4. .env 파일 설정
echo "환경 변수 파일 설정 중..."
cat > .env << EOF
CHROMEDRIVER_PATH=$(pwd)/drivers/chromedriver
HEADLESS=True

# AWS RDS 설정 - 아래 값들을 실제 RDS 정보로 변경할 것
DB_HOST=your-rds-endpoint.rds.amazonaws.com
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your-secure-password
DB_NAME=StrikeZone_VR
EOF

# 5. 크론잡 설정 (매일 자정에 실행)
echo "크론잡 설정 중..."
CRON_JOB="0 0 * * * cd $(pwd) && source venv/bin/activate && python main.py >> $(pwd)/crawler.log 2>&1"
(crontab -l 2>/dev/null || echo "") | grep -v "main.py" | { cat; echo "$CRON_JOB"; } | crontab -

echo "설치 완료! 크론잡이 설정되었음"
echo "수동으로 실행하려면: source venv/bin/activate && python main.py"
echo "로그 파일: $(pwd)/crawler.log"
