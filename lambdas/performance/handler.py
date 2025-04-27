import os, json, time, random, psycopg2
from datetime import datetime, date
from psycopg2.extras import RealDictCursor
from common import column, PSQLType

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", 5432)),
    "user": os.environ.get("DB_USER", "admin"),
    "password": os.environ.get("DB_PASSWORD", "secretpassword"),
    "dbname": os.environ.get("DB_NAME", "metrics"),
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

def ensure_table():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cols = [
                column("id", PSQLType.SERIAL, primary_key=True),
                column("latency_ms", PSQLType.INTEGER),
                column("created_at", PSQLType.TIMESTAMP, default="NOW()")
            ]
            cur.execute(f"CREATE TABLE IF NOT EXISTS performance_metrics ({', '.join(cols)});")
            conn.commit()

def record_metric():
    latency = random.randint(10, 500)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO performance_metrics (latency_ms) VALUES (%s) RETURNING id",
                (latency,),
            )
            new_id = cur.fetchone()[0]
            conn.commit()
    return {"id": new_id, "latency_ms": latency}

def lambda_handler(event, context):
    ensure_table()
    row = record_metric()
    return {"statusCode": 200, "body": json.dumps(row)}

# ------------------ performance measurement helpers ----------------

def measure_exec_time(func):
    start = time.time()
    result = func()
    duration = time.time() - start
    return result, duration 