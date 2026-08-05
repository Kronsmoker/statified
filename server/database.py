import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_db():
    if DATABASE_URL:
        return psycopg2.connect(
            DATABASE_URL,
            cursor_factory=RealDictCursor
        )

    return sqlite3.connect("statified.db")


def execute_query(query, params=None, fetch=False):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(query, params or ())

    result = None
    if fetch:
        result = cur.fetchall()

    conn.commit()
    cur.close()
    conn.close()

    return result
