import os
import json
import random
import string
from datetime import datetime, date

import psycopg2
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
            columns = [
                column("id", PSQLType.SERIAL, primary_key=True),
                column("text_val", PSQLType.TEXT),
                column("int_val", PSQLType.INTEGER),
                column("float_val", PSQLType.FLOAT),
                column("date_val", PSQLType.DATE),
                column("created_at", PSQLType.TIMESTAMP, default="NOW()")
            ]
            create_sql = f"CREATE TABLE IF NOT EXISTS functional_results ({', '.join(columns)});"
            cur.execute(create_sql)
            conn.commit()

def generate_random_string(length: int = 12) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_row():
    return {
        "text_val": generate_random_string(),
        "int_val": random.randint(1, 1000),
        "float_val": round(random.uniform(0, 1000), 2),
        "date_val": date.today(),
        "created_at": datetime.utcnow(),
    }

def insert_sample_data():
    row_data = generate_row()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO functional_results (text_val, int_val, float_val, date_val, created_at)
                VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                (
                    row_data["text_val"],
                    row_data["int_val"],
                    row_data["float_val"],
                    row_data["date_val"],
                    row_data["created_at"],
                ),
            )
            new_id = cur.fetchone()[0]
            conn.commit()
    row_data["id"] = new_id
    return row_data

def lambda_handler(event, context):
    ensure_table()
    row = insert_sample_data()
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Functional data inserted", "row": row})
    } 