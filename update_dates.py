import sqlite3

conn = sqlite3.connect("stuplan.db")
cursor = conn.cursor()

# 今の宿題データを、年-月-日の形に直す
cursor.execute("SELECT id, deadline FROM homeworks")
rows = cursor.fetchall()

for row in rows:
    homework_id, deadline = row
    # "6/21" のような形を "2026-06-21" の形に変える
    if "/" in deadline and "-" not in deadline:
        month, day = deadline.split("/")
        new_deadline = f"2026-{int(month):02d}-{int(day):02d}"
        cursor.execute("UPDATE homeworks SET deadline = ? WHERE id = ?", (new_deadline, homework_id))
        print(f"変更: {deadline} → {new_deadline}")

conn.commit()
conn.close()
print("日付の変更が完了しました")
