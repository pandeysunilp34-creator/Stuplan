from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import date
import calendar
from translations import TRANSLATIONS

app = Flask(__name__)
import os

def init_db():
    """PostgreSQLのテーブルを自動作成する"""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT NOT NULL UNIQUE, password TEXT NOT NULL)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS schedules (id SERIAL PRIMARY KEY, time TEXT NOT NULL, title TEXT NOT NULL, place TEXT NOT NULL, user_id INTEGER DEFAULT 1)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS homeworks (id SERIAL PRIMARY KEY, subject TEXT NOT NULL, task TEXT NOT NULL, deadline TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0, user_id INTEGER DEFAULT 1)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS parttime_jobs (id SERIAL PRIMARY KEY, date TEXT NOT NULL, start TEXT NOT NULL, "end" TEXT NOT NULL, place TEXT NOT NULL, user_id INTEGER DEFAULT 1)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS notifications (id SERIAL PRIMARY KEY, type TEXT NOT NULL, message TEXT NOT NULL, time TEXT NOT NULL, user_id INTEGER DEFAULT 1)""")
        conn.commit()
        conn.close()
        print("PostgreSQLテーブル作成完了")
    except Exception as e:
        print(f"テーブル作成エラー: {e}")

init_db()

app.secret_key = "stuplan_secret_key_2026"

def get_db_connection():
    import os
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(database_url)
        return conn
    else:
        conn = sqlite3.connect("stuplan.db")
        conn.row_factory = sqlite3.Row
        return conn

def get_user_id():
    return session.get("user_id", 1)

def get_schedules(keyword=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    uid = get_user_id()
    if keyword:
        cursor.execute(
            "SELECT * FROM schedules WHERE user_id = ? AND (title LIKE ? OR place LIKE ?) ORDER BY time",
            (uid, f"%{keyword}%", f"%{keyword}%")
        )
    else:
        cursor.execute("SELECT * FROM schedules WHERE user_id = ? ORDER BY time", (uid,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_schedule_by_id(schedule_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM schedules WHERE id = ? AND user_id = ?", (schedule_id, get_user_id()))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_homeworks():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM homeworks WHERE user_id = ? ORDER BY deadline", (get_user_id(),))
    rows = cursor.fetchall()
    conn.close()
    today = date.today().isoformat()
    result = []
    for row in rows:
        item = dict(row)
        item["overdue"] = (item["deadline"] < today) and not item["done"]
        result.append(item)
    return result

def get_homework_by_id(homework_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM homeworks WHERE id = ? AND user_id = ?", (homework_id, get_user_id()))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_parttime_jobs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM parttime_jobs WHERE user_id = ? ORDER BY date", (get_user_id(),))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_parttime_job_by_id(job_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM parttime_jobs WHERE id = ? AND user_id = ?", (job_id, get_user_id()))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_notifications():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC", (get_user_id(),))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# --- 言語選択 ---
@app.route("/")
def index():
    if "lang" not in session:
        return redirect("/language")
    return redirect("/home")

@app.route("/language")
def language():
    return render_template("language.html")

@app.route("/set_language/<lang>")
def set_language(lang):
    if lang in ["ja", "en", "np"]:
        session["lang"] = lang
    return redirect("/login")

# --- Login ---
@app.route("/login", methods=["GET", "POST"])
def login():
    lang = session.get("lang", "ja")
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/home")
        else:
            error = {"ja": "ユーザー名またはパスワードが違います", "en": "Incorrect username or password", "np": "प्रयोगकर्ता नाम वा पासवर्ड गलत छ"}.get(lang)
            return render_template("login.html", error=error, lang=lang)
    return render_template("login.html", lang=lang)

# --- Register ---
@app.route("/register", methods=["GET", "POST"])
def register():
    lang = session.get("lang", "ja")
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        password_confirm = request.form["password_confirm"]
        if len(password) < 6:
            error = {"ja": "パスワードは6文字以上にしてください", "en": "Password must be at least 6 characters", "np": "पासवर्ड कम्तीमा ६ अक्षर हुनुपर्छ"}.get(lang)
            return render_template("register.html", error=error, lang=lang)
        if password != password_confirm:
            error = {"ja": "パスワードが一致しません", "en": "Passwords do not match", "np": "पासवर्ड मेल खाएन"}.get(lang)
            return render_template("register.html", error=error, lang=lang)
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, generate_password_hash(password)))
            conn.commit()
            conn.close()
            success = {"ja": "登録が完了しました。ログインしてください。", "en": "Registration complete. Please login.", "np": "दर्ता सफल भयो। कृपया लगइन गर्नुहोस्।"}.get(lang)
            return render_template("register.html", success=success, lang=lang)
        except:
            error = {"ja": "そのユーザー名はすでに使われています", "en": "That username is already taken", "np": "त्यो प्रयोगकर्ता नाम पहिले नै प्रयोग भइसकेको छ"}.get(lang)
            return render_template("register.html", error=error, lang=lang)
    return render_template("register.html", lang=lang)

# --- Logout ---
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/language")

# --- Home ---
@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect("/login")
    uid = get_user_id()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM schedules WHERE user_id = ?", (uid,))
    schedule_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM homeworks WHERE done = 0 AND user_id = ?", (uid,))
    homework_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM parttime_jobs WHERE user_id = ?", (uid,))
    parttime_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM notifications WHERE user_id = ?", (uid,))
    notification_count = cursor.fetchone()[0]
    conn.close()
    return render_template("home.html", schedule_count=schedule_count, homework_count=homework_count, parttime_count=parttime_count, notification_count=notification_count, lang=session.get("lang", "ja"))

# --- Schedule ---
@app.route("/schedule")
def schedule():
    keyword = request.args.get("keyword", "")
    schedules = get_schedules(keyword)
    lang = session.get("lang", "ja")
    t = TRANSLATIONS[lang]
    return render_template("schedule.html", schedules=schedules, keyword=keyword, t=t)

@app.route("/schedule/add", methods=["GET", "POST"])
def add_schedule():
    lang = session.get("lang", "ja")
    t = TRANSLATIONS[lang]
    if request.method == "POST":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO schedules (time, title, place, user_id) VALUES (?, ?, ?, ?)",
            (request.form["time"], request.form["title"], request.form["place"], get_user_id()))
        conn.commit()
        conn.close()
        return redirect("/schedule")
    return render_template("add_schedule.html", t=t)

@app.route("/schedule/edit/<int:schedule_id>", methods=["GET", "POST"])
def edit_schedule(schedule_id):
    lang = session.get("lang", "ja")
    t = TRANSLATIONS[lang]
    if request.method == "POST":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE schedules SET time = ?, title = ?, place = ? WHERE id = ? AND user_id = ?",
            (request.form["time"], request.form["title"], request.form["place"], schedule_id, get_user_id()))
        conn.commit()
        conn.close()
        return redirect("/schedule")
    return render_template("edit_schedule.html", item=get_schedule_by_id(schedule_id), t=t)

@app.route("/schedule/delete/<int:schedule_id>")
def delete_schedule(schedule_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM schedules WHERE id = ? AND user_id = ?", (schedule_id, get_user_id()))
    conn.commit()
    conn.close()
    return redirect("/schedule")

# --- Homework ---
@app.route("/homework")
def homework():
    lang = session.get("lang", "ja")
    t = TRANSLATIONS[lang]
    return render_template("homework.html", homeworks=get_homeworks(), t=t)

@app.route("/homework/add", methods=["GET", "POST"])
def add_homework():
    lang = session.get("lang", "ja")
    t = TRANSLATIONS[lang]
    if request.method == "POST":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO homeworks (subject, task, deadline, done, user_id) VALUES (?, ?, ?, 0, ?)",
            (request.form["subject"], request.form["task"], request.form["deadline"], get_user_id()))
        conn.commit()
        conn.close()
        return redirect("/homework")
    return render_template("add_homework.html", t=t)

@app.route("/homework/edit/<int:homework_id>", methods=["GET", "POST"])
def edit_homework(homework_id):
    lang = session.get("lang", "ja")
    t = TRANSLATIONS[lang]
    if request.method == "POST":
        done = 1 if request.form.get("done") == "on" else 0
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE homeworks SET subject = ?, task = ?, deadline = ?, done = ? WHERE id = ? AND user_id = ?",
            (request.form["subject"], request.form["task"], request.form["deadline"], done, homework_id, get_user_id()))
        conn.commit()
        conn.close()
        return redirect("/homework")
    return render_template("edit_homework.html", item=get_homework_by_id(homework_id), t=t)

@app.route("/homework/delete/<int:homework_id>")
def delete_homework(homework_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM homeworks WHERE id = ? AND user_id = ?", (homework_id, get_user_id()))
    conn.commit()
    conn.close()
    return redirect("/homework")

# --- Part-time Job ---
@app.route("/parttime")
def parttime():
    lang = session.get("lang", "ja")
    t = TRANSLATIONS[lang]
    return render_template("parttime.html", parttime_jobs=get_parttime_jobs(), t=t)

@app.route("/parttime/add", methods=["GET", "POST"])
def add_parttime():
    lang = session.get("lang", "ja")
    t = TRANSLATIONS[lang]
    if request.method == "POST":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO parttime_jobs (date, start, end, place, user_id) VALUES (?, ?, ?, ?, ?)",
            (request.form["date"], request.form["start"], request.form["end"], request.form["place"], get_user_id()))
        conn.commit()
        conn.close()
        return redirect("/parttime")
    return render_template("add_parttime.html", t=t)

@app.route("/parttime/edit/<int:job_id>", methods=["GET", "POST"])
def edit_parttime(job_id):
    lang = session.get("lang", "ja")
    t = TRANSLATIONS[lang]
    if request.method == "POST":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE parttime_jobs SET date = ?, start = ?, end = ?, place = ? WHERE id = ? AND user_id = ?",
            (request.form["date"], request.form["start"], request.form["end"], request.form["place"], job_id, get_user_id()))
        conn.commit()
        conn.close()
        return redirect("/parttime")
    return render_template("edit_parttime.html", item=get_parttime_job_by_id(job_id), t=t)

@app.route("/parttime/delete/<int:job_id>")
def delete_parttime(job_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM parttime_jobs WHERE id = ? AND user_id = ?", (job_id, get_user_id()))
    conn.commit()
    conn.close()
    return redirect("/parttime")

# --- Notification ---
@app.route("/notification")
def notification():
    lang = session.get("lang", "ja")
    t = TRANSLATIONS[lang]
    return render_template("notification.html", notifications=get_notifications(), t=t)

@app.route("/notification/add", methods=["GET", "POST"])
def add_notification():
    lang = session.get("lang", "ja")
    t = TRANSLATIONS[lang]
    if request.method == "POST":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO notifications (type, message, time, user_id) VALUES (?, ?, ?, ?)",
            (request.form["type"], request.form["message"], request.form["time"], get_user_id()))
        conn.commit()
        conn.close()
        return redirect("/notification")
    return render_template("add_notification.html", t=t)

@app.route("/notification/delete/<int:notification_id>")
def delete_notification(notification_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notifications WHERE id = ? AND user_id = ?", (notification_id, get_user_id()))
    conn.commit()
    conn.close()
    return redirect("/notification")

# --- Calendar ---
@app.route("/calendar")
def calendar_view():
    today = date.today()
    year = int(request.args.get("year", today.year))
    month = int(request.args.get("month", today.month))
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1
    cal = calendar.monthcalendar(year, month)
    uid = get_user_id()
    conn = get_db_connection()
    cursor = conn.cursor()
    month_str = f"{year}-{month:02d}"
    cursor.execute("SELECT deadline, task, subject FROM homeworks WHERE deadline LIKE ? AND user_id = ?", (f"{month_str}%", uid))
    homework_rows = cursor.fetchall()
    cursor.execute("SELECT * FROM parttime_jobs WHERE user_id = ?", (uid,))
    parttime_rows = cursor.fetchall()
    conn.close()
    events = {}
    for row in homework_rows:
        parts = row["deadline"].split("-")
        if len(parts) == 3 and parts[2].isdigit():
            d = int(parts[2])
            if d not in events:
                events[d] = []
            events[d].append({"type": "homework", "text": f"📝{row['subject']}"})
    for row in parttime_rows:
        try:
            parts = row["date"].split(" ")[0].split("/")
            if len(parts) == 2:
                p_month, p_day = int(parts[0]), int(parts[1])
                if p_month == month:
                    if p_day not in events:
                        events[p_day] = []
                    events[p_day].append({"type": "parttime", "text": f"💼{row['place']}"})
        except:
            pass
    lang = session.get("lang", "ja")
    t = TRANSLATIONS[lang]
    return render_template("calendar.html", year=year, month=month, cal=cal, events=events, today=today,
        prev_year=prev_year, prev_month=prev_month, next_year=next_year, next_month=next_month, t=t)

# --- Dashboard ---
@app.route("/dashboard")
def dashboard():
    today = date.today()
    today_str = today.isoformat()
    today_display = f"{today.year}年{today.month}月{today.day}日"
    uid = get_user_id()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM homeworks WHERE done = 0 AND user_id = ?", (uid,))
    homework_undone = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM homeworks WHERE done = 0 AND deadline < ? AND user_id = ?", (today_str, uid))
    homework_overdue = cursor.fetchone()[0]
    cursor.execute("SELECT * FROM schedules WHERE user_id = ? ORDER BY time", (uid,))
    schedules = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT 3", (uid,))
    recent_notifications = [dict(row) for row in cursor.fetchall()]
    parttime_count = 0
    total_hours = 0
    cursor.execute("SELECT start, end FROM parttime_jobs WHERE user_id = ?", (uid,))
    for row in cursor.fetchall():
        try:
            start_h, start_m = map(int, row["start"].split(":"))
            end_h, end_m = map(int, row["end"].split(":"))
            hours = (end_h * 60 + end_m - start_h * 60 - start_m) / 60
            total_hours += hours
            parttime_count += 1
        except:
            pass
    conn.close()
    lang = session.get("lang", "ja")
    t = TRANSLATIONS[lang]
    return render_template("dashboard.html", today_display=today_display, homework_undone=homework_undone,
        homework_overdue=homework_overdue, schedules=schedules, recent_notifications=recent_notifications,
        parttime_count=parttime_count, total_hours=round(total_hours, 1), t=t)

# --- Graph ---
@app.route("/graph")
def graph():
    today = date.today().isoformat()
    uid = get_user_id()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM homeworks WHERE done = 1 AND user_id = ?", (uid,))
    homework_done = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM homeworks WHERE done = 0 AND deadline >= ? AND user_id = ?", (today, uid))
    homework_undone = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM homeworks WHERE done = 0 AND deadline < ? AND user_id = ?", (today, uid))
    homework_overdue = cursor.fetchone()[0]
    cursor.execute("SELECT date, start, end, place FROM parttime_jobs WHERE user_id = ? ORDER BY date", (uid,))
    parttime_rows = cursor.fetchall()
    conn.close()
    parttime_labels = []
    parttime_hours = []
    total_hours = 0
    for row in parttime_rows:
        try:
            start_h, start_m = map(int, row["start"].split(":"))
            end_h, end_m = map(int, row["end"].split(":"))
            hours = round((end_h * 60 + end_m - start_h * 60 - start_m) / 60, 1)
            parttime_labels.append(f"{row['date']} {row['place']}")
            parttime_hours.append(hours)
            total_hours += hours
        except:
            pass
    lang = session.get("lang", "ja")
    t = TRANSLATIONS[lang]
    return render_template("graph.html", homework_done=homework_done, homework_undone=homework_undone,
        homework_overdue=homework_overdue, parttime_labels=parttime_labels, parttime_hours=parttime_hours,
        total_hours=round(total_hours, 1), t=t)

# --- AI提案 ---
@app.route("/ai")
def ai():
    from datetime import timedelta
    today = date.today()
    today_str = today.isoformat()
    uid = get_user_id()
    suggestions = []
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM homeworks WHERE done = 0 AND deadline < ? AND user_id = ?", (today_str, uid))
    overdue_count = cursor.fetchone()[0]
    if overdue_count > 0:
        suggestions.append({"level": "danger", "icon": "⚠️", "message": f"期限切れの宿題が{overdue_count}件あります。早急に対応しましょう。"})
    three_days_later = (today + timedelta(days=3)).isoformat()
    cursor.execute("SELECT subject, task, deadline FROM homeworks WHERE done = 0 AND deadline >= ? AND deadline <= ? AND user_id = ?",
        (today_str, three_days_later, uid))
    for hw in cursor.fetchall():
        deadline_date = date.fromisoformat(hw["deadline"])
        days_left = (deadline_date - today).days
        if days_left == 0:
            msg = f"「{hw['subject']} / {hw['task']}」の締め切りは今日です！"
        elif days_left == 1:
            msg = f"「{hw['subject']} / {hw['task']}」の締め切りは明日です！"
        else:
            msg = f"「{hw['subject']} / {hw['task']}」の締め切りまであと{days_left}日です。"
        suggestions.append({"level": "warning", "icon": "📝", "message": msg})
    cursor.execute("SELECT COUNT(*) FROM homeworks WHERE done = 0 AND user_id = ?", (uid,))
    undone_count = cursor.fetchone()[0]
    if undone_count >= 3:
        suggestions.append({"level": "warning", "icon": "📚", "message": f"未完了の宿題が{undone_count}件あります。優先順位をつけて取り組みましょう。"})
    total_hours = 0
    cursor.execute("SELECT start, end FROM parttime_jobs WHERE user_id = ?", (uid,))
    for row in cursor.fetchall():
        try:
            start_h, start_m = map(int, row["start"].split(":"))
            end_h, end_m = map(int, row["end"].split(":"))
            total_hours += (end_h * 60 + end_m - start_h * 60 - start_m) / 60
        except:
            pass
    if total_hours >= 20:
        suggestions.append({"level": "warning", "icon": "💼", "message": f"アルバイトの合計時間が{round(total_hours, 1)}時間あります。勉強時間もしっかり確保しましょう。"})
    elif total_hours > 0:
        suggestions.append({"level": "info", "icon": "💼", "message": f"今週のアルバイトは{round(total_hours, 1)}時間です。バランスよく勉強も進めましょう。"})
    conn.close()
    if not suggestions:
        suggestions.append({"level": "success", "icon": "✅", "message": "今のところ問題はありません。この調子で頑張りましょう！"})
    lang = session.get("lang", "ja")
    t = TRANSLATIONS[lang]
    return render_template("ai.html", suggestions=suggestions, t=t)

# --- 履歴書 ---
@app.route("/resume", methods=["GET", "POST"])
def resume():
    if request.method == "POST":
        data = {k: request.form.get(k, "") for k in ["name", "name_kana", "birthday", "gender", "address", "phone", "email", "education", "work", "motivation", "skills", "pr"]}
        session["resume_data"] = data
        return render_template("resume_preview.html", data=data)
    data = session.get("resume_data", {})
    return render_template("resume_form.html", data=data)

@app.route("/resume/blank")
def resume_blank():
    return render_template("resume_preview.html", data={})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
