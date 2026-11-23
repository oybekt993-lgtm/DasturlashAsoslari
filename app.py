import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).with_name("toshkent_yonalish.db")


class RideApp:
    def __init__(self):
        self.db = sqlite3.connect(DB_PATH)
        self.db.row_factory = sqlite3.Row
        self.user_id = None
        self.role = None
        self.create_tables()
        self.seed_data()

    def create_tables(self):
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ism TEXT NOT NULL,
            telefon TEXT UNIQUE NOT NULL,
            parol TEXT NOT NULL,
            rol TEXT NOT NULL CHECK(rol IN ('haydovchi','yolovchi','dispetcher')),
            jins TEXT CHECK(jins IN ('erkak','ayol')),
            bloklangan INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            haydovchi_id INTEGER NOT NULL,
            marka TEXT NOT NULL,
            model TEXT NOT NULL,
            davlat_raqami TEXT UNIQUE NOT NULL,
            rang TEXT,
            FOREIGN KEY(haydovchi_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qayerdan TEXT NOT NULL,
            qayerga TEXT NOT NULL,
            UNIQUE(qayerdan, qayerga)
        );

        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            haydovchi_id INTEGER NOT NULL,
            avtomobil_id INTEGER NOT NULL,
            yonalish_id INTEGER NOT NULL,
            j_nash_vaqti TEXT NOT NULL,
            umumiy_joylar INTEGER NOT NULL CHECK(umumiy_joylar > 0),
            qolgan_joylar INTEGER NOT NULL,
            narx REAL NOT NULL,
            holat TEXT NOT NULL DEFAULT 'ochiq' CHECK(holat IN ('ochiq','toldi','bekor','yakunlangan')),
            faqat_ayol INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(haydovchi_id) REFERENCES users(id),
            FOREIGN KEY(avtomobil_id) REFERENCES vehicles(id),
            FOREIGN KEY(yonalish_id) REFERENCES routes(id)
        );

        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qatnov_id INTEGER NOT NULL,
            yolovchi_id INTEGER NOT NULL,
            olib_ketish_manzili TEXT NOT NULL,
            holat TEXT NOT NULL DEFAULT 'band' CHECK(holat IN ('band','bekor','yakunlangan')),
            yaratilgan_vaqti TEXT NOT NULL,
            UNIQUE(qatnov_id, yolovchi_id),
            FOREIGN KEY(qatnov_id) REFERENCES trips(id),
            FOREIGN KEY(yolovchi_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qatnov_id INTEGER NOT NULL,
            yolovchi_id INTEGER NOT NULL,
            haydovchi_id INTEGER NOT NULL,
            ball INTEGER NOT NULL CHECK(ball BETWEEN 1 AND 5),
            izoh TEXT,
            UNIQUE(qatnov_id, yolovchi_id),
            FOREIGN KEY(qatnov_id) REFERENCES trips(id),
            FOREIGN KEY(yolovchi_id) REFERENCES users(id),
            FOREIGN KEY(haydovchi_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            yolovchi_id INTEGER NOT NULL,
            haydovchi_id INTEGER NOT NULL,
            qatnov_id INTEGER,
            matn TEXT NOT NULL,
            holat TEXT NOT NULL DEFAULT 'yangi',
            FOREIGN KEY(yolovchi_id) REFERENCES users(id),
            FOREIGN KEY(haydovchi_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS trip_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            haydovchi_id INTEGER NOT NULL,
            yonalish_id INTEGER NOT NULL,
            avtomobil_id INTEGER NOT NULL,
            umumiy_joylar INTEGER NOT NULL,
            narx REAL NOT NULL,
            faqat_ayol INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(haydovchi_id) REFERENCES users(id)
        );
        """)
        self.db.commit()

    def seed_data(self):
        cur = self.db.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] == 0:
            self.db.execute("INSERT INTO users(ism,telefon,parol,rol,jins) VALUES(?,?,?,?,?)", ("Dispetcher", "admin", "admin", "dispetcher", "erkak"))
            self.db.execute("INSERT INTO users(ism,telefon,parol,rol,jins) VALUES(?,?,?,?,?)", ("Haydovchi", "haydovchi", "1234", "haydovchi", "erkak"))
            self.db.execute("INSERT INTO users(ism,telefon,parol,rol,jins) VALUES(?,?,?,?,?)", ("Malika", "malika", "1234", "yolovchi", "ayol"))
            self.db.commit()

    def input_text(self, label):
        return input(label).strip()

    def input_int(self, label, minimum=0, maximum=None):
        while True:
            try:
                value = int(input(label).strip())
                if value < minimum or (maximum is not None and value > maximum):
                    raise ValueError
                return value
            except ValueError:
                print("Xato: butun son kiriting.")

    def input_datetime(self, label):
        while True:
            raw = input(label + " (YYYY-MM-DD HH:MM): ").strip()
            try:
                dt = datetime.strptime(raw, "%Y-%m-%d %H:%M")
                return dt
            except ValueError:
                print("Xato sana vaqti. Masalan: 2026-12-01 09:30")

    def register(self):
        print("\n--- RO'YXATDAN O'TISH ---")
        ism = self.input_text("Ism: ")
        telefon = self.input_text("Telefon: ")
        parol = self.input_text("Parol: ")
        while True:
            rol = self.input_text("Rol (haydovchi/yolovchi): ").lower()
            if rol in ('haydovchi', 'yolovchi'):
                break
        while True:
            jins = self.input_text("Jins (erkak/ayol): ").lower()
            if jins in ('erkak', 'ayol'):
                break
        try:
            self.db.execute("INSERT INTO users(ism,telefon,parol,rol,jins) VALUES(?,?,?,?,?)", (ism, telefon, parol, rol, jins))
            self.db.commit()
            print("Ro'yxatdan o'tdingiz.")
        except sqlite3.IntegrityError:
            print("Bu telefon raqam oldin ro'yxatdan o'tgan.")

    def login(self):
        print("\n--- TIZIMGA KIRISH ---")
        telefon = self.input_text("Telefon/login: ")
        parol = self.input_text("Parol: ")
        user = self.db.execute("SELECT * FROM users WHERE telefon=? AND parol=?", (telefon, parol)).fetchone()
        if not user:
            print("Login yoki parol noto'g'ri.")
            return
        if user["bloklangan"]:
            print("Hisobingiz bloklangan.")
            return
        self.user_id = user["id"]
        self.role = user["rol"]
        print(f"Xush kelibsiz, {user['ism']}!")

    def logout(self):
        self.user_id = None
        self.role = None

    def add_vehicle(self):
        marka = self.input_text("Marka: ")
        model = self.input_text("Model: ")
        davlat_raqami = self.input_text("Davlat raqami: ").upper()
        rang = self.input_text("Rang: ")
        try:
            self.db.execute("INSERT INTO vehicles(haydovchi_id,marka,model,davlat_raqami,rang) VALUES(?,?,?,?,?)", (self.user_id, marka, model, davlat_raqami, rang))
            self.db.commit()
            print("Avtomobil qo'shildi.")
        except sqlite3.IntegrityError:
            print("Bu davlat raqami yoki ma'lumot allaqachon mavjud.")

    def get_or_create_route(self, from_place, to_place):
        route = self.db.execute("SELECT * FROM routes WHERE qayerdan=? AND qayerga=?", (from_place, to_place)).fetchone()
        if route:
            return route["id"]
        cur = self.db.execute("INSERT INTO routes(qayerdan,qayerga) VALUES(?,?)", (from_place, to_place))
        self.db.commit()
        return cur.lastrowid

    def driver_vehicles(self):
        return self.db.execute("SELECT * FROM vehicles WHERE haydovchi_id=?", (self.user_id,)).fetchall()

    def publish_trip(self):
        vehicles = self.driver_vehicles()
        if not vehicles:
            print("Avval avtomobil ma'lumotini kiriting.")
            return
        print("Avtomobillar:")
        for v in vehicles:
            print(f"{v['id']}. {v['marka']} {v['model']} ({v['davlat_raqami']})")
        avtomobil_id = self.input_int("Avtomobil ID: ", 1)
        if not any(v["id"] == avtomobil_id for v in vehicles):
            print("Noto'g'ri avtomobil.")
            return
        from_place = self.input_text("Jo'nash shahri/manzili: ")
        to_place = self.input_text("Boradigan manzil: ")
        departs = self.input_datetime("Jo'nash sanasi")
        seats = self.input_int("Bo'sh joylar soni: ", 1)
        price = float(self.input_text("Bir joy narxi: "))
        women = 1 if self.input_text("Faqat ayol yo'lovchilar uchun? (ha/yo'q): ").lower() in ('ha','yes','y') else 0
        route_id = self.get_or_create_route(from_place, to_place)
        self.db.execute("INSERT INTO trips(haydovchi_id,avtomobil_id,yonalish_id,j_nash_vaqti,umumiy_joylar,qolgan_joylar,narx,faqat_ayol) VALUES(?,?,?,?,?,?,?,?)", (self.user_id, avtomobil_id, route_id, departs.isoformat(sep=' '), seats, seats, price, women))
        self.db.commit()
        print("Qatnov e'loni chiqarildi.")

    def save_template(self):
        vehicles = self.driver_vehicles()
        if not vehicles:
            print("Avval avtomobil qo'shing.")
            return
        for v in vehicles:
            print(f"{v['id']}. {v['marka']} {v['model']}")
        avtomobil_id = self.input_int("Avtomobil ID: ", 1)
        from_place = self.input_text("Jo'nash: ")
        to_place = self.input_text("Borish: ")
        seats = self.input_int("Joylar: ", 1)
        try:
            price = float(self.input_text("Narx: "))
        except ValueError:
            print("Xato narx.")
            return
        women = 1 if self.input_text("Faqat ayollar? (ha/yo'q): ").lower() in ('ha','y','yes') else 0
        route_id = self.get_or_create_route(from_place, to_place)
        self.db.execute("INSERT INTO trip_templates(haydovchi_id,yonalish_id,avtomobil_id,umumiy_joylar,narx,faqat_ayol) VALUES(?,?,?,?,?,?)", (self.user_id, route_id, avtomobil_id, seats, price, women))
        self.db.commit()
        print("Shablon saqlandi.")

    def publish_from_template(self):
        templates = self.db.execute("SELECT t.*, r.qayerdan, r.qayerga FROM trip_templates t JOIN routes r ON r.id=t.yonalish_id WHERE t.haydovchi_id=?", (self.user_id,)).fetchall()
        if not templates:
            print("Shablon yo'q.")
            return
        for t in templates:
            print(f"{t['id']}. {t['qayerdan']} -> {t['qayerga']}, {t['umumiy_joylar']} joy, {t['narx']} so'm")
        template_id = self.input_int("Shablon ID: ", 1)
        template = next((t for t in templates if t['id'] == template_id), None)
        if not template:
            print("Noto'g'ri shablon.")
            return
        departs = self.input_datetime("Jo'nash sanasi")
        seats = template['umumiy_joylar']
        self.db.execute("INSERT INTO trips(haydovchi_id,avtomobil_id,yonalish_id,j_nash_vaqti,umumiy_joylar,qolgan_joylar,narx,faqat_ayol) VALUES(?,?,?,?,?,?,?,?)", (self.user_id, template['avtomobil_id'], template['yonalish_id'], departs.isoformat(sep=' '), seats, seats, template['narx'], template['faqat_ayol']))
        self.db.commit()
        print("Shablondan qatnov e'loni chiqarildi.")

    def refresh_trip_statuses(self):
        now = datetime.now()
        self.db.execute("UPDATE trips SET holat='yakunlangan' WHERE j_nash_vaqti < ? AND holat NOT IN ('bekor','yakunlangan')", (now.isoformat(sep=' '),))
        self.db.commit()

    def search_trips(self):
        self.refresh_trip_statuses()
        from_place = self.input_text("Jo'nash shahri: ")
        to_place = self.input_text("Borish shahri: ")
        date_raw = self.input_text("Sana (YYYY-MM-DD): ")
        try:
            datetime.strptime(date_raw, "%Y-%m-%d")
        except ValueError:
            print("Xato sana.")
            return
        women_only = False
        if self.user_id:
            user = self.db.execute("SELECT jins FROM users WHERE id=?", (self.user_id,)).fetchone()
            if user and user['jins'] == 'ayol':
                women_only = self.input_text("Faqat ayol yo'lovchilar uchun qatnovlarni ko'rish? (ha/yo'q): ").lower() in ('ha','y','yes')
        now = datetime.now().isoformat(sep=' ')
        rows = self.db.execute("""
            SELECT t.*, r.qayerdan, r.qayerga,
                   u.ism AS haydovchi, v.marka, v.model,
                   (SELECT COALESCE(AVG(ball),0) FROM ratings ra WHERE ra.haydovchi_id=t.haydovchi_id) AS reyting
            FROM trips t
            JOIN routes r ON r.id=t.yonalish_id
            JOIN users u ON u.id=t.haydovchi_id
            JOIN vehicles v ON v.id=t.avtomobil_id
            WHERE r.qayerdan=? AND r.qayerga=? AND substr(t.j_nash_vaqti,1,10)=?
              AND t.j_nash_vaqti > ? AND t.qolgan_joylar>0 AND t.holat='ochiq'
              AND u.bloklangan=0 AND (?=0 OR t.faqat_ayol=1)
            ORDER BY t.j_nash_vaqti
        """, (from_place, to_place, date_raw, now, 1 if women_only else 0)).fetchall()
        if not rows:
            print("Mos qatnov topilmadi.")
            return
        for r in rows:
            print(f"{r['id']}. {r['haydovchi']} | {r['marka']} {r['model']} | {r['j_nash_vaqti']} | {r['qolgan_joylar']} joy | {r['narx']} so'm | Reyting: {r['reyting']:.1f}" + (" | AYOLLAR UCHUN" if r['faqat_ayol'] else ""))

    def book_trip(self):
        self.search_trips()
        trip_id = self.input_int("Band qilinadigan qatnov ID: ", 1)
        trip = self.db.execute("SELECT t.*, u.jins FROM trips t JOIN users u ON u.id=t.haydovchi_id WHERE t.id=?", (trip_id,)).fetchone()
        if not trip:
            print("Qatnov topilmadi.")
            return
        self.refresh_trip_statuses()
        trip = self.db.execute("SELECT * FROM trips WHERE id=?", (trip_id,)).fetchone()
        if trip["holat"] != 'ochiq' or trip["qolgan_joylar"] <= 0:
            print("Qatnovda bo'sh joy yo'q yoki u yopilgan.")
            return
        user = self.db.execute("SELECT * FROM users WHERE id=?", (self.user_id,)).fetchone()
        if trip["faqat_ayol"] and user["jins"] != 'ayol':
            print("Bu qatnov faqat ayol yo'lovchilar uchun.")
            return
        existing = self.db.execute("SELECT id FROM bookings WHERE qatnov_id=? AND yolovchi_id=?", (trip_id, self.user_id)).fetchone()
        if existing:
            print("Siz bu qatnovni oldin band qilgansiz.")
            return
        address = self.input_text("Olib ketish manzili: ")
        try:
            self.db.execute("BEGIN")
            trip = self.db.execute("SELECT qolgan_joylar, holat FROM trips WHERE id=?", (trip_id,)).fetchone()
            if trip['qolgan_joylar'] <= 0:
                raise sqlite3.IntegrityError("Joy qolmadi")
            self.db.execute("INSERT INTO bookings(qatnov_id,yolovchi_id,olib_ketish_manzili,yaratilgan_vaqti) VALUES(?,?,?,?)", (trip_id, self.user_id, address, datetime.now().isoformat(sep=' ')))
            remaining = trip['qolgan_joylar'] - 1
            new_status = 'toldi' if remaining == 0 else 'ochiq'
            self.db.execute("UPDATE trips SET qolgan_joylar=?, holat=? WHERE id=?", (remaining, new_status, trip_id))
            self.db.commit()
            print("Joy muvaffaqiyatli band qilindi.")
        except sqlite3.IntegrityError as exc:
            self.db.rollback()
            print(f"Band qilishda xato: {exc}")

    def cancel_booking(self):
        rows = self.db.execute("""
            SELECT b.*, t.j_nash_vaqti, r.qayerdan, r.qayerga
            FROM bookings b JOIN trips t ON t.id=b.qatnov_id
            JOIN routes r ON r.id=t.yonalish_id
            WHERE b.yolovchi_id=? AND b.holat='band'
        """, (self.user_id,)).fetchall()
        if not rows:
            print("Faol bron yo'q.")
            return
        for r in rows:
            print(f"{r['id']}. {r['qayerdan']} -> {r['qayerga']} | {r['j_nash_vaqti']} | {r['olib_ketish_manzili']}")
        booking_id = self.input_int("Bekor qilinadigan bron ID: ", 1)
        booking = next((r for r in rows if r['id'] == booking_id), None)
        if not booking:
            print("Noto'g'ri bron.")
            return
        departure = datetime.strptime(booking['j_nash_vaqti'], "%Y-%m-%d %H:%M:%S")
        if departure - datetime.now() < timedelta(hours=2):
            print("Jo'nashga 2 soatdan kam vaqt qoldi. Bron bekor qilinmaydi.")
            return
        trip = self.db.execute("SELECT qolgan_joylar, umumiy_joylar FROM trips WHERE id=?", (booking['qatnov_id'],)).fetchone()
        self.db.execute("UPDATE bookings SET holat='bekor' WHERE id=?", (booking_id,))
        remaining = min(trip['umumiy_joylar'], trip['qolgan_joylar'] + 1)
        self.db.execute("UPDATE trips SET qolgan_joylar=?, holat='ochiq' WHERE id=?", (remaining, booking['qatnov_id']))
        self.db.commit()
        print("Bron bekor qilindi.")

    def my_bookings(self):
        rows = self.db.execute("""
            SELECT b.*, t.j_nash_vaqti, r.qayerdan, r.qayerga, u.ism AS haydovchi
            FROM bookings b JOIN trips t ON t.id=b.qatnov_id
            JOIN routes r ON r.id=t.yonalish_id JOIN users u ON u.id=t.haydovchi_id
            WHERE b.yolovchi_id=? ORDER BY t.j_nash_vaqti DESC
        """, (self.user_id,)).fetchall()
        if not rows:
            print("Bronlar topilmadi.")
            return
        for r in rows:
            print(f"Bron #{r['id']}: {r['qayerdan']} -> {r['qayerga']} | {r['j_nash_vaqti']} | Haydovchi: {r['haydovchi']} | {r['holat']}")

    def rate_driver(self):
        rows = self.db.execute("""
            SELECT b.id AS bron_id, b.qatnov_id, t.haydovchi_id, t.j_nash_vaqti, u.ism
            FROM bookings b JOIN trips t ON t.id=b.qatnov_id JOIN users u ON u.id=t.haydovchi_id
            WHERE b.yolovchi_id=? AND b.holat='band' AND t.j_nash_vaqti < ?
              AND NOT EXISTS (SELECT 1 FROM ratings ra WHERE ra.qatnov_id=b.qatnov_id AND ra.yolovchi_id=b.yolovchi_id)
        """, (self.user_id, datetime.now().isoformat(sep=' '))).fetchall()
        if not rows:
            print("Baholash uchun tugagan safar yo'q.")
            return
        for r in rows:
            print(f"{r['bron_id']}. {r['ism']} | {r['j_nash_vaqti']}")
        bron_id = self.input_int("Bron ID: ", 1)
        row = next((r for r in rows if r['bron_id'] == bron_id), None)
        if not row:
            print("Noto'g'ri bron.")
            return
        ball = self.input_int("Baho (1-5): ", 1, 5)
        izoh = self.input_text("Izoh (ixtiyoriy): ")
        self.db.execute("INSERT INTO ratings(qatnov_id,yolovchi_id,haydovchi_id,ball,izoh) VALUES(?,?,?,?,?)", (row['qatnov_id'], self.user_id, row['haydovchi_id'], ball, izoh))
        self.db.execute("UPDATE bookings SET holat='yakunlangan' WHERE id=?", (bron_id,))
        self.db.commit()
        print("Haydovchi baholandi.")

    def add_complaint(self):
        haydovchilar = self.db.execute("""
            SELECT DISTINCT u.id, u.ism FROM users u JOIN trips t ON t.haydovchi_id=u.id
            JOIN bookings b ON b.qatnov_id=t.id WHERE b.yolovchi_id=?
        """, (self.user_id,)).fetchall()
        if not haydovchilar:
            print("Shikoyat qilinadigan haydovchi yo'q.")
            return
        for d in haydovchilar:
            print(f"{d['id']}. {d['ism']}")
        driver_id = self.input_int("Haydovchi ID: ", 1)
        matn = self.input_text("Shikoyat matni: ")
        self.db.execute("INSERT INTO complaints(yolovchi_id,haydovchi_id,matn) VALUES(?,?,?)", (self.user_id, driver_id, matn))
        self.db.commit()
        print("Shikoyat qabul qilindi.")

    def driver_passengers(self):
        rows = self.db.execute("""
            SELECT t.id AS qatnov_id, t.j_nash_vaqti, r.qayerdan, r.qayerga,
                   u.ism, u.telefon, b.olib_ketish_manzili, b.holat
            FROM trips t JOIN routes r ON r.id=t.yonalish_id
            JOIN bookings b ON b.qatnov_id=t.id JOIN users u ON u.id=b.yolovchi_id
            WHERE t.haydovchi_id=? ORDER BY t.j_nash_vaqti DESC
        """, (self.user_id,)).fetchall()
        if not rows:
            print("Band yo'lovchilar yo'q.")
            return
        for r in rows:
            print(f"Qatnov #{r['qatnov_id']}: {r['qayerdan']} -> {r['qayerga']} | {r['j_nash_vaqti']} | {r['ism']} | {r['telefon']} | Manzil: {r['olib_ketish_manzili']} | {r['holat']}")

    def driver_rating(self):
        row = self.db.execute("SELECT AVG(ball) AS reyting, COUNT(*) AS soni FROM ratings WHERE haydovchi_id=?", (self.user_id,)).fetchone()
        print(f"Sizning reytingingiz: {(row['reyting'] or 0):.2f} ({row['soni']} ta baho)")

    def dispatcher_all_trips(self):
        rows = self.db.execute("""
            SELECT t.*, r.qayerdan, r.qayerga, u.ism AS haydovchi
            FROM trips t JOIN routes r ON r.id=t.yonalish_id JOIN users u ON u.id=t.haydovchi_id
            ORDER BY t.j_nash_vaqti DESC
        """).fetchall()
        for r in rows:
            print(f"#{r['id']} {r['qayerdan']} -> {r['qayerga']} | {r['haydovchi']} | {r['j_nash_vaqti']} | {r['qolgan_joylar']}/{r['umumiy_joylar']} | {r['holat']}")

    def dispatcher_complaints(self):
        rows = self.db.execute("""
            SELECT c.*, d.ism AS haydovchi, p.ism AS yolovchi
            FROM complaints c JOIN users d ON d.id=c.haydovchi_id JOIN users p ON p.id=c.yolovchi_id
            WHERE c.holat='yangi'
        """).fetchall()
        if not rows:
            print("Yangi shikoyat yo'q.")
            return
        for r in rows:
            print(f"#{r['id']} Yo'lovchi: {r['yolovchi']} | Haydovchi: {r['haydovchi']} | {r['matn']}")
        complaint_id = self.input_int("Ko'rib chiqiladigan shikoyat ID: ", 1)
        row = next((r for r in rows if r['id'] == complaint_id), None)
        if not row:
            print("Noto'g'ri ID.")
            return
        if self.input_text("Haydovchini bloklash? (ha/yo'q): ").lower() in ('ha','y','yes'):
            self.db.execute("UPDATE users SET bloklangan=1 WHERE id=?", (row['haydovchi_id'],))
        self.db.execute("UPDATE complaints SET holat='ko'rib_chiqildi' WHERE id=?", (complaint_id,))
        self.db.commit()
        print("Shikoyat ko'rib chiqildi.")

    def driver_menu(self):
        while True:
            print("\n--- HAYDOVCHI MENYUSI ---")
            print("1 Avtomobil qo'shish\n2 Qatnov e'lon qilish\n3 Shablon saqlash\n4 Shablondan e'lon qilish\n5 Yo'lovchilar ro'yxati\n6 Reytingim\n0 Chiqish")
            choice = input("Tanlov: ").strip()
            if choice == '1': self.add_vehicle()
            elif choice == '2': self.publish_trip()
            elif choice == '3': self.save_template()
            elif choice == '4': self.publish_from_template()
            elif choice == '5': self.driver_passengers()
            elif choice == '6': self.driver_rating()
            elif choice == '0': return

    def passenger_menu(self):
        while True:
            print("\n--- YO'LOVCHI MENYUSI ---")
            print("1 Qatnov qidirish\n2 Joy band qilish\n3 Bronlarni ko'rish\n4 Bronni bekor qilish\n5 Haydovchini baholash\n6 Shikoyat yuborish\n0 Chiqish")
            choice = input("Tanlov: ").strip()
            if choice == '1': self.search_trips()
            elif choice == '2': self.book_trip()
            elif choice == '3': self.my_bookings()
            elif choice == '4': self.cancel_booking()
            elif choice == '5': self.rate_driver()
            elif choice == '6': self.add_complaint()
            elif choice == '0': return

    def dispatcher_menu(self):
        while True:
            print("\n--- DISPETCHER MENYUSI ---")
            print("1 Barcha qatnovlar\n2 Shikoyatlar\n0 Chiqish")
            choice = input("Tanlov: ").strip()
            if choice == '1': self.dispatcher_all_trips()
            elif choice == '2': self.dispatcher_complaints()
            elif choice == '0': return

    def main(self):
        while True:
            print("\n=== TOSHKENT - VILOYAT YO'NALISHI ===")
            if not self.user_id:
                print("1 Kirish\n2 Ro'yxatdan o'tish\n0 Dasturdan chiqish")
                choice = input("Tanlov: ").strip()
                if choice == '1':
                    self.login()
                elif choice == '2':
                    self.register()
                elif choice == '0':
                    print("Xayr!")
                    self.db.close()
                    break
            else:
                if self.role == 'haydovchi': self.driver_menu(); self.logout()
                elif self.role == 'yolovchi': self.passenger_menu(); self.logout()
                elif self.role == 'dispetcher': self.dispatcher_menu(); self.logout()


if __name__ == "__main__":
    RideApp().main()
