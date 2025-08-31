import urllib.robotparser
import urllib.parse
from selenium import webdriver
from selenium.webdriver.common.by import By
import os
import ssl
import urllib.request as urlreq
import time
import pandas as pd
from selenium.webdriver.support.ui import Select, WebDriverWait
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import subprocess
import re

# Load environment variables from .env when present (local development convenience)
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path('.env'))

# optional app modules (present in repo)
try:
    from crawler import collect_current_season, collect_pitchers_season, collect_team_rankings_season
    from db import (
        get_conn,
        create_tables,
        count_hitters_by_year,
        count_pitchers_by_year,
        count_team_rankings_by_year,
        df_to_hitters_table,
        df_to_pitchers_table,
        df_to_team_rankings_table,
    )
except Exception:
    # allow running without DB modules for quick CSV-only tests
    collect_current_season = None
    collect_pitchers_season = None
    collect_team_rankings_season = None
    df_to_hitters_table = None
    df_to_pitchers_table = None
    df_to_team_rankings_table = None
    get_conn = None
    create_tables = None
    count_hitters_by_year = None
    count_pitchers_by_year = None
    count_team_rankings_by_year = None

# 🛡️ 크롤링 에티켓 설정
DELAY_BETWEEN_REQUESTS = 2.0
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def check_robots_txt(url: str) -> bool:
    """주어진 URL에 대해 robots.txt를 확인하고 크롤링 허용 여부를 반환합니다.

    SSL 인증서 검증 오류가 발생하면 검증을 비활성화하고 robots.txt를 가져와 파싱합니다.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        print(f"🔍 웹 크롤링 허가 확인: {robots_url}")
        print("   📖 robots.txt 파일을 읽어서 크롤링이 허용되는지 확인하고 있습니다...")

        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        try:
            rp.read()
        except Exception as e:
            # SSL 인증서 문제 등으로 rp.read()가 실패할 수 있음 -> 비검증으로 재시도
            try:
                print(f"   ⚠️ robots.txt 읽기 중 SSL 오류 발생({e}), 인증서 검증을 비활성화하고 재시도합니다...")
                data = urlreq.urlopen(robots_url, context=ssl._create_unverified_context(), timeout=10).read().decode('utf-8')
                rp.parse(data.splitlines())
            except Exception as e2:
                print(f"   ❌ robots.txt를 가져오지 못했습니다: {e2}")
                raise

        can_fetch = rp.can_fetch("*", url)
        if can_fetch:
            print(f"✅ 크롤링 허가 확인 완료!")
        else:
            print(f"❌ robots.txt가 이 URL의 크롤링을 금지합니다: {robots_url}")
        return can_fetch
    except Exception as e:
        print(f"⚠️  robots.txt 확인 중 오류 발생: {e}")
        print("   💭 인터넷 연결을 확인하거나 수동으로 robots.txt를 확인해 주세요.")
        return False


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

# 크롬드라이버 실행 - ChromeDriverManager를 사용, 로컬 Chrome 버전에서 major 추출해 시도
chromedriver_path_env = os.getenv('CHROMEDRIVER_PATH')
print(f"   🧪 디버그: CHROMEDRIVER_PATH env raw repr: {repr(chromedriver_path_env)}")
if chromedriver_path_env:
    print(f"   🧪 디버그: os.path.exists -> {os.path.exists(chromedriver_path_env)}")
else:
    # fallback to project drivers folder if .env wasn't read for any reason
    local_drv = os.path.join(os.getcwd(), 'drivers', 'chromedriver.exe')
    if os.path.exists(local_drv):
        chromedriver_path_env = local_drv
        print(f"   🧪 디버그: .env 미탐지, 로컬 드라이버 경로 사용 -> {chromedriver_path_env}")
    else:
        print(f"   🧪 디버그: 로컬 드라이버도 없음: {local_drv}")

try:
    svc = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=svc, options=chrome_options)
    print("   ✅ webdriver-manager로 드라이버 설치/실행 성공")
except Exception as e_wdm:
    print(f"   ⚠️ webdriver-manager 실패: {e_wdm}")
    # CHROMEDRIVER_PATH 있으면 시도
    if chromedriver_path_env and os.path.exists(chromedriver_path_env):
        try:
            svc = Service(chromedriver_path_env)
            driver = webdriver.Chrome(service=svc, options=chrome_options)
            print("   ✅ CHROMEDRIVER_PATH에 있는 드라이버로 실행 성공")
        except Exception as e_env:
            print(f"   ❌ CHROMEDRIVER_PATH 드라이버 실행 실패: {e_env}")
            raise RuntimeError("chromedriver 실행에 실패했습니다. CHROMEDRIVER_PATH를 확인하세요.")
    else:
        # 시도: 로컬 chrome 실행파일에서 버전 추출하고 major로 설치 시도
        chrome_candidates = [
            os.getenv('CHROME_PATH'),
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
        chrome_version = None
        for c in chrome_candidates:
            if not c:
                continue
            try:
                if os.path.exists(c):
                    out = subprocess.check_output([c, '--version'], stderr=subprocess.STDOUT, timeout=5)
                    s = out.decode('utf-8', errors='ignore')
                    m = re.search(r"(\d+)(?:\.\d+)*", s)
                    if m:
                        chrome_version = m.group(0)
                        break
            except Exception:
                continue

        if chrome_version:
            major = chrome_version.split('.')[0]
            try:
                print(f"   ℹ️ 로컬 Chrome 버전 감지: {chrome_version}, major={major} -> 해당 major용 드라이버 설치 시도")
                svc = Service(ChromeDriverManager(version=major).install())
                driver = webdriver.Chrome(service=svc, options=chrome_options)
                print("   ✅ webdriver-manager(major)로 드라이버 설치/실행 성공")
            except Exception as e_major:
                print(f"   ⚠️ webdriver-manager(major) 실패: {e_major}")
                raise RuntimeError("chromedriver를 찾을 수 없습니다. chromedriver를 설치하거나 CHROMEDRIVER_PATH를 설정하세요.")
        else:
            raise RuntimeError("chromedriver를 찾을 수 없습니다. chromedriver를 설치하거나 CHROMEDRIVER_PATH를 설정하세요.")

driver.implicitly_wait(10)

wait = WebDriverWait(driver, 10)

print("   ✅ 크롬 브라우저가 성공적으로 실행되었습니다!")
print("   💡 Chrome DevTools 메시지는 정상적인 브라우저 실행 로그입니다 (무시하셔도 됩니다)")

print(f"\n🌐 4단계: KBO 공식 홈페이지 접속")
print(f"   🔗 접속 중: {target_url}")

# robots.txt 확인 통과 후에만 접속
driver.get(target_url)

# 일부 사이트는 접속 직후 동의/쿠키/팝업 창이 떠서 자동화가 멈춥니다.
# 자주 등장하는 알럿과 동의 버튼을 자동으로 닫아 진행을 돕습니다.
try:
    # 짧게 대기 후 JS alert가 있는지 확인
    time.sleep(0.8)
    alert = driver.switch_to.alert
    alert_text = alert.text if hasattr(alert, 'text') else ''
    alert.accept()
    print(f"   ✅ 페이지의 JS alert를 수락했습니다: {alert_text}")
except Exception:
    # 알럿이 없으면 무시
    pass

# 흔한 동의/쿠키 버튼들을 XPath로 시도해서 클릭
popup_xpaths = [
    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'동의')]",
    "//button[contains(., '확인')]",
    "//button[contains(., '동의함')]",
    "//button[contains(., '수락')]",
    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'agree')]",
    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'accept')]",
    "//button[contains(., '닫기')]",
]
for xp in popup_xpaths:
    try:
        el = driver.find_element(By.XPATH, xp)
        el.click()
        print(f"   ✅ 팝업 버튼을 클릭했습니다 (XPath): {xp}")
        time.sleep(0.6)
        break
    except Exception:
        continue

# 디버깅용 스크린샷 저장
try:
    driver.save_screenshot('kbo_page_after_popup.png')
    print("   📸 팝업 처리 후 스크린샷 저장: kbo_page_after_popup.png")
except Exception:
    pass

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
        df = df1
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
    # DB 저장 시도: 환경 변수로 Postgres가 설정되어 있으면 자동으로 업서트
    if df_to_hitters_table and get_conn:
        try:
            print('\n🔁 DB 연결을 시도합니다...')
            conn = get_conn()
            try:
                create_tables(conn)
            except Exception:
                # create_tables 내부에서 커밋하므로 실패해도 계속
                pass
            conn.close()

            # 히터 저장
            try:
                n = df_to_hitters_table(result)
                print(f"   ✅ DB: hitters 테이블에 {n}건 저장(업서트) 완료")
            except Exception as e:
                print('   ⚠️ DB에 hitters 저장 실패:', e)
                print('   💾 CSV가 이미 저장되어 있으므로 수동 업로드를 진행하세요.')

            # 투수/팀 데이터는 crawler 모듈의 함수로 수집하여 저장
            if collect_pitchers_season:
                try:
                    pitchers_df = collect_pitchers_season(driver, current_season, safe_sleep)
                    if pitchers_df is not None and len(pitchers_df) > 0:
                        m = df_to_pitchers_table(pitchers_df)
                        print(f"   ✅ DB: pitchers 테이블에 {m}건 저장(업서트) 완료")
                except Exception as e:
                    print('   ⚠️ pitchers 수집/저장 실패:', e)

            if collect_team_rankings_season:
                try:
                    rankings_df = collect_team_rankings_season(driver, current_season, safe_sleep)
                    if rankings_df is not None and len(rankings_df) > 0:
                        k = df_to_team_rankings_table(rankings_df)
                        print(f"   ✅ DB: team_rankings 테이블에 {k}건 저장(업서트) 완료")
                except Exception as e:
                    print('   ⚠️ team_rankings 수집/저장 실패:', e)

        except Exception as e_conn:
            print('   ⚠️ DB 연결 실패:', e_conn)
            print('   💾 CSV 파일이 보존되어 있으니 파일을 DB에 수동으로 임포트하세요.')
    
else:
    print('❌ 오류: 데이터가 수집되지 않았습니다.')
    print('   💭 인터넷 연결이나 KBO 홈페이지 상태를 확인해 주세요.')

print(f"\n🏁 크롤링이 완료되었습니다!")
print(f"   🤖 크롬 브라우저를 자동으로 종료합니다...")
driver.quit()
print(f"   ✅ 모든 작업이 성공적으로 완료되었습니다!")
print(f"   🎉 {current_season}시즌 KBO 타자 기록을 성공적으로 수집했습니다!")