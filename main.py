import urllib.robotparser
import urllib.parse
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import pandas as pd
from selenium.webdriver.support.ui import Select, WebDriverWait
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options

# 🤖 robots.txt 확인 및 강제 적용
def check_robots_txt(url):
    """robots.txt를 확인하여 크롤링 허용 여부를 체크"""
    try:
        # robots.txt 파서 생성
        rp = urllib.robotparser.RobotFileParser()
        
        # 도메인에서 robots.txt URL 생성
        parsed_url = urllib.parse.urlparse(url)
        robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
        
        print(f"🔍 robots.txt 확인 중: {robots_url}")
        
        # robots.txt 읽기
        rp.set_url(robots_url)
        rp.read()
        
        # 크롤링 허용 여부 확인 (* = 모든 User-agent)
        can_fetch = rp.can_fetch("*", url)
        
        if can_fetch:
            print(f"✅ robots.txt 허용: {url}")
            return True
        else:
            print(f"❌ robots.txt 금지: {url}")
            print("🚫 이 URL은 크롤링이 금지되어 있습니다.")
            return False
            
    except Exception as e:
        print(f"⚠️  robots.txt 확인 실패: {e}")
        print("⚠️  수동으로 robots.txt를 확인해 주세요.")
        return False

# 🛡️ 크롤링 에티켓 설정
DELAY_BETWEEN_REQUESTS = 2.0
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

print("🤖 KBO 크롤러 시작 - 교육/연구 목적 (현재 시즌)")
print("=" * 50)

# 크롤링 대상 URL
target_url = 'https://www.koreabaseball.com/Record/Player/HitterBasic/Basic1.aspx?sort=HRA_RT'

# 🚨 robots.txt 강제 확인
if not check_robots_txt(target_url):
    print("\n🛑 robots.txt에 의해 크롤링이 중단됩니다.")
    print("📖 https://www.koreabaseball.com/robots.txt 를 확인해 주세요.")
    exit(1)  # 프로그램 강제 종료

print("⏰ 서버 부하 방지를 위해 충분한 지연시간을 설정합니다...")

# 크롬 옵션 설정
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument(f"--user-agent={USER_AGENT}")

# 크롬드라이버 실행
driver = webdriver.Chrome(options=chrome_options)
driver.implicitly_wait(10)

wait = WebDriverWait(driver, 10)

# robots.txt 확인 통과 후에만 접속
driver.get(target_url)

# 🛡️ 안전한 대기 함수
def safe_sleep():
    """서버 부하 방지를 위한 적절한 대기"""
    time.sleep(DELAY_BETWEEN_REQUESTS)
    print("⏳ 대기 중... (서버 부하 방지)")

def create_table(driver):
    kbo_page = driver.page_source
    soup = BeautifulSoup(kbo_page, 'html.parser')
    table = soup.select_one('#cphContents_cphContents_cphContents_udpContent > div.record_result > table')
    table = pd.read_html(str(table), flavor='html5lib')[0]
    return table

def team_list(driver):
    safe_sleep()
    combobox = driver.find_element(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_ddlTeam_ddlTeam')
    safe_sleep()
    options = combobox.find_elements(By.TAG_NAME, 'option')[1:]
    teams = [option.text for option in options]
    return teams

def page_click(driver):
    df1 = create_table(driver)
    page_count = len(driver.find_elements(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_udpContent > div.record_result > div > a'))
    if page_count > 1:
        driver.find_element(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_ucPager_btnNo2').click()
        df2 = create_table(driver)
        safe_sleep()
        driver.find_element(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_ucPager_btnNo1').click()
        df = pd.concat([df1, df2])
    else:
        return df1
    return df

# 메인 크롤링 로직 - 현재 시즌(2025)만 수집
dfs = []
current_season = "2025"  # 🎯 현재 시즌만!

print(f"📅 수집 대상: {current_season} 시즌 (현재 시즌)")

print(f"\n🗓️  시즌 {current_season} 수집 중...")
safe_sleep()

# 시즌 선택
season_combo = driver.find_element(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_ddlSeason_ddlSeason')
season_combo = Select(season_combo)
season_combo.select_by_value(current_season)
teams = team_list(driver)

print(f"⚾ 총 {len(teams)}개 팀 발견: {', '.join(teams)}")

for team_idx, team in enumerate(teams, 1):
    print(f"   🏟️  {team} 팀 수집 중... ({team_idx}/{len(teams)})")
    safe_sleep()
    
    combobox = driver.find_element(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_ddlTeam_ddlTeam')
    team_combo = Select(combobox)
    team_combo.select_by_visible_text(team)
    safe_sleep()
    
    df = page_click(driver)
    df['year'] = current_season
    dfs.append(df)

# 결과 처리
if dfs:
    result = pd.concat(dfs, ignore_index=True)
    print(f"\n✅ 총 {len(result)}개 선수 기록 수집 완료! ({current_season}시즌)")
    
    try:
        print("\n📊 수집된 데이터 미리보기:")
        print(result.head(10).to_string(index=False))
    except Exception:
        print(result.head(10))
        
    filename = f'kbo_hitters_{current_season}.csv'
    result.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f'\n💾 파일 저장 완료: {filename}')
    
else:
    print('❌ 데이터가 수집되지 않았습니다.')

print("\n🏁 크롤링 완료! 감사합니다.")
driver.quit()