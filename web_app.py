from datetime import datetime, timedelta
from pathlib import Path
import sqlite3

from flask import Flask, flash, redirect, render_template, request, session, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "toshkent_yonalish.db"
app = Flask(__name__)
app.secret_key = "hamroh-local-development-key"


def db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = db()
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT, ism TEXT NOT NULL,
      telefon TEXT UNIQUE NOT NULL, parol TEXT NOT NULL,
      rol TEXT NOT NULL CHECK(rol IN ('haydovchi','yolovchi','dispetcher')),
      jins TEXT NOT NULL CHECK(jins IN ('erkak','ayol')), bloklangan INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS vehicles (
      id INTEGER PRIMARY KEY AUTOINCREMENT, haydovchi_id INTEGER NOT NULL,
      marka TEXT NOT NULL, model TEXT NOT NULL, davlat_raqami TEXT UNIQUE NOT NULL,
      rang TEXT, FOREIGN KEY(haydovchi_id) REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS routes (
      id INTEGER PRIMARY KEY AUTOINCREMENT, qayerdan TEXT NOT NULL,
      qayerga TEXT NOT NULL, UNIQUE(qayerdan,qayerga));
    CREATE TABLE IF NOT EXISTS trips (
      id INTEGER PRIMARY KEY AUTOINCREMENT, haydovchi_id INTEGER NOT NULL,
      avtomobil_id INTEGER NOT NULL, yonalish_id INTEGER NOT NULL,
      j_nash_vaqti TEXT NOT NULL, umumiy_joylar INTEGER NOT NULL,
      qolgan_joylar INTEGER NOT NULL, narx REAL NOT NULL,
      holat TEXT NOT NULL DEFAULT 'ochiq', faqat_ayol INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS bookings (
      id INTEGER PRIMARY KEY AUTOINCREMENT, qatnov_id INTEGER NOT NULL,
      yolovchi_id INTEGER NOT NULL, olib_ketish_manzili TEXT NOT NULL,
      holat TEXT NOT NULL DEFAULT 'band', yaratilgan_vaqti TEXT NOT NULL,
      UNIQUE(qatnov_id,yolovchi_id));
    CREATE TABLE IF NOT EXISTS ratings (
      id INTEGER PRIMARY KEY AUTOINCREMENT, qatnov_id INTEGER NOT NULL,
      yolovchi_id INTEGER NOT NULL, haydovchi_id INTEGER NOT NULL,
      ball INTEGER NOT NULL CHECK(ball BETWEEN 1 AND 5), izoh TEXT,
      UNIQUE(qatnov_id,yolovchi_id));
    CREATE TABLE IF NOT EXISTS complaints (
      id INTEGER PRIMARY KEY AUTOINCREMENT, yolovchi_id INTEGER NOT NULL,
      haydovchi_id INTEGER NOT NULL, qatnov_id INTEGER,
      matn TEXT NOT NULL, holat TEXT NOT NULL DEFAULT 'yangi');
    CREATE TABLE IF NOT EXISTS trip_templates (
      id INTEGER PRIMARY KEY AUTOINCREMENT, haydovchi_id INTEGER NOT NULL,
      yonalish_id INTEGER NOT NULL, avtomobil_id INTEGER NOT NULL,
      umumiy_joylar INTEGER NOT NULL, narx REAL NOT NULL,
      faqat_ayol INTEGER NOT NOT NULL DEFAULT 0);
    """.replace("faqat_ayol INTEGER NOT NOT NULL", "faqat_ayol INTEGER NOT NULL"))
    if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        connection.execute("INSERT INTO users(ism,telefon,parol,rol,jins) VALUES(?,?,?,?,?)", ("Dispetcher","admin","admin","dispetcher","erkak"))
        connection.execute("INSERT INTO users(ism,telefon,parol,rol,jins) VALUES(?,?,?,?,?)", ("Haydovchi","haydovchi","1234","haydovchi","erkak"))
        connection.execute("INSERT INTO users(ism,telefon,parol,rol,jins) VALUES(?,?,?,?,?)", ("Malika","malika","1234","yolovchi","ayol"))
    connection.commit()
    connection.close()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = db().execute("SELECT * FROM users WHERE telefon=? AND parol=?", (request.form["telefon"].strip(), request.form["parol"])).fetchone()
        if not user:
            flash("Login yoki parol noto'g'ri", "error")
        elif user["bloklangan"]:
            flash("Hisobingiz bloklangan", "error")
        else:
            session.update(user_id=user["id"], user_name=user["ism"], role=user["rol"])
            return redirect(url_for("dashboard"))
    return render_template("auth.html", mode="login")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        connection = db()
        try:
            connection.execute("INSERT INTO users(ism,telefon,parol,rol,jins) VALUES(?,?,?,?,?)", (request.form["ism"].strip(), request.form["telefon"].strip(), request.form["parol"], request.form["rol"], request.form["jins"]))
            connection.commit()
            flash("Ro'yxatdan o'tdingiz. Endi tizimga kiring", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Bu telefon raqam allaqachon mavjud", "error")
        finally:
            connection.close()
    return render_template("auth.html", mode="register")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/kabinet")
def dashboard():
    connection = db()
    connection.execute("UPDATE trips SET holat='yakunlangan' WHERE j_nash_vaqti < ? AND holat NOT IN ('bekor','yakunlangan')", (datetime.now().isoformat(sep=" "),))
    connection.commit()

    if not session.get("user_id"):
        qayerdan = request.args.get("qayerdan", "")
        qayerga = request.args.get("qayerga", "")
        sana = request.args.get("sana", "")
        trips = search_trips(connection, qayerdan, qayerga, sana)
        connection.close()
        return render_template("dashboard.html", trips=trips, vehicles=[], my_bookings=[])

    role = session["role"]
    user_id = session["user_id"]
    vehicles = connection.execute("SELECT * FROM vehicles WHERE haydovchi_id=?", (user_id,)).fetchall() if role == "haydovchi" else []
    passenger_list = connection.execute("""
      SELECT b.*,u.ism,u.telefon,t.j_nash_vaqti,r.qayerdan,r.qayerga
      FROM bookings b JOIN users u ON u.id=b.yolovchi_id JOIN trips t ON t.id=b.qatnov_id
      JOIN routes r ON r.id=t.yonalish_id WHERE t.haydovchi_id=?
      ORDER BY t.j_nash_vaqti DESC,b.yaratilgan_vaqti DESC""", (user_id,)).fetchall() if role == "haydovchi" else []
    my_bookings = connection.execute("""
      SELECT b.*,b.holat bron_holat,t.id trip_id,t.haydovchi_id,t.j_nash_vaqti,t.holat,t.qolgan_joylar,
             r.qayerdan,r.qayerga,u.ism haydovchi,
             EXISTS(SELECT 1 FROM ratings ra WHERE ra.qatnov_id=t.id AND ra.yolovchi_id=b.yolovchi_id) baholangan
      FROM bookings b JOIN trips t ON t.id=b.qatnov_id JOIN routes r ON r.id=t.yonalish_id
      JOIN users u ON u.id=t.haydovchi_id WHERE b.yolovchi_id=?
      ORDER BY b.yaratilgan_vaqti DESC""", (user_id,)).fetchall() if role == "yolovchi" else []
    complaints = connection.execute("""
      SELECT c.*,u.ism yolovchi,d.ism haydovchi FROM complaints c
      JOIN users u ON u.id=c.yolovchi_id JOIN users d ON d.id=c.haydovchi_id
      WHERE c.holat='yangi'""").fetchall() if role == "dispetcher" else []
    all_trips = connection.execute("""
      SELECT t.*,r.qayerdan,r.qayerga,u.ism haydovchi,u.bloklangan,v.marka,v.model
      FROM trips t JOIN routes r ON r.id=t.yonalish_id JOIN users u ON u.id=t.haydovchi_id
      JOIN vehicles v ON v.id=t.avtomobil_id ORDER BY t.j_nash_vaqti DESC""").fetchall() if role == "dispetcher" else []
    trips = search_trips(connection, request.args.get("qayerdan", ""), request.args.get("qayerga", ""), request.args.get("sana", ""))
    connection.close()
    return render_template("dashboard.html", trips=trips, vehicles=vehicles, passenger_list=passenger_list,
                           my_bookings=my_bookings, complaints=complaints, all_trips=all_trips)


def search_trips(connection, from_place, to_place, date):
    if not from_place or not to_place:
        return []
    where = ["t.holat='ochiq'", "t.qolgan_joylar>0", "u.bloklangan=0"]
    params = [from_place, to_place]
    sql = """
      SELECT t.*,r.qayerdan,r.qayerga,u.ism haydovchi,v.marka,v.model,
      (SELECT COALESCE(AVG(ball),0) FROM ratings ra WHERE ra.haydovchi_id=t.haydovchi_id) reyting
      FROM trips t JOIN routes r ON r.id=t.yonalish_id JOIN users u ON u.id=t.haydovchi_id
      JOIN vehicles v ON v.id=t.avtomobil_id WHERE r.qayerdan=? AND r.qayerga=?"""
    if date:
        where.append("substr(t.j_nash_vaqti,1,10)=?")
        params.append(date)
    where.append("t.j_nash_vaqti > ?")
    params.append(datetime.now().isoformat(sep=" "))
    sql += " AND " + " AND ".join(where) + " ORDER BY t.j_nash_vaqti"
    return connection.execute(sql, params).fetchall()


@app.post("/vehicle/add")
def add_vehicle():
    if session.get("role") != "haydovchi":
        return redirect(url_for("dashboard"))
    connection = db()
    try:
        connection.execute("INSERT INTO vehicles(haydovchi_id,marka,model,davlat_raqami,rang) VALUES(?,?,?,?,?)", (session["user_id"], request.form["marka"].strip(), request.form["model"].strip(), request.form["raqam"].strip().upper(), request.form["rang"].strip()))
        connection.commit(); flash("Avtomobil qo'shildi", "success")
    except sqlite3.IntegrityError:
        flash("Bu davlat raqami band yoki ma'lumot noto'g'ri", "error")
    finally:
        connection.close()
    return redirect(url_for("dashboard"))


@app.post("/trip/add")
def add_trip():
    if session.get("role") != "haydovchi":
        return redirect(url_for("dashboard"))
    connection = db()
    vehicle = connection.execute("SELECT id FROM vehicles WHERE id=? AND haydovchi_id=?", (request.form["avtomobil_id"], session["user_id"])).fetchone()
    if not vehicle:
        flash("Avtomobil topilmadi", "error")
    else:
        route = connection.execute("SELECT id FROM routes WHERE qayerdan=? AND qayerga=?", (request.form["qayerdan"].strip(), request.form["qayerga"].strip())).fetchone()
        route_id = route["id"] if route else connection.execute("INSERT INTO routes(qayerdan,qayerga) VALUES(?,?)", (request.form["qayerdan"].strip(), request.form["qayerga"].strip())).lastrowid
        seats = int(request.form["joylar"]); price = float(request.form["narx"])
        women = 1 if request.form.get("faqat_ayol") else 0
        connection.execute("INSERT INTO trips(haydovchi_id,avtomobil_id,yonalish_id,j_nash_vaqti,umumiy_joylar,qolgan_joylar,narx,faqat_ayol) VALUES(?,?,?,?,?,?,?,?)", (session["user_id"], vehicle["id"], route_id, request.form["vaqt"].replace("T"," "), seats, seats, price, women))
        connection.commit(); flash("Qatnov e'loni chiqarildi", "success")
    connection.close()
    return redirect(url_for("dashboard"))


@app.post("/trip/<int:trip_id>/book")
def book_trip(trip_id):
    if session.get("role") != "yolovchi":
        return redirect(url_for("login"))
    connection = db()
    trip = connection.execute("SELECT * FROM trips WHERE id=?", (trip_id,)).fetchone()
    user = connection.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    if not trip or trip["qolgan_joylar"] <= 0 or trip["holat"] != "ochiq":
        flash("Joy qolmadi yoki qatnov yopilgan", "error")
    elif trip["faqat_ayol"] and user["jins"] != "ayol":
        flash("Bu qatnov faqat ayollarga mo'ljallangan", "error")
    else:
        try:
            connection.execute("BEGIN IMMEDIATE")
            trip = connection.execute("SELECT qolgan_joylar,holat,j_nash_vaqti FROM trips WHERE id=?", (trip_id,)).fetchone()
            if not trip or trip["holat"] != "ochiq" or trip["qolgan_joylar"] <= 0:
                connection.rollback()
                flash("Joy qolmadi yoki qatnov yopilgan", "error")
            elif trip["j_nash_vaqti"] <= datetime.now().isoformat(sep=" "):
                connection.rollback()
                flash("Jo'nash vaqti o'tgan qatnovni band qilib bo'lmaydi", "error")
            else:
                connection.execute("INSERT INTO bookings(qatnov_id,yolovchi_id,olib_ketish_manzili,yaratilgan_vaqti) VALUES(?,?,?,?)", (trip_id, session["user_id"], request.form["manzil"].strip(), datetime.now().isoformat(sep=" ")))
                remaining = trip["qolgan_joylar"] - 1
                connection.execute("UPDATE trips SET qolgan_joylar=?,holat=? WHERE id=?", (remaining, "toldi" if remaining == 0 else "ochiq", trip_id))
                connection.commit(); flash("Joy muvaffaqiyatli band qilindi", "success")
        except sqlite3.IntegrityError:
            connection.rollback()
            flash("Siz bu qatnovni oldin band qilgansiz yoki joy qolmadi", "error")
    connection.close()
    return redirect(url_for("dashboard"))


@app.post("/booking/<int:booking_id>/cancel")
def cancel_booking(booking_id):
    if session.get("role") != "yolovchi":
        return redirect(url_for("login"))
    connection = db()
    booking = connection.execute("""
      SELECT b.*,t.j_nash_vaqti,t.qolgan_joylar,t.holat trip_holat
      FROM bookings b JOIN trips t ON t.id=b.qatnov_id
      WHERE b.id=? AND b.yolovchi_id=? AND b.holat='band'""", (booking_id, session["user_id"])).fetchone()
    if not booking:
        flash("Bekor qilinadigan bron topilmadi", "error")
    else:
        try:
            try:
                departure = datetime.strptime(booking["j_nash_vaqti"], "%Y-%m-%d %H:%M")
            except ValueError:
                departure = datetime.strptime(booking["j_nash_vaqti"], "%Y-%m-%d %H:%M:%S")
            if departure - datetime.now() < timedelta(hours=2):
                flash("Jo'nashga 2 soatdan kam vaqt qolgani uchun bron bekor qilinmaydi", "error")
            else:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute("UPDATE bookings SET holat='bekor' WHERE id=?", (booking_id,))
                remaining = booking["qolgan_joylar"] + 1
                connection.execute("UPDATE trips SET qolgan_joylar=?,holat='ochiq' WHERE id=?", (remaining, booking["qatnov_id"]))
                connection.commit()
                flash("Bron muvaffaqiyatli bekor qilindi", "success")
        except ValueError:
            connection.rollback()
            flash("Qatnov vaqti noto'g'ri", "error")
    connection.close()
    return redirect(url_for("dashboard"))


@app.post("/trip/<int:trip_id>/rate")
def rate_driver(trip_id):
    if session.get("role") != "yolovchi":
        return redirect(url_for("login"))
    connection = db()
    trip = connection.execute("SELECT haydovchi_id FROM trips WHERE id=?", (trip_id,)).fetchone()
    booking = connection.execute("SELECT id FROM bookings WHERE qatnov_id=? AND yolovchi_id=?", (trip_id, session["user_id"])).fetchone()
    if trip and booking:
        try:
            connection.execute("INSERT INTO ratings(qatnov_id,yolovchi_id,haydovchi_id,ball,izoh) VALUES(?,?,?,?,?)",
                               (trip_id, session["user_id"], trip["haydovchi_id"], int(request.form["ball"]), request.form.get("izoh", "").strip()))
            connection.commit(); flash("Haydovchi baholandi", "success")
        except sqlite3.IntegrityError:
            flash("Bu qatnov oldin baholangan", "error")
    connection.close()
    return redirect(url_for("dashboard"))


@app.post("/complaint/add")
def add_complaint():
    if session.get("role") != "yolovchi":
        return redirect(url_for("login"))
    connection = db()
    trip_id = request.form.get("trip_id")
    trip = connection.execute("SELECT haydovchi_id FROM trips WHERE id=?", (trip_id,)).fetchone() if trip_id else None
    if trip:
        connection.execute("INSERT INTO complaints(yolovchi_id,haydovchi_id,qatnov_id,matn) VALUES(?,?,?,?)",
                           (session["user_id"], trip["haydovchi_id"], trip_id, request.form["matn"].strip()))
        connection.commit(); flash("Shikoyat dispetcherga yuborildi", "success")
    else:
        flash("Shikoyat uchun qatnov topilmadi", "error")
    connection.close()
    return redirect(url_for("dashboard"))


@app.post("/complaint/<int:complaint_id>/process")
def process_complaint(complaint_id):
    if session.get("role") != "dispetcher":
        return redirect(url_for("login"))
    connection = db()
    complaint = connection.execute("SELECT * FROM complaints WHERE id=?", (complaint_id,)).fetchone()
    if complaint:
        if request.form.get("bloklash"):
            connection.execute("UPDATE users SET bloklangan=1 WHERE id=?", (complaint["haydovchi_id"],))
        connection.execute("UPDATE complaints SET holat='korib_chiqildi' WHERE id=?", (complaint_id,))
        connection.commit(); flash("Shikoyat ko'rib chiqildi", "success")
    connection.close()
    return redirect(url_for("dashboard"))


init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
