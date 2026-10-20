import os
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URLが設定されていません")
    exit()

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS schedules (
    id SERIAL PRIMARY KEY,
    time TEXT NOT NULL,
    title TEXT NOT NULL,
    place TEXT NOT NULL,
    user_id INTEGER DEFAULT 1
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS homeworks (
    id SERIAL PRIMARY KEY,
    subject TEXT NOT NULL,
    task TEXT NOT NULL,
    deadline TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0,
    user_id INTEGER DEFAULT 1
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS parttime_jobs (
    id SERIAL PRIMARY KEY,
    date TEXT NOT NULL,
    start TEXT NOT NULL,
    "end" TEXT NOT NULL,
    place TEXT NOT NULL,
    user_id INTEGER DEFAULT 1
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    type TEXT NOT NULL,
    message TEXT NOT NULL,
    time TEXT NOT NULL,
    user_id INTEGER DEFAULT 1
)
""")

conn.commit()
conn.close()
print("全テーブルの作成が完了しました")
