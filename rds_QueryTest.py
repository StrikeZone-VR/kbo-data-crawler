import os
import psycopg2
from dotenv import load_dotenv

def query_rds():
    """
    RDS에 연결하여 간단한 쿼리를 실행하는 함수.
    """
    # .env 파일 로드
    load_dotenv()

    # 환경 변수에서 RDS 연결 정보 가져오기
    host = os.getenv('PGHOST')
    port = os.getenv('PGPORT')
    user = os.getenv('PGUSER')
    password = os.getenv('PGPASSWORD')
    dbname = os.getenv('PGDATABASE')

    try:
        # PostgreSQL 연결
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname
        )
        print("✅ RDS 연결 성공")

        # 커서 생성 및 간단한 쿼리 실행
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user;")
            result = cur.fetchone()
            print("📊 쿼리 결과:", result)

        # 연결 종료
        conn.close()
        print("🔒 연결 종료")

    except Exception as e:
        print("❌ RDS 연결 실패:", e)

if __name__ == "__main__":
    query_rds()
