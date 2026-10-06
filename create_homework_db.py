import sqlite3

conn = sqlite3.connect("stuplan.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS homeworks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    task TEXT NOT NULL,
    deadline TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0
)
""")

cursor.execute("SELECT COUNT(*) FROM homeworks")
count = cursor.fetchone()[0]

if count == 0:
    sample_data = [
        ("情報工学概論", "レポート提出", "6/21", 0),
        ("データベース", "SQL練習問題", "6/23", 0),
        ("ゼミ", "発表スライド作成", "6/26", 1),
    ]
    cursor.executemany(
        "INSERT INTO homeworks (subject, task, deadline, done) VALUES (?, ?, ?, ?)",
        sample_data
    )
    print("仮データを追加しました")
else:
    print("すでにデータがあります")

conn.commit()
conn.close()
print("homeworksテーブルの準備が完了しました")
