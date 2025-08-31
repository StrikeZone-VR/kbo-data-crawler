# test_db_conn.py
import os
import psycopg2

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