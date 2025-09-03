"""
create_tables.py - StrikeZone_VR 데이터베이스의 테이블을 생성하는 스크립트
"""
import os
from dotenv import load_dotenv
import os.path
import psycopg2

# 현재 디렉토리의 절대 경로
current_dir = os.path.dirname(os.path.abspath(__file__))
# .env 파일 절대 경로
env_path = os.path.join(current_dir, '.env')
load_dotenv(env_path)

def get_conn():
    """환경 변수로 Postgres 연결을 생성하여 반환한다."""
    host = os.getenv('PGHOST', 'localhost')
    port = int(os.getenv('PGPORT', 5432))
    user = os.getenv('PGUSER', 'postgres')
    password = os.getenv('PGPASSWORD', '')
    dbname = os.getenv('PGDATABASE', 'StrikeZone_VR')

    conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
    return conn

def create_tables(conn):
    """필요한 테이블을 생성한다."""
    with conn.cursor() as cur:
        # 타자(hitters) 테이블
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
        
        # 투수(pitchers) 테이블
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
        
        # 팀 순위(team_rankings) 테이블
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
        
        # 필요한 컬럼 추가 (ALTER TABLE)
        cur.execute("ALTER TABLE IF EXISTS team_rankings ADD COLUMN IF NOT EXISTS games INTEGER;")
        cur.execute("ALTER TABLE IF EXISTS team_rankings ADD COLUMN IF NOT EXISTS streak TEXT;")
        cur.execute("ALTER TABLE IF EXISTS team_rankings ADD COLUMN IF NOT EXISTS last10 TEXT;")
        cur.execute("ALTER TABLE IF EXISTS team_rankings ADD COLUMN IF NOT EXISTS home_record TEXT;")
        cur.execute("ALTER TABLE IF EXISTS team_rankings ADD COLUMN IF NOT EXISTS away_record TEXT;")
    
    conn.commit()
    print("테이블이 성공적으로 생성!")

if __name__ == "__main__":
    try:
        conn = get_conn()
        create_tables(conn)
        conn.close()
        print("데이터베이스 스키마 생성 완료!")
    except Exception as e:
        print(f"오류 발생: {e}")
