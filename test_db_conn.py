# test_db_conn.py
import os
import psycopg2
from dotenv import load_dotenv
import os.path

# 현재 디렉토리의 절대 경로
current_dir = os.path.dirname(os.path.abspath(__file__))
# .env 파일 절대 경로
env_path = os.path.join(current_dir, '.env')
print(f"환경 변수 파일 경로: {env_path}")
print(f"파일 존재 여부: {os.path.exists(env_path)}")

# .env 파일 로드
load_dotenv(env_path)

print('PGHOST=', os.getenv('PGHOST'))
try:
    conn = psycopg2.connect(
        host=os.getenv('PGHOST','localhost'),
        port=int(os.getenv('PGPORT',5432)),
        user=os.getenv('PGUSER','postgres'),
        password=os.getenv('PGPASSWORD','postgres'),
        dbname=os.getenv('PGDATABASE','postgres')
    )
    with conn.cursor() as cur:
        cur.execute("SELECT current_database(), current_user;")
        print(cur.fetchone())
    conn.close()
    print('DB 연결 성공')
except Exception as e:
    print('DB 연결 실패:', e)