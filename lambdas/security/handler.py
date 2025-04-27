import os, json, time, hashlib, random, psycopg2
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
                column("event_hash", PSQLType.TEXT),
                column("int_val", PSQLType.INTEGER),
                column("float_val", PSQLType.FLOAT),
                column("date_val", PSQLType.DATE),
                column("created_at", PSQLType.TIMESTAMP, default="NOW()")
            ]
            cur.execute(f"CREATE TABLE IF NOT EXISTS security_events ({', '.join(cols)});")
            conn.commit()

def gen_row():
    return {
        "event_hash": hashlib.sha256(str(time.time()).encode()).hexdigest(),
        "int_val": random.randint(1, 100),
        "float_val": random.random(),
        "date_val": date.today(),
        "created_at": datetime.utcnow(),
    }

def record_event():
    row = gen_row()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO security_events (event_hash, int_val, float_val, date_val, created_at)
                VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                (
                    row["event_hash"],
                    row["int_val"],
                    row["float_val"],
                    row["date_val"],
                    row["created_at"],
                ),
            )
            new_id = cur.fetchone()[0]
            conn.commit()
    row["id"] = new_id
    return row

def lambda_handler(event, context):
    ensure_table()
    row = record_event()
    return {"statusCode": 200, "body": json.dumps(row)} 