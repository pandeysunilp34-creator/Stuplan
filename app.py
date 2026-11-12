from flask import Flask, render_template, request, redirect, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import json
from datetime import date
import calendar
from translations import TRANSLATIONS

VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "BM9aWYi531OzMEIxdcb_AO4rXbPm-jl8jOiB9mLTaRNsmt2Dg-xMnPRCz8dV5OMG4OWE5-A0DmKCVJ-ebLkKDr8")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQghwa-QIN7hzG-P-HRG8Op7B4aESMiY2BxFmjc2os_fkahRANCAATPWlmIud9TszBCMXXG_wDuK12z5vo5fIzogfZi02kTbJrdg4PsTJz0Qs_HVeTjBuDlhOfgNA5iglSfnmy5Cg6_")
VAPID_CLAIMS = {"sub": "mailto:stuplan@example.com"}
app = Flask(__name__)
app.secret_key = "stuplan_secret_key_2026"

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if DATABASE_URL:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        return conn
    else:
        conn = sqlite3.connect("stuplan.db")
        conn.row_factory = sqlite3.Row
        return conn

def ph(n=1):
    if DATABASE_URL:
        return ",".join(["%s"] * n) if n > 1 else "%s"
    else:
        return ",".join(["?"] * n) if n > 1 else "?"

def fetchall_as_dict(cursor):
    if DATABASE_URL:
        cols = [desc[0] for desc in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    else:
        return [dict(row) for row in cursor.fetchall()]

def fetchone_as_dict(cursor):
    if DATABASE_URL:
        cols = [desc[0] for desc in cursor.description]
        row = cursor.fetchone()
        return dict(zip(cols, row)) if row else None
    else:
        row = cursor.fetchone()
        return dict(row) if row else None

def init_db():
    if not DATABASE_URL:
        return
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT NOT NULL UNIQUE, password TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cursor.execute("""ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS schedules (id SERIAL PRIMARY KEY, time TEXT NOT NULL, title TEXT NOT NULL, place TEXT NOT NULL, user_id INTEGER DEFAULT 1)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS homeworks (id SERIAL PRIMARY KEY, subject TEXT NOT NULL, task TEXT NOT NULL, deadline TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0, user_id INTEGER DEFAULT 1)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS parttime_jobs (id SERIAL PRIMARY KEY, date TEXT NOT NULL, start TEXT NOT NULL, "end" TEXT NOT NULL, place TEXT NOT NULL, user_id INTEGER DEFAULT 1)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS push_subscriptions (id SERIAL PRIMARY KEY, user_id INTEGER, subscription TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS notifications (id SERIAL PRIMARY KEY, type TEXT NOT NULL, message TEXT NOT NULL, time TEXT NOT NULL, user_id INTEGER DEFAULT 1)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS job_places (id SERIAL PRIMARY KEY, name TEXT NOT NULL, hourly_wage INTEGER NOT NULL DEFAULT 1000, late_night_wage INTEGER NOT NULL DEFAULT 1250, user_id INTEGER DEFAULT 1)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS job_shifts (id SERIAL PRIMARY KEY, job_place_id INTEGER NOT NULL, date TEXT NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL, memo TEXT DEFAULT '', user_id INTEGER DEFAULT 1)""")
        conn.commit()
        conn.close()
        print("PostgreSQLテーブル作成完了")
    except Exception as e:
        print(f"テーブル作成エラー: {e}")

init_db()

def get_user_id():
    return session.get("user_id", 1)

def get_schedules(keyword=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    uid = get_user_id()
    p = ph()
    if keyword:
        kw = f"%{keyword}%"
        cursor.execute(f"SELECT * FROM schedules WHERE user_id = {p} AND (title LIKE {p} OR place LIKE {p}) ORDER BY time", (uid, kw, kw))
    else:
        cursor.execute(f"SELECT * FROM schedules WHERE user_id = {p} ORDER BY time", (uid,))
    rows = fetchall_as_dict(cursor)
    conn.close()
    return rows

def get_schedule_by_id(schedule_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    p = ph()
    cursor.execute(f"SELECT * FROM schedules WHERE id = {p} AND user_id = {p}", (schedule_id, get_user_id()))
    row = fetchone_as_dict(cursor)
    conn.close()
    return row

def get_homeworks():
    conn = get_db_connection()
    cursor = conn.cursor()
    p = ph()
    cursor.execute(f"SELECT * FROM homeworks WHERE user_id = {p} ORDER BY deadline", (get_user_id(),))
    rows = fetchall_as_dict(cursor)
    conn.close()
    today = date.today().isoformat()
    result = []
    for item in rows:
        item["overdue"] = (item["deadline"] < today) and not item["done"]
        result.append(item)
    return result

def get_homework_by_id(homework_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    p = ph()
    cursor.execute(f"SELECT * FROM homeworks WHERE id = {p} AND user_id = {p}", (homework_id, get_user_id()))
    row = fetchone_as_dict(cursor)
    conn.close()
    return row

def get_parttime_jobs():
    conn = get_db_connection()
    cursor = conn.cursor()
    p = ph()
    cursor.execute(f'SELECT * FROM parttime_jobs WHERE user_id = {p} ORDER BY date', (get_user_id(),))
    rows = fetchall_as_dict(cursor)
    conn.close()
    return rows

def get_parttime_job_by_id(job_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    p = ph()
    cursor.execute(f'SELECT * FROM parttime_jobs WHERE id = {p} AND user_id = {p}', (job_id, get_user_id()))
    row = fetchone_as_dict(cursor)
    conn.close()
    return row

def get_notifications():
    conn = get_db_connection()
    cursor = conn.cursor()
    p = ph()
    cursor.execute(f"SELECT * FROM notifications WHERE user_id = {p} ORDER BY id DESC", (get_user_id(),))
    rows = fetchall_as_dict(cursor)
    conn.close()
    return rows

def calc_pay(start_str, end_str, hourly_wage, late_night_wage):
    try:
        sh, sm = map(int, start_str.split(":"))
        eh, em = map(int, end_str.split(":"))
        start_min = sh * 60 + sm
        end_min = eh * 60 + em
        if end_min <= start_min:
            end_min += 24 * 60
        total_pay = 0
        for m in range(start_min, end_min):
            hour = (m // 60) % 24
            if hour >= 22 or hour < 5:
                total_pay += late_night_wage / 60
            else:
                total_pay += hourly_wage / 60
        total_hours = (end_min - start_min) / 60
        return round(total_pay), round(total_hours, 2)
    except:
        return 0, 0

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

@app.route("/login", methods=["GET", "POST"])
def login():
    lang = session.get("lang", "ja")
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db_connection()
        cursor = conn.cursor()
        p = ph()
        cursor.execute(f"SELECT * FROM users WHERE username = {p}", (username,))
        user = fetchone_as_dict(cursor)
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/home")
        else:
            error = {"ja": "ユーザー名またはパスワードが違います", "en": "Incorrect username or password", "np": "प्रयोगकर्ता नाम वा पासवर्ड गलत छ"}.get(lang)
            return render_template("login.html", error=error, lang=lang)
    return render_template("login.html", lang=lang)

@app.route("/register", methods=["GET", "POST"])
def register():
    lang = session.get("lang", "ja")
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        p = ph()
        try:
            cursor.execute(f"INSERT INTO users (username, password) VALUES ({p}, {p})", (username, hashed))
            conn.commit()
            conn.close()
            return redirect("/login")
        except Exception:
            conn.close()
            error = {"ja": "そのユーザー名はすでに使われています", "en": "Username already taken", "np": "त्यो प्रयोगकर्ता नाम पहिले नै प्रयोग भइसकेको छ"}.get(lang)
            return render_template("register.html", error=error, lang=lang)
    return render_template("register.html", lang=lang)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/home")
def home():
    lang = session.get("lang", "ja")
    t = TRANSLATIONS.get(lang, TRANSLATIONS["ja"])
    schedule_count = len(get_schedules())
    homework_count = sum(1 for h in get_homeworks() if not h["done"])
    parttime_count = len(get_parttime_jobs())
    notification_count = len(get_notifications())
    return render_template("home.html", lang=lang, t=t,
                           schedule_count=schedule_count,
                           homework_count=homework_count,
                           parttime_count=parttime_count,
                           notification_count=notification_count)

@app.route("/schedule")
def schedule():
    lang = session.get("lang", "ja")
    t = TRANSLATIONS.get(lang, TRANSLATIONS["ja"])
    keyword = request.args.get("q", "")
    schedules = get_schedules(keyword if keyword else None)
    return render_template("schedule.html", schedules=schedules, lang=lang, t=t, keyword=keyword)

@app.route("/schedule/add", methods=["GET", "POST"])
def add_schedule():
    lang = session.get("lang", "ja")
    t = TRANSLATIONS.get(lang, TRANSLATIONS["ja"])
    if request.method == "POST":
        time = request.form["time"]
        title = request.form["title"]
        place = request.form["place"]
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"INSERT INTO schedules (time, title, place, user_id) VALUES ({ph(4)})", (time, title, place, get_user_id()))
        conn.commit()
        conn.close()
        return redirect("/schedule")
    return render_template("add_schedule.html", lang=lang, t=t)

@app.route("/schedule/edit/<int:schedule_id>", methods=["GET", "POST"])
def edit_schedule(schedule_id):
    lang = session.get("lang", "ja")
    t = TRANSLATIONS.get(lang, TRANSLATIONS["ja"])
    schedule = get_schedule_by_id(schedule_id)
    if not schedule:
        return redirect("/schedule")
    if request.method == "POST":
        time = request.form["time"]
        title = request.form["title"]
        place = request.form["place"]
        conn = get_db_connection()
        cursor = conn.cursor()
        p = ph()
        cursor.execute(f"UPDATE schedules SET time={p}, title={p}, place={p} WHERE id={p} AND user_id={p}", (time, title, place, schedule_id, get_user_id()))
        conn.commit()
        conn.close()
        return redirect("/schedule")
    return render_template("edit_schedule.html", schedule=schedule, lang=lang, t=t)

@app.route("/schedule/delete/<int:schedule_id>")
def delete_schedule(schedule_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    p = ph()
    cursor.execute(f"DELETE FROM schedules WHERE id={p} AND user_id={p}", (schedule_id, get_user_id()))
    conn.commit()
    conn.close()
    return redirect("/schedule")

@app.route("/homework")
def homework():
    lang = session.get("lang", "ja")
    t = TRANSLATIONS.get(lang, TRANSLATIONS["ja"])
    homeworks = get_homeworks()
    return render_template("homework.html", homeworks=homeworks, lang=lang, t=t)

@app.route("/homework/add", methods=["GET", "POST"])
def add_homework():
    lang = session.get("lang", "ja")
    t = TRANSLATIONS.get(lang, TRANSLATIONS["ja"])
    if request.method == "POST":
        subject = request.form["subject"]
        task = request.form["task"]
        deadline = request.form["deadline"]
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"INSERT INTO homeworks (subject, task, deadline, user_id) VALUES ({ph(4)})", (subject, task, deadline, get_user_id()))
        conn.commit()
        conn.close()
        return redirect("/homework")
    return render_template("add_homework.html", lang=lang, t=t)

@app.route("/homework/edit/<int:homework_id>", methods=["GET", "POST"])
def edit_homework(homework_id):
    lang = session.get("lang", "ja")
    t = TRANSLATIONS.get(lang, TRANSLATIONS["ja"])
    homework = get_homework_by_id(homework_id)
    if not homework:
        return redirect("/homework")
    if request.method == "POST":
        subject = request.form["subject"]
        task = request.form["task"]
        deadline = request.form["deadline"]
        conn = get_db_connection()
        cursor = conn.cursor()
        p = ph()
        cursor.execute(f"UPDATE homeworks SET subject={p}, task={p}, deadline={p} WHERE id={p} AND user_id={p}", (subject, task, deadline, homework_id, get_user_id()))
        conn.commit()
        conn.close()
        return redirect("/homework")
    return render_template("edit_homework.html", homework=homework, lang=lang, t=t)

@app.route("/homework/toggle/<int:homework_id>")
def toggle_homework(homework_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    p = ph()
    cursor.execute(f"SELECT done FROM homeworks WHERE id={p} AND user_id={p}", (homework_id, get_user_id()))
    row = fetchone_as_dict(cursor)
    if row:
        new_done = 0 if row["done"] else 1
        cursor.execute(f"UPDATE homeworks SET done={p} WHERE id={p} AND user_id={p}", (new_done, homework_id, get_user_id()))
        conn.commit()
    conn.close()
    return redirect("/homework")

@app.route("/homework/delete/<int:homework_id>")
def delete_homework(homework_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    p = ph()
    cursor.execute(f"DELETE FROM homeworks WHERE id={p} AND user_id={p}", (homework_id, get_user_id()))
    conn.commit()
    conn.close()
    return redirect("/homework")

@app.route("/parttime")
def parttime():
    lang = session.get("lang", "ja")
    t = TRANSLATIONS.get(lang, TRANSLATIONS["ja"])
    parttime_jobs = get_parttime_jobs()
    return render_template("parttime.html", parttime_jobs=parttime_jobs, lang=lang, t=t)

@app.route("/parttime/add", methods=["GET", "POST"])
def add_parttime():
    lang = session.get("lang", "ja")
    t = TRANSLATIONS.get(lang, TRANSLATIONS["ja"])
    if request.method == "POST":
        date_val = request.form["date"]
        start = request.form["start"]
        end = request.form["end"]
        place = request.form["place"]
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f'INSERT INTO parttime_jobs (date, start, "end", place, user_id) VALUES ({ph(5)})', (date_val, start, end, place, get_user_id()))
        conn.commit()
        conn.close()
        return redirect("/parttime")
    return render_template("add_parttime.html", lang=lang, t=t)

@app.route("/parttime/edit/<int:job_id>", methods=["GET", "POST"])
def edit_parttime(job_id):
    lang = session.get("lang", "ja")
    t = TRANSLATIONS.get(lang, TRANSLATIONS["ja"])
    job = get_parttime_job_by_id(job_id)
    if not job:
        return redirect("/parttime")
    if request.method == "POST":
        date_val = request.form["date"]
        start = request.form["start"]
        end = request.form["end"]
        place = request.form["place"]
        conn = get_db_connection()
        cursor = conn.cursor()
        p = ph()
        cursor.execute(f'UPDATE parttime_jobs SET date={p}, start={p}, "end"={p}, place={p} WHERE id={p} AND user_id={p}', (date_val, start, end, place, job_id, get_user_id()))
        conn.commit()
        conn.close()
        return redirect("/parttime")
    return render_template("edit_parttime.html", job=job, lang=lang, t=t)

@app.route("/parttime/delete/<int:job_id>")
def delete_parttime(job_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    p = ph()
    cursor.execute(f'DELETE FROM parttime_jobs WHERE id={p} AND user_id={p}', (job_id, get_user_id()))
    conn.commit()
    conn.close()
    return redirect("/parttime")

@app.route("/jobs")
def jobs():
    conn = get_db_connection()
    cursor = conn.cursor()
    p = ph()
    cursor.execute(f"SELECT * FROM job_places WHERE user_id={p} ORDER BY id", (get_user_id(),))
    places = fetchall_as_dict(cursor)
    conn.close()
    return render_template("jobs.html", places=places)

@app.route("/jobs/add", methods=["GET", "POST"])
def add_job_place():
    if request.method == "POST":
        name = request.form["name"]
        hourly_wage = int(request.form["hourly_wage"])
        late_night_wage = int(request.form["late_night_wage"])
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"INSERT INTO job_places (name, hourly_wage, late_night_wage, user_id) VALUES ({ph(4)})", (name, hourly_wage, late_night_wage, get_user_id()))
        conn.commit()
        conn.close()
        return redirect("/jobs")
    return render_template("add_job_place.html")

@app.route("/jobs/edit/<int:place_id>", methods=["GET", "POST"])
def edit_job_place(place_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    p = ph()
    cursor.execute(f"SELECT * FROM job_places WHERE id={p} AND user_id={p}", (place_id, get_user_id()))
    place = fetchone_as_dict(cursor)
    conn.close()
    if not place:
        return redirect("/jobs")
    if request.method == "POST":
        name = request.form["name"]
        hourly_wage = int(request.form["hourly_wage"])
        late_night_wage = int(request.form["late_night_wage"])
        conn = get_db_connection()
        cursor = conn.cursor()
        p = ph()
        cursor.execute(f"UPDATE job_places SET name={p}, hourly_wage={p}, late_night_wage={p} WHERE id={p} AND user_id={p}", (name, hourly_wage, late_night_wage, place_id, get_user_id()))
        conn.commit()
        conn.close()
        return redirect("/jobs")
    return render_template("edit_job_place.html", place=place)

@app.route("/jobs/delete/<int:place_id>")
def delete_job_place(place_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    p = ph()
    cursor.execute(f"DELETE FROM job_shifts WHERE job_place_id={p} AND user_id={p}", (place_id, get_user_id()))
    cursor.execute(f"DELETE FROM job_places WHERE id={p} AND user_id={p}", (place_id, get_user_id()))
    conn.commit()
    conn.close()
    return redirect("/jobs")

@app.route("/jobs/<int:place_id>/shifts")
def job_shifts(place_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    p = ph()
    cursor.execute(f"SELECT * FROM job_places WHERE id={p} AND user_id={p}", (place_id, get_user_id()))
    place = fetchone_as_dict(cursor)
    if not place:
        conn.close()
        return redirect("/jobs")
    month_filter = request.args.get("month", "")
    if month_filter:
        cursor.execute(f"SELECT * FROM job_shifts WHERE job_place_id={p} AND user_id={p} AND date LIKE {p} ORDER BY date DESC", (place_id, get_user_id(), f"{month_filter}%"))
    else:
        cursor.execute(f"SELECT * FROM job_shifts WHERE job_place_id={p} AND user_id={p} ORDER BY date DESC", (place_id, get_user_id()))
    raw_shifts = fetchall_as_dict(cursor)
    cursor.execute(f"SELECT DISTINCT LEFT(date,7) as ym FROM job_shifts WHERE job_place_id={p} AND user_id={p} ORDER BY ym DESC", (place_id, get_user_id()))
    month_rows = fetchall_as_dict(cursor)
    conn.close()
    months = [r["ym"] for r in month_rows]
    shifts = []
    total_pay = 0
    total_hours = 0
    for s in raw_shifts:
        pay, hours = calc_pay(s["start_time"], s["end_time"], place["hourly_wage"], place["late_night_wage"])
        s["pay"] = pay
        s["hours"] = hours
        total_pay += pay
        total_hours += hours
        shifts.append(s)
    return render_template("job_shifts.html", place=place, shifts=shifts, months=months, current_month=month_filter, total_pay=total_pay, total_hours=round(total_hours, 2))

@app.route("/jobs/<int:place_id>/shifts/add", methods=["GET", "POST"])
def add_job_shift(place_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    p = ph()
    cursor.execute(f"SELECT * FROM job_places WHERE id={p} AND user_id={p}", (place_id, get_user_id()))
    place = fetchone_as_dict(cursor)
    conn.close()
    if not place:
        return redirect("/jobs")
    if request.method == "POST":
        date_val = request.form["date"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]
        memo = request.form.get("memo", "")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"INSERT INTO job_shifts (job_place_id, date, start_time, end_time, memo, user_id) VALUES ({ph(6)})", (place_id, date_val, start_time, end_time, memo, get_user_id()))
        conn.commit()
        conn.close()
        return redirect(f"/jobs/{place_id}/shifts")
    return render_template("add_job_shift.html", place=place)

@app.route("/jobs/<int:place_id>/shifts/delete/<int:shift_id>")
def delete_job_shift(place_id, shift_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    p = ph()
    cursor.execute(f"DELETE FROM job_shifts WHERE id={p} AND user_id={p}", (shift_id, get_user_id()))
    conn.commit()
    conn.close()
    return redirect(f"/jobs/{place_id}/shifts")

@app.route("/salary")
def salary():
    conn = get_db_connection()
    cursor = conn.cursor()
    p = ph()
    cursor.execute(f"SELECT * FROM job_places WHERE user_id={p}", (get_user_id(),))
    places = fetchall_as_dict(cursor)
    place_map = {pl["id"]: pl for pl in places}
    cursor.execute(f"SELECT * FROM job_shifts WHERE user_id={p} ORDER BY date DESC", (get_user_id(),))
    all_shifts = fetchall_as_dict(cursor)
    conn.close()
    grand_total_pay = 0
    grand_total_hours = 0
    place_totals = {}
    monthly = {}
    for s in all_shifts:
        pl = place_map.get(s["job_place_id"])
        if not pl:
            continue
        pay, hours = calc_pay(s["start_time"], s["end_time"], pl["hourly_wage"], pl["late_night_wage"])
        s["pay"] = pay
        s["hours"] = hours
        s["place_name"] = pl["name"]
        grand_total_pay += pay
        grand_total_hours += hours
        pname = pl["name"]
        if pname not in place_totals:
            place_totals[pname] = {"total_pay": 0, "total_hours": 0}
        place_totals[pname]["total_pay"] += pay
        place_totals[pname]["total_hours"] = round(place_totals[pname]["total_hours"] + hours, 2)
        ym = s["date"][:7]
        if ym not in monthly:
            monthly[ym] = {"total_pay": 0, "total_hours": 0, "shifts": []}
        monthly[ym]["total_pay"] += pay
        monthly[ym]["total_hours"] = round(monthly[ym]["total_hours"] + hours, 2)
        monthly[ym]["shifts"].append(s)
    sorted_months = sorted(monthly.keys(), reverse=True)
    return render_template("salary.html", grand_total_pay=grand_total_pay, grand_total_hours=round(grand_total_hours, 2), place_totals=place_totals, monthly=monthly, sorted_months=sorted_months)
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
        cursor.execute(f"INSERT INTO notifications (type, message, time, user_id) VALUES ({ph(4)})", (request.form["type"], request.form["message"], request.form["time"], get_user_id()))
        conn.commit()
        conn.close()
        return redirect("/notification")
    return render_template("add_notification.html", t=t)

@app.route("/notification/delete/<int:notification_id>")
def delete_notification(notification_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    p = ph()
    cursor.execute(f"DELETE FROM notifications WHERE id = {p} AND user_id = {p}", (notification_id, get_user_id()))
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
    p = ph()
    conn = get_db_connection()
    cursor = conn.cursor()
    month_str = f"{year}-{month:02d}"
    cursor.execute(f"SELECT deadline, task, subject FROM homeworks WHERE deadline LIKE {ph()} AND user_id = {p}", (f"{month_str}%", uid))
    homework_rows = fetchall_as_dict(cursor)
    cursor.execute(f"SELECT * FROM parttime_jobs WHERE user_id = {p}", (uid,))
    parttime_rows = fetchall_as_dict(cursor)
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
    return render_template("calendar.html", year=year, month=month, cal=cal, events=events, today=today, prev_year=prev_year, prev_month=prev_month, next_year=next_year, next_month=next_month, t=t)

# --- Dashboard ---
@app.route("/dashboard")
def dashboard():
    today = date.today()
    today_str = today.isoformat()
    today_display = f"{today.year}年{today.month}月{today.day}日"
    uid = get_user_id()
    p = ph()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM homeworks WHERE done = 0 AND user_id = {p}", (uid,))
    homework_undone = cursor.fetchone()[0]
    cursor.execute(f"SELECT COUNT(*) FROM homeworks WHERE done = 0 AND deadline < {p} AND user_id = {p}", (today_str, uid))
    homework_overdue = cursor.fetchone()[0]
    cursor.execute(f"SELECT * FROM schedules WHERE user_id = {p} AND time LIKE {ph()} ORDER BY time", (uid, f"{today_str}%"))
    schedules = fetchall_as_dict(cursor)
    from datetime import timedelta
    week_later = (today + timedelta(days=7)).isoformat()
    cursor.execute(f"SELECT * FROM homeworks WHERE done = 0 AND deadline >= {p} AND deadline <= {p} AND user_id = {p} ORDER BY deadline LIMIT 5", (today_str, week_later, uid))
    upcoming_homeworks = fetchall_as_dict(cursor)
    cursor.execute(f"SELECT * FROM notifications WHERE user_id = {p} ORDER BY id DESC LIMIT 3", (uid,))
    recent_notifications = fetchall_as_dict(cursor)
    parttime_count = 0
    total_hours = 0
    cursor.execute(f'SELECT start, "end" FROM parttime_jobs WHERE user_id = {p}', (uid,))
    for row in cursor.fetchall():
        try:
            start_h, start_m = map(int, row[0].split(":"))
            end_h, end_m = map(int, row[1].split(":"))
            hours = (end_h * 60 + end_m - start_h * 60 - start_m) / 60
            total_hours += hours
            parttime_count += 1
        except:
            pass
    conn.close()
    lang = session.get("lang", "ja")
    t = TRANSLATIONS[lang]
    return render_template("dashboard.html", today_display=today_display, homework_undone=homework_undone, homework_overdue=homework_overdue, schedules=schedules, upcoming_homeworks=upcoming_homeworks, recent_notifications=recent_notifications, parttime_count=parttime_count, total_hours=round(total_hours, 1), t=t)


@app.route("/push/vapid-key")
def vapid_key():
    return jsonify({"publicKey": VAPID_PUBLIC_KEY})

@app.route("/push/subscribe", methods=["POST"])
def push_subscribe():
    if "user_id" not in session:
        return jsonify({"error": "not logged in"}), 401
    sub = request.get_json()
    uid = get_user_id()
    conn = get_db_connection()
    cursor = conn.cursor()
    p = ph()
    cursor.execute(f"INSERT INTO push_subscriptions (user_id, subscription) VALUES ({p}, {p})", (uid, json.dumps(sub)))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

# --- Graph ---
@app.route("/graph")
def graph():
    today = date.today().isoformat()
    uid = get_user_id()
    p = ph()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM homeworks WHERE done = 1 AND user_id = {p}", (uid,))
    homework_done = cursor.fetchone()[0]
    cursor.execute(f"SELECT COUNT(*) FROM homeworks WHERE done = 0 AND deadline >= {p} AND user_id = {p}", (today, uid))
    homework_undone = cursor.fetchone()[0]
    cursor.execute(f"SELECT COUNT(*) FROM homeworks WHERE done = 0 AND deadline < {p} AND user_id = {p}", (today, uid))
    homework_overdue = cursor.fetchone()[0]
    cursor.execute(f'SELECT date, start, "end", place FROM parttime_jobs WHERE user_id = {p} ORDER BY date', (uid,))
    parttime_rows = cursor.fetchall()
    conn.close()
    parttime_labels = []
    parttime_hours = []
    total_hours = 0
    for row in parttime_rows:
        try:
            start_h, start_m = map(int, row[1].split(":"))
            end_h, end_m = map(int, row[2].split(":"))
            hours = round((end_h * 60 + end_m - start_h * 60 - start_m) / 60, 1)
            parttime_labels.append(f"{row[0]} {row[3]}")
            parttime_hours.append(hours)
            total_hours += hours
        except:
            pass
    lang = session.get("lang", "ja")
    t = TRANSLATIONS[lang]
    return render_template("graph.html", homework_done=homework_done, homework_undone=homework_undone, homework_overdue=homework_overdue, parttime_labels=parttime_labels, parttime_hours=parttime_hours, total_hours=round(total_hours, 1), t=t)

# --- AI提案 ---
@app.route("/ai")
def ai():
    from datetime import timedelta
    today = date.today()
    today_str = today.isoformat()
    uid = get_user_id()
    p = ph()
    suggestions = []
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM homeworks WHERE done = 0 AND deadline < {p} AND user_id = {p}", (today_str, uid))
    overdue_count = cursor.fetchone()[0]
    if overdue_count > 0:
        suggestions.append({"level": "danger", "icon": "⚠️", "message": f"期限切れの宿題が{overdue_count}件あります。早急に対応しましょう。"})
    three_days_later = (today + timedelta(days=3)).isoformat()
    cursor.execute(f"SELECT subject, task, deadline FROM homeworks WHERE done = 0 AND deadline >= {p} AND deadline <= {p} AND user_id = {p}", (today_str, three_days_later, uid))
    for hw in fetchall_as_dict(cursor):
        deadline_date = date.fromisoformat(hw["deadline"])
        days_left = (deadline_date - today).days
        if days_left == 0:
            msg = f"「{hw['subject']} / {hw['task']}」の締め切りは今日です！"
        elif days_left == 1:
            msg = f"「{hw['subject']} / {hw['task']}」の締め切りは明日です！"
        else:
            msg = f"「{hw['subject']} / {hw['task']}」の締め切りまであと{days_left}日です。"
        suggestions.append({"level": "warning", "icon": "📝", "message": msg})
    cursor.execute(f"SELECT COUNT(*) FROM homeworks WHERE done = 0 AND user_id = {p}", (uid,))
    undone_count = cursor.fetchone()[0]
    if undone_count >= 3:
        suggestions.append({"level": "warning", "icon": "📚", "message": f"未完了の宿題が{undone_count}件あります。優先順位をつけて取り組みましょう。"})
    total_hours = 0
    cursor.execute(f'SELECT start, "end" FROM parttime_jobs WHERE user_id = {p}', (uid,))
    for row in cursor.fetchall():
        try:
            start_h, start_m = map(int, row[0].split(":"))
            end_h, end_m = map(int, row[1].split(":"))
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


# --- プロフィール ---
@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect("/login")
    uid = get_user_id()
    p = ph()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE id = {p}", (uid,))
    user = fetchone_as_dict(cursor)
    cursor.execute(f"SELECT COUNT(*) FROM schedules WHERE user_id = {p}", (uid,))
    schedule_count = cursor.fetchone()[0]
    cursor.execute(f"SELECT COUNT(*) FROM homeworks WHERE user_id = {p}", (uid,))
    homework_count = cursor.fetchone()[0]
    cursor.execute(f"SELECT COUNT(*) FROM parttime_jobs WHERE user_id = {p}", (uid,))
    parttime_count = cursor.fetchone()[0]
    conn.close()
    lang = session.get("lang", "ja")
    return render_template("profile.html", user=user, schedule_count=schedule_count, homework_count=homework_count, parttime_count=parttime_count, lang=lang, pw_error=None, pw_success=None)

@app.route("/profile/change_password", methods=["POST"])
def change_password():
    if "user_id" not in session:
        return redirect("/login")
    uid = get_user_id()
    lang = session.get("lang", "ja")
    current_password = request.form["current_password"]
    new_password = request.form["new_password"]
    new_password_confirm = request.form["new_password_confirm"]
    p = ph()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE id = {p}", (uid,))
    user = fetchone_as_dict(cursor)
    cursor.execute(f"SELECT COUNT(*) FROM schedules WHERE user_id = {p}", (uid,))
    schedule_count = cursor.fetchone()[0]
    cursor.execute(f"SELECT COUNT(*) FROM homeworks WHERE user_id = {p}", (uid,))
    homework_count = cursor.fetchone()[0]
    cursor.execute(f"SELECT COUNT(*) FROM parttime_jobs WHERE user_id = {p}", (uid,))
    parttime_count = cursor.fetchone()[0]
    if not check_password_hash(user["password"], current_password):
        conn.close()
        pw_error = {"ja": "現在のパスワードが違います", "en": "Current password is incorrect", "np": "हालको पासवर्ड गलत छ"}.get(lang)
        return render_template("profile.html", user=user, schedule_count=schedule_count, homework_count=homework_count, parttime_count=parttime_count, lang=lang, pw_error=pw_error, pw_success=None)
    if len(new_password) < 6:
        conn.close()
        pw_error = {"ja": "新しいパスワードは6文字以上にしてください", "en": "New password must be at least 6 characters", "np": "नयाँ पासवर्ड कम्तीमा ६ अक्षर हुनुपर्छ"}.get(lang)
        return render_template("profile.html", user=user, schedule_count=schedule_count, homework_count=homework_count, parttime_count=parttime_count, lang=lang, pw_error=pw_error, pw_success=None)
    if new_password != new_password_confirm:
        conn.close()
        pw_error = {"ja": "新しいパスワードが一致しません", "en": "New passwords do not match", "np": "नयाँ पासवर्ड मेल खाएन"}.get(lang)
        return render_template("profile.html", user=user, schedule_count=schedule_count, homework_count=homework_count, parttime_count=parttime_count, lang=lang, pw_error=pw_error, pw_success=None)
    cursor.execute(f"UPDATE users SET password = {p} WHERE id = {p}", (generate_password_hash(new_password), uid))
    conn.commit()
    conn.close()
    pw_success = {"ja": "パスワードを変更しました", "en": "Password changed successfully", "np": "पासवर्ड परिवर्तन भयो"}.get(lang)
    user["password"] = generate_password_hash(new_password)
    return render_template("profile.html", user=user, schedule_count=schedule_count, homework_count=homework_count, parttime_count=parttime_count, lang=lang, pw_error=None, pw_success=pw_success)

@app.route("/set_language_stay/<lang>")
def set_language_stay(lang):
    if lang in ["ja", "en", "np"]:
        session["lang"] = lang
    return redirect("/profile")
