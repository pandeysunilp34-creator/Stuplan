import sqlite3

conn = sqlite3.connect("stuplan.db")
cursor = conn.cursor()

# schedulesテーブルを作成
cursor.execute("""
CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time TEXT NOT NULL,
    title TEXT NOT NULL,
    place TEXT NOT NULL
)
""")

# 仮データを入れる（最初の1回だけ）
cursor.execute("SELECT COUNT(*) FROM schedules")
count = cursor.fetchone()[0]

if count == 0:
    sample_data = [
        ("09:00", "情報工学概論", "201教室"),
        ("13:00", "ゼミ", "研究室"),
        ("18:00", "アルバイト", "コンビニ"),
    ]
    cursor.executemany("INSERT INTO schedules (time, title, place) VALUES (?, ?, ?)", sample_data)
    print("仮データを追加しました")
else:
    print("すでにデータがあります")

conn.commit()
conn.close()
print("データベースの準備が完了しました")
