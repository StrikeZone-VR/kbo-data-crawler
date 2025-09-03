"""db.py
간단한 Postgres 연결과 테이블 생성 유틸리티.

환경 변수로 다음 값을 읽는다:
  - PGHOST (기본: localhost)
  - PGPORT (기본: 5432)
  - PGUSER
  - PGPASSWORD
  - PGDATABASE

이 모듈은 psycopg2를 사용한다.
"""
import os
import os.path
from dotenv import load_dotenv

# 현재 디렉토리의 절대 경로
current_dir = os.path.dirname(os.path.abspath(__file__))
# .env 파일 절대 경로
env_path = os.path.join(current_dir, '.env')
load_dotenv(env_path)
try:
    import psycopg2
    from psycopg2.extras import execute_values
except Exception as e:
    psycopg2 = None
    execute_values = None
    print("⚠️ psycopg2 모듈을 불러오지 못함. Postgres에 연결하려면 'psycopg2-binary'를 설치해야 한다.")


def _parse_fractional_innings(s: str) -> float:
    """Convert innings written like '12 1/3' or '12 2/3' to float (e.g. 12.3333...)."""
    try:
        s = str(s).strip()
        if not s:
            return None
        # Common formats: '12 1/3', '12', '12.1' (treat as literal float)
        if '/' in s:
            parts = s.split()
            if len(parts) == 2:
                whole = float(parts[0].replace(',', ''))
                num, den = parts[1].split('/')
                return whole + (float(num) / float(den))
            else:
                # fallback: try to evaluate a single fraction
                if ' ' not in s:
                    # e.g. '1/3'
                    num, den = s.split('/')
                    return float(num) / float(den)
        # no fraction, try plain float
        return float(s.replace(',', ''))
    except Exception:
        return None


def _safe_number(val, target_type: str):
    """Convert val to appropriate Python type or None.

    target_type: 'int', 'real', 'ip' (innings), 'text'
    """
    if val is None:
        return None
    s = str(val).strip()
    if s in ('', '-', '—', '–'):
        return None
    try:
        if target_type == 'text':
            return s
        if target_type == 'int':
            # remove commas and any non-digit trailing
            s2 = s.replace(',', '')
            return int(float(s2))
        if target_type == 'real':
            s2 = s.replace(',', '').replace('%', '')
            return float(s2)
        if target_type == 'ip':
            return _parse_fractional_innings(s)
    except Exception:
        return None



def get_conn():
    """환경 변수로 Postgres 연결을 생성하여 반환한다."""
    host = os.getenv('PGHOST', 'localhost')
    port = int(os.getenv('PGPORT', 5432))
    user = os.getenv('PGUSER', 'postgres')
    password = os.getenv('PGPASSWORD', '')
    dbname = os.getenv('PGDATABASE', 'kbo')

    conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
    return conn


def create_tables(conn):
    """필요한 테이블을 생성한다. id 대신 (player_name, team, year)을 기본키로 사용한다."""
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS hitters (
            player_name TEXT NOT NULL,
            team TEXT,
            avg REAL,
            g INTEGER,
            pa INTEGER,
            ab INTEGER,
            r INTEGER,
            h INTEGER,
            doubles INTEGER,
            triples INTEGER,
            hr INTEGER,
            tb INTEGER,
            rbi INTEGER,
            sac INTEGER,
            sf INTEGER,
            year INTEGER NOT NULL,
            PRIMARY KEY (player_name, team, year)
        );
        """)
        # pitchers 테이블
        cur.execute("""
        CREATE TABLE IF NOT EXISTS pitchers (
            player_name TEXT NOT NULL,
            team TEXT,
            era REAL,
            ip REAL,
            w INTEGER,
            l INTEGER,
            sv INTEGER,
            so INTEGER,
            bb INTEGER,
            h INTEGER,
            hr INTEGER,
            year INTEGER NOT NULL,
            PRIMARY KEY (player_name, team, year)
        );
        """)

        # team_rankings 테이블
        cur.execute("""
        CREATE TABLE IF NOT EXISTS team_rankings (
            team TEXT NOT NULL,
            games INTEGER,
            rank INTEGER,
            wins INTEGER,
            losses INTEGER,
            draws INTEGER,
            pct REAL,
            gb REAL,
            streak TEXT,
            last10 TEXT,
            home_record TEXT,
            away_record TEXT,
            year INTEGER NOT NULL,
            PRIMARY KEY (team, year)
        );
        """)
        # If the table existed from an older run, ensure expected columns exist.
        # This avoids failing INSERTs when new columns were added after the table was first created.
        cur.execute("ALTER TABLE team_rankings ADD COLUMN IF NOT EXISTS games INTEGER;")
        cur.execute("ALTER TABLE team_rankings ADD COLUMN IF NOT EXISTS streak TEXT;")
        cur.execute("ALTER TABLE team_rankings ADD COLUMN IF NOT EXISTS last10 TEXT;")
        cur.execute("ALTER TABLE team_rankings ADD COLUMN IF NOT EXISTS home_record TEXT;")
        cur.execute("ALTER TABLE team_rankings ADD COLUMN IF NOT EXISTS away_record TEXT;")
        # 미래 확장: players, teams 등의 메타 테이블을 추가가능.
        conn.commit()


def count_hitters_by_year(conn, year):
    """해당 연도에 저장된 hitters 레코드 수를 반환한다."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM hitters WHERE year = %s", (int(year),))
        r = cur.fetchone()
        return r[0] if r else 0


def count_pitchers_by_year(conn, year):
    """해당 연도에 저장된 pitchers 레코드 수를 반환한다."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM pitchers WHERE year = %s", (int(year),))
        r = cur.fetchone()
        return r[0] if r else 0


def count_team_rankings_by_year(conn, year):
    """해당 연도에 저장된 team_rankings 레코드 수를 반환한다."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM team_rankings WHERE year = %s", (int(year),))
        r = cur.fetchone()
        return r[0] if r else 0


def df_to_hitters_table(df):
    """DataFrame을 hitters 테이블에 upsert 형태로 저장한다.
    기대하는 컬럼: 한글 컬럼명(예: '선수명','팀명','HR' 등)과 'year' 열이 포함되어야 한다.
    """
    if execute_values is None:
        raise RuntimeError("psycopg2.extras.execute_values를 사용할 수 없음. 'psycopg2-binary'를 설치할 것")

    colmap = {
        '선수명': 'player_name',
        '팀명': 'team',
        'AVG': 'avg',
        'G': 'g',
        'PA': 'pa',
        'AB': 'ab',
        'R': 'r',
        'H': 'h',
        '2B': 'doubles',
        '3B': 'triples',
        'HR': 'hr',
        'TB': 'tb',
        'RBI': 'rbi',
        'SAC': 'sac',
        'SF': 'sf',
        'year': 'year'
    }

    cols = []
    for df_col, db_col in colmap.items():
        if df_col in df.columns:
            cols.append((db_col, df_col))

    if not cols:
        raise ValueError('DataFrame에 필요한 컬럼이 없음. 원본 컬럼명을 확인할 것.')

    insert_cols = [c[0] for c in cols]
    df_cols = [c[1] for c in cols]
    # Deduplicate by primary key columns if present (player_name, team, year)
    key_df_cols = [df_col for db_col, df_col in cols if db_col in ('player_name', 'team', 'year')]
    if key_df_cols:
        df = df.copy()
        df = df.drop_duplicates(subset=key_df_cols, keep='last')

    records = []
    for _, row in df.iterrows():
        values = []
        for db_col, df_col in zip(insert_cols, df_cols):
            val = row[df_col] if df_col in row.index else None
            if db_col in ('player_name', 'team'):
                values.append(_safe_number(val, 'text'))
            elif db_col in ('year', 'g', 'pa', 'ab', 'r', 'h', 'doubles', 'triples', 'hr', 'tb', 'rbi', 'sac', 'sf'):
                values.append(_safe_number(val, 'int'))
            else:
                values.append(_safe_number(val, 'real'))
        records.append(tuple(values))

    if not records:
        return 0

    insert_sql = (
        f"INSERT INTO hitters ({', '.join(insert_cols)}) VALUES %s "
        f"ON CONFLICT (player_name, team, year) DO UPDATE SET "
        + ", ".join([f"{col}=EXCLUDED.{col}" for col in insert_cols if col not in ('player_name','team','year')])
    )

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            execute_values(cur, insert_sql, records)
        conn.commit()
        return len(records)
    finally:
        conn.close()


def df_to_pitchers_table(df):
    if execute_values is None:
        raise RuntimeError("psycopg2.extras.execute_values를 사용할 수 없음. 'psycopg2-binary'를 설치할 것")

    colmap = {
        '선수명': 'player_name',
        '팀명': 'team',
        'ERA': 'era',
        'IP': 'ip',
        'W': 'w',
        'L': 'l',
        'SV': 'sv',
        'SO': 'so',
        'BB': 'bb',
        'H': 'h',
        'HR': 'hr',
        'year': 'year'
    }

    cols = []
    for df_col, db_col in colmap.items():
        if df_col in df.columns:
            cols.append((db_col, df_col))

    if not cols:
        raise ValueError('투수 DataFrame에 필요한 컬럼이 없음.')

    insert_cols = [c[0] for c in cols]
    df_cols = [c[1] for c in cols]

    # Deduplicate by primary key columns if present (player_name, team, year)
    key_df_cols = [df_col for db_col, df_col in cols if db_col in ('player_name', 'team', 'year')]
    if key_df_cols:
        df = df.copy()
        df = df.drop_duplicates(subset=key_df_cols, keep='last')

    # sanitize pitcher numeric values (IP may be fractional string)
    records2 = []
    for _, row in df.iterrows():
        vals = []
        for db_col, df_col in zip(insert_cols, df_cols):
            val = row[df_col] if df_col in row.index else None
            if db_col in ('player_name', 'team'):
                vals.append(_safe_number(val, 'text'))
            elif db_col in ('year', 'w', 'l', 'sv', 'so', 'bb', 'h', 'hr'):
                vals.append(_safe_number(val, 'int'))
            elif db_col == 'ip':
                vals.append(_safe_number(val, 'ip'))
            else:
                vals.append(_safe_number(val, 'real'))
        records2.append(tuple(vals))
    records = records2
    if not records:
        return 0

    insert_sql = (
        f"INSERT INTO pitchers ({', '.join(insert_cols)}) VALUES %s "
        f"ON CONFLICT (player_name, team, year) DO UPDATE SET "
        + ", ".join([f"{col}=EXCLUDED.{col}" for col in insert_cols if col not in ('player_name','team','year')])
    )

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            execute_values(cur, insert_sql, records)
        conn.commit()
        return len(records)
    finally:
        conn.close()


def df_to_team_rankings_table(df):
    if execute_values is None:
        raise RuntimeError("psycopg2.extras.execute_values를 사용할 수 없음. 'psycopg2-binary'를 설치할 것")

    colmap = {
    # accept common header variants from KBO tables
    '팀': 'team',
    '팀명': 'team',
    '순위': 'rank',
    '순위.1': 'rank',
    '경기': 'games',
    'G': 'games',
    '승': 'wins',
    '패': 'losses',
    '무': 'draws',
    '승률': 'pct',
    '게임차': 'gb',
    'GB': 'gb',
    '연속': 'streak',
    '최근10경기': 'last10',
    '홈': 'home_record',
    '방문': 'away_record',
    'year': 'year'
    }

    cols = []
    for df_col, db_col in colmap.items():
        if df_col in df.columns:
            cols.append((db_col, df_col))

    if not cols:
        raise ValueError('팀 순위 DataFrame에 필요한 컬럼이 없음.')

    insert_cols = [c[0] for c in cols]
    df_cols = [c[1] for c in cols]

    # Deduplicate by primary key columns if present (team, year)
    key_df_cols = [df_col for db_col, df_col in cols if db_col in ('team', 'year')]
    if key_df_cols:
        df = df.copy()
        df = df.drop_duplicates(subset=key_df_cols, keep='last')

    # sanitize team ranking numeric values
    records2 = []
    for _, row in df.iterrows():
        vals = []
        for db_col, df_col in zip(insert_cols, df_cols):
            val = row[df_col] if df_col in row.index else None
            if db_col in ('team', 'streak', 'last10', 'home_record', 'away_record'):
                vals.append(_safe_number(val, 'text'))
            elif db_col in ('year', 'rank', 'wins', 'losses', 'draws', 'games'):
                vals.append(_safe_number(val, 'int'))
            else:
                vals.append(_safe_number(val, 'real'))
        records2.append(tuple(vals))
    records = records2
    if not records:
        return 0

    insert_sql = (
        f"INSERT INTO team_rankings ({', '.join(insert_cols)}) VALUES %s "
        f"ON CONFLICT (team, year) DO UPDATE SET "
        + ", ".join([f"{col}=EXCLUDED.{col}" for col in insert_cols if col not in ('team','year')])
    )

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            execute_values(cur, insert_sql, records)
        conn.commit()
        return len(records)
    finally:
        conn.close()
