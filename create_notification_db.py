import sqlite3

conn = sqlite3.connect("stuplan.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    message TEXT NOT NULL,
    time TEXT NOT NULL
)
""")

cursor.execute("SELECT COUNT(*) FROM notifications")
count = cursor.fetchone()[0]

if count == 0:
    sample_data = [
        ("宿題", "データベースの宿題は6/23までです", "1時間前"),
        ("授業", "明日の情報工学概論は201教室です", "3時間前"),
        ("アルバイト", "6/20のシフトが追加されました", "1日前"),
    ]
    cursor.executemany(
        "INSERT INTO notifications (type, message, time) VALUES (?, ?, ?)",
        sample_data
    )
    print("仮データを追加しました")
else:
    print("すでにデータがあります")

conn.commit()
conn.close()
print("notificationsテーブルの準備が完了しました")
