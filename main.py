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
        
        print(f"🔍 웹 크롤링 허가 확인: {robots_url}")
        print("   📖 robots.txt 파일을 읽어서 크롤링이 허용되는지 확인하고 있습니다...")
        
        # robots.txt 읽기
        rp.set_url(robots_url)
        rp.read()
        
        # 크롤링 허용 여부 확인 (* = 모든 User-agent)
        can_fetch = rp.can_fetch("*", url)
        
        if can_fetch:
            print(f"✅ 크롤링 허가 확인 완료!")
            print(f"   📄 해당 페이지는 크롤링이 허용됩니다: /Record/ 경로")
            return True
        else:
            print(f"❌ 크롤링 금지 페이지입니다!")
            print(f"   🚫 robots.txt에서 이 URL의 크롤링을 금지하고 있습니다.")
            return False
            
    except Exception as e:
        print(f"⚠️  robots.txt 확인 중 오류 발생: {e}")
        print("   💭 인터넷 연결을 확인하거나 수동으로 robots.txt를 확인해 주세요.")
        return False

# 🛡️ 크롤링 에티켓 설정
DELAY_BETWEEN_REQUESTS = 2.0
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

print("🤖 KBO 타자 기록 크롤러를 시작합니다!")
print("📊 2025년 현재 시즌 모든 팀의 타자 기록을 수집합니다")
print("🎯 교육/연구 목적으로만 사용됩니다")
print("=" * 60)

# 크롤링 대상 URL
target_url = 'https://www.koreabaseball.com/Record/Player/HitterBasic/Basic1.aspx?sort=HRA_RT'

print("\n🚨 1단계: 크롤링 허가 확인")
print("   💡 웹사이트의 robots.txt를 확인해서 크롤링이 허용되는지 검사합니다")

# 🚨 robots.txt 강제 확인
if not check_robots_txt(target_url):
    print("\n🛑 크롤링이 중단됩니다.")
    print("📖 자세한 내용: https://www.koreabaseball.com/robots.txt")
    exit(1)  # 프로그램 강제 종료

print("\n⏰ 2단계: 안전한 크롤링 설정")
print("   🛡️  KBO 서버에 무리가 가지 않도록 요청 간격을 2초로 설정합니다")
print("   🌐 정상적인 웹브라우저로 인식되도록 User-Agent를 설정합니다")

# 크롬 옵션 설정
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument(f"--user-agent={USER_AGENT}")

print("\n🚀 3단계: 크롬 브라우저 실행")
print("   💻 자동화된 크롬 브라우저를 실행합니다...")

# 크롬드라이버 실행
driver = webdriver.Chrome(options=chrome_options)
driver.implicitly_wait(10)

wait = WebDriverWait(driver, 10)

print("   ✅ 크롬 브라우저가 성공적으로 실행되었습니다!")
print("   💡 Chrome DevTools 메시지는 정상적인 브라우저 실행 로그입니다 (무시하셔도 됩니다)")

print(f"\n🌐 4단계: KBO 공식 홈페이지 접속")
print(f"   🔗 접속 중: {target_url}")

# robots.txt 확인 통과 후에만 접속
driver.get(target_url)

print("   ✅ KBO 타자 기록 페이지에 성공적으로 접속했습니다!")

# 🛡️ 안전한 대기 함수
def safe_sleep():
    """서버 부하 방지를 위한 적절한 대기"""
    time.sleep(DELAY_BETWEEN_REQUESTS)
    print("     ⏳ 서버 부하 방지를 위해 2초 대기 중...")

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
        print("     📄 2페이지가 있어서 추가로 수집합니다...")
        driver.find_element(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_ucPager_btnNo2').click()
        df2 = create_table(driver)
        safe_sleep()
        driver.find_element(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_ucPager_btnNo1').click()
        df = pd.concat([df1, df2])
    else:
        df1
    return df

# 메인 크롤링 로직 - 현재 시즌(2025)만 수집
dfs = []
current_season = "2025"  # 🎯 현재 시즌만!

print(f"\n📅 5단계: 데이터 수집 시작")
print(f"   🎯 수집 대상: {current_season}시즌 KBO 전체 팀 타자 기록")

print(f"\n🗓️  {current_season}시즌 데이터 수집을 시작합니다...")
safe_sleep()

# 시즌 선택
season_combo = driver.find_element(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_ddlSeason_ddlSeason')
season_combo = Select(season_combo)
season_combo.select_by_value(current_season)
teams = team_list(driver)

print(f"⚾ 발견된 팀 목록: {len(teams)}개")
print(f"   📋 {', '.join(teams)}")
print(f"\n🔄 각 팀별로 선수 기록을 차례대로 수집합니다...")

for team_idx, team in enumerate(teams, 1):
    print(f"\n   🏟️  [{team_idx:2d}/{len(teams)}] {team} 팀 선수 기록 수집 중...")
    safe_sleep()
    
    combobox = driver.find_element(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_ddlTeam_ddlTeam')
    team_combo = Select(combobox)
    team_combo.select_by_visible_text(team)
    safe_sleep()
    
    df = page_click(driver)
    df['year'] = current_season
    dfs.append(df)
    print(f"     ✅ {team} 팀 {len(df)}명 선수 기록 수집 완료!")

# 결과 처리
print(f"\n📊 6단계: 수집 결과 정리 및 저장")
if dfs:
    result = pd.concat(dfs, ignore_index=True)
    print(f"✅ 데이터 수집 성공!")
    print(f"   📈 총 {len(result)}명의 선수 기록을 수집했습니다 ({current_season}시즌)")
    
    try:
        print(f"\n📋 수집된 데이터 미리보기 (상위 10명):")
        print("=" * 80)
        print(result.head(10).to_string(index=False))
    except Exception:
        print(result.head(10))
        
    filename = f'kbo_hitters_{current_season}.csv'
    result.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"\n💾 파일 저장 완료!")
    print(f"   📁 저장 위치: {filename}")
    print(f"   📊 엑셀에서도 열어볼 수 있습니다!")
    
else:
    print('❌ 오류: 데이터가 수집되지 않았습니다.')
    print('   💭 인터넷 연결이나 KBO 홈페이지 상태를 확인해 주세요.')

print(f"\n🏁 크롤링이 완료되었습니다!")
print(f"   🤖 크롬 브라우저를 자동으로 종료합니다...")
driver.quit()
print(f"   ✅ 모든 작업이 성공적으로 완료되었습니다!")
print(f"   🎉 {current_season}시즌 KBO 타자 기록을 성공적으로 수집했습니다!")