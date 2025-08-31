"""crawler.py
KBO 웹사이트에서 현재 시즌의 타자 기록을 수집하는 함수들을 모아둔 모듈입니다.
함수 반환값은 pandas.DataFrame 형태입니다.
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from bs4 import BeautifulSoup
import pandas as pd
import time


def create_table_from_page(driver):
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.select_one('#cphContents_cphContents_cphContents_udpContent > div.record_result > table')
    df = pd.read_html(str(table), flavor='html5lib')[0]
    return df


def get_team_list(driver, sleep_fn):
    sleep_fn()
    combobox = driver.find_element(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_ddlTeam_ddlTeam')
    sleep_fn()
    options = combobox.find_elements(By.TAG_NAME, 'option')[1:]
    teams = [opt.text for opt in options]
    return teams


def collect_current_season(driver, season, sleep_fn):
    """현재 시즌(season 문자열, 예: '2025')의 모든 팀 타자 데이터를 수집하여 하나의 DataFrame으로 반환합니다."""
    # 시즌 선택
    season_combo = driver.find_element(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_ddlSeason_ddlSeason')
    season_combo = Select(season_combo)
    season_combo.select_by_value(season)
    teams = get_team_list(driver, sleep_fn)

    dfs = []
    for team in teams:
        sleep_fn()
        combobox = driver.find_element(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_ddlTeam_ddlTeam')
        team_combo = Select(combobox)
        team_combo.select_by_visible_text(team)
        sleep_fn()
        df = create_table_from_page(driver)
        # 페이징이 있으면 2페이지 합치기
        page_links = driver.find_elements(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_udpContent > div.record_result > div > a')
        if len(page_links) > 1:
            driver.find_element(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_ucPager_btnNo2').click()
            sleep_fn()
            df2 = create_table_from_page(driver)
            # 페이지 원복
            driver.find_element(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_ucPager_btnNo1').click()
            df = pd.concat([df, df2], ignore_index=True)

        df['team'] = team
        df['year'] = int(season)
        dfs.append(df)

    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()


def collect_pitchers_season(driver, season, sleep_fn):
    """현재 시즌의 투수 기록을 수집하여 DataFrame으로 반환합니다."""
    # 페이지로 이동(투수 기본 기록 페이지로 추정 경로)
    target = 'https://www.koreabaseball.com/Record/Player/PitcherBasic/Basic1.aspx'
    driver.get(target)
    sleep_fn()

    # 시즌 선택
    season_combo = driver.find_element(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_ddlSeason_ddlSeason')
    season_combo = Select(season_combo)
    season_combo.select_by_value(season)
    sleep_fn()

    teams = get_team_list(driver, sleep_fn)
    dfs = []
    for team in teams:
        sleep_fn()
        combobox = driver.find_element(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_ddlTeam_ddlTeam')
        team_combo = Select(combobox)
        team_combo.select_by_visible_text(team)
        sleep_fn()
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.select_one('#cphContents_cphContents_cphContents_udpContent > div.record_result > table')
        if table is None:
            continue
        df = pd.read_html(str(table), flavor='html5lib')[0]
        # 페이징 처리(간단)
        page_links = driver.find_elements(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_udpContent > div.record_result > div > a')
        if len(page_links) > 1:
            driver.find_element(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_ucPager_btnNo2').click()
            sleep_fn()
            df2 = pd.read_html(str(BeautifulSoup(driver.page_source, 'html.parser').select_one('#cphContents_cphContents_cphContents_udpContent > div.record_result > table')), flavor='html5lib')[0]
            driver.find_element(By.CSS_SELECTOR, '#cphContents_cphContents_cphContents_ucPager_btnNo1').click()
            df = pd.concat([df, df2], ignore_index=True)

        df['team'] = team
        df['year'] = int(season)
        dfs.append(df)

    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()


def collect_team_rankings_season(driver, season, sleep_fn):
    """현재 시즌 팀 순위를 수집하여 DataFrame으로 반환합니다."""
    # 팀 순위(일별) 페이지로 이동 — KBO 사이트의 최신 경로
    target = 'https://www.koreabaseball.com/Record/TeamRank/TeamRankDaily.aspx'
    driver.get(target)
    sleep_fn()

    # 페이지에서 순위 테이블 찾기
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    # 여러 가능한 선택자를 시도해서 테이블을 찾음
    table = soup.select_one('#cphContents_cphContents_cphContents_udpContent > div.rank_result > table')
    if table is None:
        table = soup.select_one('table.tData')
    if table is None:
        # fallback: 페이지의 첫 번째 테이블
        table = soup.find('table')
    if table is None:
        return pd.DataFrame()

    df = pd.read_html(str(table), flavor='html5lib')[0]
    # 표 헤더 차이에 대비: '팀명' -> '팀' 등
    if '팀명' in df.columns and '팀' not in df.columns:
        df = df.rename(columns={'팀명': '팀'})
    if '게임차' in df.columns and 'GB' not in df.columns:
        # leave both names; db layer accepts '게임차' too
        pass
    # 표에 연도 컬럼이 없다면 추가
    df['year'] = int(season)
    return df
