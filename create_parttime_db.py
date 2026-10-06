import sqlite3

conn = sqlite3.connect("stuplan.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS parttime_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    start TEXT NOT NULL,
    end TEXT NOT NULL,
    place TEXT NOT NULL
)
""")

cursor.execute("SELECT COUNT(*) FROM parttime_jobs")
count = cursor.fetchone()[0]

if count == 0:
    sample_data = [
        ("6/20 (土)", "10:00", "16:00", "コンビニ"),
        ("6/22 (月)", "18:00", "22:00", "コンビニ"),
        ("6/25 (木)", "09:00", "13:00", "カフェ"),
    ]
    cursor.executemany(
        "INSERT INTO parttime_jobs (date, start, end, place) VALUES (?, ?, ?, ?)",
        sample_data
    )
    print("仮データを追加しました")
else:
    print("すでにデータがあります")

conn.commit()
conn.close()
print("parttime_jobsテーブルの準備が完了しました")
