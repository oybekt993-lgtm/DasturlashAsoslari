import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).with_name("toshkent_yonalish.db")


class RideGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Toshkent - viloyat qatnov tizimi")
        self.root.geometry("980x680")
        self.root.minsize(800, 600)

        self.db = sqlite3.connect(DB_PATH)
        self.db.row_factory = sqlite3.Row
        self.user_id = None
        self.role = None
        self.user_name = None

        self.create_tables()
        self.seed_data()
        self.build_login()

    def create_tables(self):
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ism TEXT NOT NULL,
            telefon TEXT UNIQUE NOT NULL,
            parol TEXT NOT NULL,
            rol TEXT NOT NULL CHECK(rol IN ('haydovchi','yolovchi','dispetcher')),
            jins TEXT NOT NULL CHECK(jins IN ('erkak','ayol')),
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
            UNIQUE(qayerdan,qayerga)
        );
        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            haydovchi_id INTEGER NOT NULL,
            avtomobil_id INTEGER NOT NULL,
            yonalish_id INTEGER NOT NULL,
            j_nash_vaqti TEXT NOT NULL,
            umumiy_joylar INTEGER NOT NULL,
            qolgan_joylar INTEGER NOT NULL,
            narx REAL NOT NULL,
            holat TEXT NOT NULL DEFAULT 'ochiq',
            faqat_ayol INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qatnov_id INTEGER NOT NULL,
            yolovchi_id INTEGER NOT NULL,
            olib_ketish_manzili TEXT NOT NULL,
            holat TEXT NOT NULL DEFAULT 'band',
            yaratilgan_vaqti TEXT NOT NULL,
            UNIQUE(qatnov_id,yolovchi_id)
        );
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qatnov_id INTEGER NOT NULL,
            yolovchi_id INTEGER NOT NULL,
            haydovchi_id INTEGER NOT NULL,
            ball INTEGER NOT NULL CHECK(ball BETWEEN 1 AND 5),
            izoh TEXT,
            UNIQUE(qatnov_id,yolovchi_id)
        );
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            yolovchi_id INTEGER NOT NULL,
            haydovchi_id INTEGER NOT NULL,
            qatnov_id INTEGER,
            matn TEXT NOT NULL,
            holat TEXT NOT NULL DEFAULT 'yangi'
        );
        CREATE TABLE IF NOT EXISTS trip_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            haydovchi_id INTEGER NOT NULL,
            yonalish_id INTEGER NOT NULL,
            avtomobil_id INTEGER NOT NULL,
            umumiy_joylar INTEGER NOT NULL,
            narx REAL NOT NULL,
            faqat_ayol INTEGER NOT NULL DEFAULT 0
        );
        """)
        self.db.commit()

    def seed_data(self):
        if self.db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            self.db.execute("INSERT INTO users(ism,telefon,parol,rol,jins) VALUES(?,?,?,?,?)", ("Dispetcher", "admin", "admin", "dispetcher", "erkak"))
            self.db.execute("INSERT INTO users(ism,telefon,parol,rol,jins) VALUES(?,?,?,?,?)", ("Haydovchi", "haydovchi", "1234", "haydovchi", "erkak"))
            self.db.execute("INSERT INTO users(ism,telefon,parol,rol,jins) VALUES(?,?,?,?,?)", ("Malika", "malika", "1234", "yolovchi", "ayol"))
            self.db.commit()

    def clear(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def form_field(self, parent, label, width=34, show=None):
        ttk.Label(parent, text=label).pack(anchor="w", pady=(8, 2))
        entry = ttk.Entry(parent, width=width, show=show)
        entry.pack(fill="x")
        return entry

    def build_login(self):
        self.clear()
        frame = ttk.Frame(self.root, padding=35)
        frame.place(relx=.5, rely=.5, anchor="center")

        ttk.Label(frame, text="Toshkent - viloyat qatnov tizimi", font=("Segoe UI", 18, "bold")).pack(pady=(0, 20))
        login = self.form_field(frame, "Telefon yoki login:")
        password = self.form_field(frame, "Parol:", show="*")

        def login_action():
            user = self.db.execute("SELECT * FROM users WHERE telefon=? AND parol=?", (login.get().strip(), password.get())).fetchone()
            if not user:
                messagebox.showerror("Xato", "Login yoki parol noto'g'ri")
                return
            if user["bloklangan"]:
                messagebox.showerror("Bloklangan", "Bu hisob bloklangan")
                return
            self.user_id = user["id"]
            self.role = user["rol"]
            self.user_name = user["ism"]
            self.build_main()

        ttk.Button(frame, text="Kirish", command=login_action).pack(fill="x", pady=(18, 7))
        ttk.Button(frame, text="Ro'yxatdan o'tish", command=self.build_register).pack(fill="x")

        info = ttk.Label(frame, text="Sinov: admin/admin | haydovchi/1234 | malika/1234", foreground="#666")
        info.pack(pady=(18, 0))

        login.bind("<Return>", lambda e: login_action())
        password.bind("<Return>", lambda e: login_action())

    def build_register(self):
        self.clear()
        frame = ttk.Frame(self.root, padding=35)
        frame.place(relx=.5, rely=.5, anchor="center")

        ttk.Label(frame, text="Ro'yxatdan o'tish", font=("Segoe UI", 18, "bold")).pack(pady=(0, 12))
        name = self.form_field(frame, "Ism:")
        phone = self.form_field(frame, "Telefon:")
        password = self.form_field(frame, "Parol:", show="*")

        ttk.Label(frame, text="Rol:").pack(anchor="w", pady=(8, 2))
        role = ttk.Combobox(frame, values=["haydovchi", "yolovchi"], state="readonly", width=32)
        role.set("yolovchi")
        role.pack(fill="x")

        ttk.Label(frame, text="Jins:").pack(anchor="w", pady=(8, 2))
        gender = ttk.Combobox(frame, values=["erkak", "ayol"], state="readonly", width=32)
        gender.set("erkak")
        gender.pack(fill="x")

        def register_action():
            if not all((name.get().strip(), phone.get().strip(), password.get())):
                messagebox.showwarning("Diqqat", "Barcha maydonlarni to'ldiring")
                return
            try:
                self.db.execute("INSERT INTO users(ism,telefon,parol,rol,jins) VALUES(?,?,?,?,?)", (name.get().strip(), phone.get().strip(), password.get(), role.get(), gender.get()))
                self.db.commit()
                messagebox.showinfo("Muvaffaqiyat", "Ro'yxatdan o'tdingiz")
                self.build_login()
            except sqlite3.IntegrityError:
                messagebox.showerror("Xato", "Bu telefon raqam allaqachon mavjud")

        ttk.Button(frame, text="Ro'yxatdan o'tish", command=register_action).pack(fill="x", pady=(18, 7))
        ttk.Button(frame, text="Kirishga qaytish", command=self.build_login).pack(fill="x")

    def build_main(self):
        self.clear()
        top = ttk.Frame(self.root, padding=(12, 8))
        top.pack(fill="x")
        ttk.Label(top, text=f"Foydalanuvchi: {self.user_name} ({self.role})", font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Button(top, text="Chiqish", command=self.logout).pack(side="right")

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        if self.role == "haydovchi":
            self.build_driver_ui(notebook)
        elif self.role == "yolovchi":
            self.build_passenger_ui(notebook)
        else:
            self.build_dispatcher_ui(notebook)

    def logout(self):
        self.user_id = None
        self.role = None
        self.user_name = None
        self.build_login()

    def refresh_trip_statuses(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.db.execute("UPDATE trips SET holat='yakunlangan' WHERE j_nash_vaqti < ? AND holat!='bekor'", (now,))
        self.db.commit()

    def make_table(self, parent, columns, widths=None, height=12):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        table = ttk.Treeview(frame, columns=columns, show="headings", height=height)
        for i, col in enumerate(columns):
            table.heading(col, text=col)
            table.column(col, width=(widths[i] if widths else 130), anchor="w")
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=table.yview)
        table.configure(yscrollcommand=yscroll.set)
        table.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")
        return table

    def build_driver_ui(self, notebook):
        tab_vehicle = ttk.Frame(notebook)
        tab_trip = ttk.Frame(notebook)
        tab_passengers = ttk.Frame(notebook)
        tab_template = ttk.Frame(notebook)
        notebook.add(tab_vehicle, text="Avtomobil")
        notebook.add(tab_trip, text="Qatnov e'loni")
        notebook.add(tab_passengers, text="Yo'lovchilar")
        notebook.add(tab_template, text="Shablon")

        left = ttk.Frame(tab_vehicle, padding=15)
        left.pack(side="left", fill="y")
        marka = self.form_field(left, "Marka:", 28)
        model = self.form_field(left, "Model:", 28)
        number = self.form_field(left, "Davlat raqami:", 28)
        color = self.form_field(left, "Rang:", 28)

        table = self.make_table(tab_vehicle, ["ID", "Marka", "Model", "Raqam", "Rang"])

        def load_vehicles():
            table.delete(*table.get_children())
            for v in self.db.execute("SELECT * FROM vehicles WHERE haydovchi_id=?", (self.user_id,)):
                table.insert("", "end", values=(v["id"], v["marka"], v["model"], v["davlat_raqami"], v["rang"] or ""))

        def add_vehicle():
            if not all((marka.get().strip(), model.get().strip(), number.get().strip())):
                messagebox.showwarning("Diqqat", "Marka, model va raqamni kiriting")
                return
            try:
                self.db.execute("INSERT INTO vehicles(haydovchi_id,marka,model,davlat_raqami,rang) VALUES(?,?,?,?,?)", (self.user_id, marka.get().strip(), model.get().strip(), number.get().strip().upper(), color.get().strip()))
                self.db.commit()
                for entry in (marka, model, number, color): entry.delete(0, "end")
                load_vehicles()
            except sqlite3.IntegrityError:
                messagebox.showerror("Xato", "Bu davlat raqami mavjud")

        ttk.Button(left, text="Avtomobil qo'shish", command=add_vehicle).pack(fill="x", pady=(18, 0))
        load_vehicles()

        form = ttk.Frame(tab_trip, padding=15)
        form.pack(side="left", fill="y")
        vehicle_combo = ttk.Combobox(form, width=35, state="readonly")
        ttk.Label(form, text="Avtomobil:").pack(anchor="w")
        vehicle_combo.pack()
        from_entry = self.form_field(form, "Jo'nash joyi:", 35)
        to_entry = self.form_field(form, "Borish joyi:", 35)
        time_entry = self.form_field(form, "Jo'nash vaqti (YYYY-MM-DD HH:MM):", 35)
        seats_entry = self.form_field(form, "Bo'sh joylar:", 35)
        price_entry = self.form_field(form, "Bir joy narxi:", 35)
        women_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(form, text="Faqat ayol yo'lovchilar", variable=women_var).pack(anchor="w", pady=8)

        def load_vehicle_options():
            rows = self.db.execute("SELECT id,marka,model,davlat_raqami FROM vehicles WHERE haydovchi_id=?", (self.user_id,)).fetchall()
            values = [f"{r['id']} - {r['marka']} {r['model']} ({r['davlat_raqami']})" for r in rows]
            vehicle_combo["values"] = values
            if values: vehicle_combo.set(values[0])

        def create_route(a, b):
            row = self.db.execute("SELECT id FROM routes WHERE qayerdan=? AND qayerga=?", (a, b)).fetchone()
            if row: return row["id"]
            cur = self.db.execute("INSERT INTO routes(qayerdan,qayerga) VALUES(?,?)", (a, b))
            self.db.commit()
            return cur.lastrowid

        def publish():
            if not vehicle_combo.get():
                messagebox.showwarning("Diqqat", "Avtomobil qo'shing")
                return
            try:
                vehicle_id = int(vehicle_combo.get().split(" - ", 1)[0])
                departure = datetime.strptime(time_entry.get().strip(), "%Y-%m-%d %H:%M")
                seats = int(seats_entry.get().strip())
                price = float(price_entry.get().strip())
                if seats < 1 or price < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Xato", "Vaqt, joy yoki narx noto'g'ri")
                return
            if not from_entry.get().strip() or not to_entry.get().strip():
                messagebox.showwarning("Diqqat", "Yo'nalishni kiriting")
                return
            route_id = create_route(from_entry.get().strip(), to_entry.get().strip())
            self.db.execute("INSERT INTO trips(haydovchi_id,avtomobil_id,yonalish_id,j_nash_vaqti,umumiy_joylar,qolgan_joylar,narx,faqat_ayol) VALUES(?,?,?,?,?,?,?,?)", (self.user_id, vehicle_id, route_id, departure.strftime("%Y-%m-%d %H:%M:%S"), seats, seats, price, int(women_var.get())))
            self.db.commit()
            load_trips()
            messagebox.showinfo("Muvaffaqiyat", "Qatnov e'loni chiqarildi")

        ttk.Button(form, text="E'lon qilish", command=publish).pack(fill="x", pady=(18, 0))
        load_vehicle_options()

        trip_table = self.make_table(tab_trip, ["ID", "Yo'nalish", "Vaqt", "Joy", "Narx", "Holat"], [55, 220, 150, 75, 100, 100])

        def load_trips():
            trip_table.delete(*trip_table.get_children())
            rows = self.db.execute("""
                SELECT t.*,r.qayerdan,r.qayerga FROM trips t
                JOIN routes r ON r.id=t.yonalish_id
                WHERE t.haydovchi_id=? ORDER BY t.j_nash_vaqti DESC
            """, (self.user_id,)).fetchall()
            for r in rows:
                trip_table.insert("", "end", values=(r["id"], f"{r['qayerdan']} -> {r['qayerga']}", r["j_nash_vaqti"], f"{r['qolgan_joylar']}/{r['umumiy_joylar']}", r["narx"], r["holat"]))

        load_trips()

        passenger_table = self.make_table(tab_passengers, ["Bron", "Yo'nalish", "Vaqt", "Yo'lovchi", "Telefon", "Olib ketish manzili", "Holat"], [55, 180, 150, 130, 120, 220, 90], 16)

        def load_passengers():
            passenger_table.delete(*passenger_table.get_children())
            rows = self.db.execute("""
                SELECT b.id bron_id,b.holat,b.olib_ketish_manzili,t.j_nash_vaqti,
                       r.qayerdan,r.qayerga,u.ism,u.telefon
                FROM trips t JOIN routes r ON r.id=t.yonalish_id
                JOIN bookings b ON b.qatnov_id=t.id JOIN users u ON u.id=b.yolovchi_id
                WHERE t.haydovchi_id=? ORDER BY t.j_nash_vaqti DESC
            """, (self.user_id,)).fetchall()
            for r in rows:
                passenger_table.insert("", "end", values=(r["bron_id"], f"{r['qayerdan']} -> {r['qayerga']}", r["j_nash_vaqti"], r["ism"], r["telefon"], r["olib_ketish_manzili"], r["holat"]))

        rating_frame = ttk.Frame(tab_template, padding=15)
        rating_frame.pack(side="left", fill="y")
        rating_label = ttk.Label(rating_frame, text="Reyting: 0.00", font=("Segoe UI", 14, "bold"))
        rating_label.pack(pady=10)

        template_vehicle = ttk.Combobox(rating_frame, width=33, state="readonly")
        ttk.Label(rating_frame, text="Avtomobil:").pack(anchor="w")
        template_vehicle.pack()
        template_from = self.form_field(rating_frame, "Jo'nash:", 33)
        template_to = self.form_field(rating_frame, "Borish:", 33)
        template_seats = self.form_field(rating_frame, "Joylar:", 33)
        template_price = self.form_field(rating_frame, "Narx:", 33)
        template_women = tk.BooleanVar(value=False)
        ttk.Checkbutton(rating_frame, text="Faqat ayollar", variable=template_women).pack(anchor="w", pady=8)

        def update_vehicle_template():
            rows = self.db.execute("SELECT id,marka,model FROM vehicles WHERE haydovchi_id=?", (self.user_id,)).fetchall()
            vals = [f"{r['id']} - {r['marka']} {r['model']}" for r in rows]
            template_vehicle["values"] = vals
            if vals: template_vehicle.set(vals[0])

        def save_template():
            if not template_vehicle.get():
                messagebox.showwarning("Diqqat", "Avtomobil tanlang")
                return
            try:
                vehicle_id = int(template_vehicle.get().split(" - ", 1)[0])
                seats = int(template_seats.get())
                price = float(template_price.get())
                if seats < 1 or price < 0: raise ValueError
            except ValueError:
                messagebox.showerror("Xato", "Joy yoki narx noto'g'ri")
                return
            if not template_from.get().strip() or not template_to.get().strip():
                messagebox.showwarning("Diqqat", "Yo'nalishni kiriting")
                return
            route_id = create_route(template_from.get().strip(), template_to.get().strip())
            self.db.execute("INSERT INTO trip_templates(haydovchi_id,yonalish_id,avtomobil_id,umumiy_joylar,narx,faqat_ayol) VALUES(?,?,?,?,?,?)", (self.user_id, route_id, vehicle_id, seats, price, int(template_women.get())))
            self.db.commit()
            load_templates()
            messagebox.showinfo("Muvaffaqiyat", "Shablon saqlandi")

        ttk.Button(rating_frame, text="Shablon saqlash", command=save_template).pack(fill="x", pady=10)

        template_table = self.make_table(rating_frame, ["ID", "Yo'nalish", "Joy", "Narx"])

        def load_templates():
            template_table.delete(*template_table.get_children())
            rows = self.db.execute("""SELECT t.id,t.umumiy_joylar,t.narx,r.qayerdan,r.qayerga
                FROM trip_templates t JOIN routes r ON r.id=t.yonalish_id WHERE t.haydovchi_id=?""", (self.user_id,)).fetchall()
            for r in rows:
                template_table.insert("", "end", values=(r["id"], f"{r['qayerdan']} -> {r['qayerga']}", r["umumiy_joylar"], r["narx"]))

        def load_rating():
            row = self.db.execute("SELECT COALESCE(AVG(ball),0) reyting,COUNT(*) soni FROM ratings WHERE haydovchi_id=?", (self.user_id,)).fetchone()
            rating_label.configure(text=f"Reyting: {row['reyting']:.2f} ({row['soni']} ta baho)")

        template_time = self.form_field(rating_frame, "Shablondan vaqt (YYYY-MM-DD HH:MM):", 33)

        def publish_template():
            selected = template_table.selection()
            if not selected:
                messagebox.showwarning("Diqqat", "Shablonni tanlang")
                return
            template_id = template_table.item(selected[0])["values"][0]
            template = self.db.execute("SELECT * FROM trip_templates WHERE id=?", (template_id,)).fetchone()
            if not template:
                messagebox.showwarning("Diqqat", "Shablon topilmadi")
                return
            try:
                departure = datetime.strptime(template_time.get().strip(), "%Y-%m-%d %H:%M")
            except ValueError:
                messagebox.showerror("Xato", "Vaqt noto'g'ri")
                return
            seats = template["umumiy_joylar"]
            self.db.execute("INSERT INTO trips(haydovchi_id,avtomobil_id,yonalish_id,j_nash_vaqti,umumiy_joylar,qolgan_joylar,narx,faqat_ayol) VALUES(?,?,?,?,?,?,?,?)", (self.user_id, template["avtomobil_id"], template["yonalish_id"], departure.strftime("%Y-%m-%d %H:%M:%S"), seats, seats, template["narx"], template["faqat_ayol"]))
            self.db.commit()
            load_trips()
            messagebox.showinfo("Muvaffaqiyat", "Shablondan qatnov e'loni chiqarildi")

        ttk.Button(rating_frame, text="Tanlangan shablondan e'lon qilish", command=publish_template).pack(fill="x", pady=8)

        update_vehicle_template()
        load_templates()
        load_rating()
        load_passengers()

    def build_passenger_ui(self, notebook):
        search_tab = ttk.Frame(notebook)
        bookings_tab = ttk.Frame(notebook)
        rating_tab = ttk.Frame(notebook)
        notebook.add(search_tab, text="Qatnov qidirish")
        notebook.add(bookings_tab, text="Bronlarim")
        notebook.add(rating_tab, text="Baho / shikoyat")

        controls = ttk.Frame(search_tab, padding=10)
        controls.pack(fill="x")
        from_entry = ttk.Entry(controls, width=18)
        to_entry = ttk.Entry(controls, width=18)
        date_entry = ttk.Entry(controls, width=14)
        date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        for text, widget in (("Jo'nash:", from_entry),("Borish:", to_entry),("Sana:", date_entry)):
            ttk.Label(controls, text=text).pack(side="left", padx=(0, 4))
            widget.pack(side="left", padx=(0, 12))

        result_table = self.make_table(search_tab, ["ID", "Haydovchi", "Yo'nalish", "Vaqt", "Joy", "Narx", "Reyting", "Ayollar"], [55, 130, 180, 150, 55, 90, 75, 90], 14)

        def search():
            self.refresh_trip_statuses()
            result_table.delete(*result_table.get_children())
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            rows = self.db.execute("""
                SELECT t.*,r.qayerdan,r.qayerga,u.ism haydovchi,
                (SELECT COALESCE(AVG(ball),0) FROM ratings ra WHERE ra.haydovchi_id=t.haydovchi_id) reyting
                FROM trips t JOIN routes r ON r.id=t.yonalish_id JOIN users u ON u.id=t.haydovchi_id
                WHERE r.qayerdan LIKE ? AND r.qayerga LIKE ? AND substr(t.j_nash_vaqti,1,10)=?
                AND t.j_nash_vaqti>? AND t.qolgan_joylar>0 AND t.holat='ochiq' AND u.bloklangan=0
                ORDER BY t.j_nash_vaqti
            """, (f"%{from_entry.get().strip()}%", f"%{to_entry.get().strip()}%", date_entry.get().strip(), now)).fetchall()
            user = self.db.execute("SELECT jins FROM users WHERE id=?", (self.user_id,)).fetchone()
            for r in rows:
                if r["faqat_ayol"] and user["jins"] != "ayol":
                    continue
                result_table.insert("", "end", values=(r["id"], r["haydovchi"], f"{r['qayerdan']} -> {r['qayerga']}", r["j_nash_vaqti"], r["qolgan_joylar"], r["narx"], f"{r['reyting']:.1f}", "Ha" if r["faqat_ayol"] else "Yo'q"))

        ttk.Button(controls, text="Qidirish", command=search).pack(side="left")

        def book_selected():
            selected = result_table.selection()
            if not selected:
                messagebox.showwarning("Diqqat", "Qatnovni tanlang")
                return
            trip_id = result_table.item(selected[0])["values"][0]
            trip = self.db.execute("SELECT * FROM trips WHERE id=?", (trip_id,)).fetchone()
            if trip["holat"] != "ochiq" or trip["qolgan_joylar"] <= 0:
                messagebox.showwarning("Diqqat", "Joy qolmadi")
                return
            user = self.db.execute("SELECT jins FROM users WHERE id=?", (self.user_id,)).fetchone()
            if trip["faqat_ayol"] and user["jins"] != "ayol":
                messagebox.showwarning("Diqqat", "Bu qatnov faqat ayollar uchun")
                return
            address_window = tk.Toplevel(self.root)
            address_window.title("Olib ketish manzili")
            address_window.geometry("420x160")
            address_window.transient(self.root)
            address_window.grab_set()
            address = self.form_field(address_window, "Manzil:", 45)

            def confirm():
                if not address.get().strip():
                    messagebox.showwarning("Diqqat", "Manzilni kiriting")
                    return
                try:
                    self.db.execute("BEGIN")
                    current = self.db.execute("SELECT qolgan_joylar,holat FROM trips WHERE id=?", (trip_id,)).fetchone()
                    if current["holat"] != "ochiq" or current["qolgan_joylar"] <= 0:
                        raise sqlite3.IntegrityError("Joy qolmadi")
                    self.db.execute("INSERT INTO bookings(qatnov_id,yolovchi_id,olib_ketish_manzili,yaratilgan_vaqti) VALUES(?,?,?,?)", (trip_id, self.user_id, address.get().strip(), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    remaining = current["qolgan_joylar"] - 1
                    status = "toldi" if remaining == 0 else "ochiq"
                    self.db.execute("UPDATE trips SET qolgan_joylar=?,holat=? WHERE id=?", (remaining, status, trip_id))
                    self.db.commit()
                    address_window.destroy()
                    messagebox.showinfo("Muvaffaqiyat", "Joy band qilindi")
                    search()
                    load_bookings()
                except sqlite3.IntegrityError as exc:
                    self.db.rollback()
                    messagebox.showerror("Xato", str(exc))

            ttk.Button(address_window, text="Band qilish", command=confirm).pack(fill="x", padx=25, pady=12)

        ttk.Button(controls, text="Joy band qilish", command=book_selected).pack(side="left")

        booking_table = self.make_table(bookings_tab, ["Bron", "Yo'nalish", "Vaqt", "Haydovchi", "Manzil", "Holat"], [55, 210, 150, 130, 220, 90], 16)

        def load_bookings():
            booking_table.delete(*booking_table.get_children())
            rows = self.db.execute("""
                SELECT b.*,t.j_nash_vaqti,r.qayerdan,r.qayerga,u.ism haydovchi
                FROM bookings b JOIN trips t ON t.id=b.qatnov_id JOIN routes r ON r.id=t.yonalish_id
                JOIN users u ON u.id=t.haydovchi_id WHERE b.yolovchi_id=? ORDER BY t.j_nash_vaqti DESC
            """, (self.user_id,)).fetchall()
            for r in rows:
                booking_table.insert("", "end", values=(r["id"], f"{r['qayerdan']} -> {r['qayerga']}", r["j_nash_vaqti"], r["haydovchi"], r["olib_ketish_manzili"], r["holat"]))

        def cancel_booking():
            selected = booking_table.selection()
            if not selected:
                messagebox.showwarning("Diqqat", "Bronni tanlang")
                return
            booking_id = booking_table.item(selected[0])["values"][0]
            booking = self.db.execute("SELECT b.*,t.j_nash_vaqti,t.id trip_id,t.qolgan_joylar,t.umumiy_joylar FROM bookings b JOIN trips t ON t.id=b.qatnov_id WHERE b.id=?", (booking_id,)).fetchone()
            if booking["holat"] != "band":
                messagebox.showwarning("Diqqat", "Bron faol emas")
                return
            departure = datetime.strptime(booking["j_nash_vaqti"], "%Y-%m-%d %H:%M:%S")
            if departure - datetime.now() < timedelta(hours=2):
                messagebox.showwarning("Cheklov", "Jo'nashga 2 soatdan kam vaqt qoldi")
                return
            self.db.execute("UPDATE bookings SET holat='bekor' WHERE id=?", (booking_id,))
            remaining = min(booking["umumiy_joylar"], booking["qolgan_joylar"] + 1)
            self.db.execute("UPDATE trips SET qolgan_joylar=?,holat='ochiq' WHERE id=?", (remaining, booking["trip_id"]))
            self.db.commit()
            messagebox.showinfo("Muvaffaqiyat", "Bron bekor qilindi")
            load_bookings()

        ttk.Button(bookings_tab, text="Bronni bekor qilish", command=cancel_booking).pack(pady=8)

        rating_controls = ttk.Frame(rating_tab, padding=15)
        rating_controls.pack(side="left", fill="y")
        rating_combo = ttk.Combobox(rating_controls, width=38, state="readonly")
        ttk.Label(rating_controls, text="Baholanadigan safar:").pack(anchor="w")
        rating_combo.pack()
        rating_score = ttk.Combobox(rating_controls, values=[1,2,3,4,5], state="readonly", width=10)
        rating_score.set(5)
        ttk.Label(rating_controls, text="Baho:").pack(anchor="w", pady=(10,2))
        rating_score.pack(anchor="w")
        rating_comment = tk.Text(rating_controls, width=38, height=5)
        ttk.Label(rating_controls, text="Izoh:").pack(anchor="w", pady=(10,2))
        rating_comment.pack()

        complaint_combo = ttk.Combobox(rating_controls, width=38, state="readonly")
        ttk.Label(rating_controls, text="Shikoyat haydovchisi:").pack(anchor="w", pady=(18,2))
        complaint_combo.pack()
        complaint_text = tk.Text(rating_controls, width=38, height=5)
        ttk.Label(rating_controls, text="Shikoyat matni:").pack(anchor="w", pady=(10,2))
        complaint_text.pack()

        def load_rating_options():
            rows = self.db.execute("""
                SELECT b.id bron_id,t.id trip_id,t.haydovchi_id,u.ism,t.j_nash_vaqti
                FROM bookings b JOIN trips t ON t.id=b.qatnov_id JOIN users u ON u.id=t.haydovchi_id
                WHERE b.yolovchi_id=? AND b.holat='band' AND t.j_nash_vaqti<?
                AND NOT EXISTS(SELECT 1 FROM ratings r WHERE r.qatnov_id=t.id AND r.yolovchi_id=b.yolovchi_id)
            """, (self.user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))).fetchall()
            rating_combo._rows = rows
            vals = [f"{r['bron_id']} - {r['ism']} - {r['j_nash_vaqti']}" for r in rows]
            rating_combo["values"] = vals
            if vals: rating_combo.set(vals[0])

            drivers = self.db.execute("""
                SELECT DISTINCT u.id,u.ism FROM users u JOIN trips t ON t.haydovchi_id=u.id
                JOIN bookings b ON b.qatnov_id=t.id WHERE b.yolovchi_id=?
            """, (self.user_id,)).fetchall()
            complaint_combo._rows = drivers
            complaint_vals = [f"{d['id']} - {d['ism']}" for d in drivers]
            complaint_combo["values"] = complaint_vals
            if complaint_vals: complaint_combo.set(complaint_vals[0])

        def submit_rating():
            if not rating_combo.get() or not hasattr(rating_combo, "_rows"):
                messagebox.showwarning("Diqqat", "Baholanadigan safar yo'q")
                return
            idx = rating_combo.current()
            if idx < 0: return
            row = rating_combo._rows[idx]
            self.db.execute("INSERT INTO ratings(qatnov_id,yolovchi_id,haydovchi_id,ball,izoh) VALUES(?,?,?,?,?)", (row["trip_id"], self.user_id, row["haydovchi_id"], int(rating_score.get()), rating_comment.get("1.0", "end").strip()))
            self.db.execute("UPDATE bookings SET holat='yakunlangan' WHERE id=?", (row["bron_id"],))
            self.db.commit()
            messagebox.showinfo("Muvaffaqiyat", "Baho saqlandi")
            rating_comment.delete("1.0", "end")
            load_rating_options()

        def submit_complaint():
            if not complaint_combo.get():
                messagebox.showwarning("Diqqat", "Haydovchini tanlang")
                return
            idx = complaint_combo.current()
            row = complaint_combo._rows[idx]
            text = complaint_text.get("1.0", "end").strip()
            if not text:
                messagebox.showwarning("Diqqat", "Shikoyat matnini kiriting")
                return
            self.db.execute("INSERT INTO complaints(yolovchi_id,haydovchi_id,matn) VALUES(?,?,?)", (self.user_id, row["id"], text))
            self.db.commit()
            complaint_text.delete("1.0", "end")
            messagebox.showinfo("Muvaffaqiyat", "Shikoyat qabul qilindi")

        ttk.Button(rating_controls, text="Baho yuborish", command=submit_rating).pack(fill="x", pady=(12,4))
        ttk.Button(rating_controls, text="Shikoyat yuborish", command=submit_complaint).pack(fill="x")

        search()
        load_bookings()
        load_rating_options()

    def build_dispatcher_ui(self, notebook):
        trips_tab = ttk.Frame(notebook)
        complaints_tab = ttk.Frame(notebook)
        notebook.add(trips_tab, text="Barcha qatnovlar")
        notebook.add(complaints_tab, text="Shikoyatlar")

        trip_table = self.make_table(trips_tab, ["ID", "Haydovchi", "Yo'nalish", "Vaqt", "Joy", "Narx", "Holat", "Blok"], [55,130,220,150,80,90,100,70], 18)

        def load_trips():
            self.refresh_trip_statuses()
            trip_table.delete(*trip_table.get_children())
            rows = self.db.execute("""
                SELECT t.*,r.qayerdan,r.qayerga,u.ism haydovchi,u.bloklangan
                FROM trips t JOIN routes r ON r.id=t.yonalish_id JOIN users u ON u.id=t.haydovchi_id
                ORDER BY t.j_nash_vaqti DESC
            """).fetchall()
            for r in rows:
                trip_table.insert("", "end", values=(r["id"], r["haydovchi"], f"{r['qayerdan']} -> {r['qayerga']}", r["j_nash_vaqti"], f"{r['qolgan_joylar']}/{r['umumiy_joylar']}", r["narx"], r["holat"], "Ha" if r["bloklangan"] else "Yo'q"))

        ttk.Button(trips_tab, text="Yangilash", command=load_trips).pack(pady=8)

        complaint_table = self.make_table(complaints_tab, ["ID", "Yo'lovchi", "Haydovchi", "Matn", "Holat"], [55,130,130,420,100], 18)

        def load_complaints():
            complaint_table.delete(*complaint_table.get_children())
            rows = self.db.execute("""
                SELECT c.*,d.ism haydovchi,p.ism yolovchi FROM complaints c
                JOIN users d ON d.id=c.haydovchi_id JOIN users p ON p.id=c.yolovchi_id
                WHERE c.holat='yangi'
            """).fetchall()
            for r in rows:
                complaint_table.insert("", "end", values=(r["id"], r["yolovchi"], r["haydovchi"], r["matn"], r["holat"]))

        def process_complaint():
            selected = complaint_table.selection()
            if not selected:
                messagebox.showwarning("Diqqat", "Shikoyatni tanlang")
                return
            complaint_id = complaint_table.item(selected[0])["values"][0]
            row = self.db.execute("SELECT * FROM complaints WHERE id=?", (complaint_id,)).fetchone()
            if messagebox.askyesno("Haydovchini bloklash", "Bu haydovchini bloklashni tasdiqlaysizmi?"):
                self.db.execute("UPDATE users SET bloklangan=1 WHERE id=?", (row["haydovchi_id"],))
            self.db.execute("UPDATE complaints SET holat='ko'rib_chiqildi' WHERE id=?", (complaint_id,))
            self.db.commit()
            load_complaints()
            load_trips()

        ttk.Button(complaints_tab, text="Shikoyatni ko'rib chiqish", command=process_complaint).pack(pady=8)
        load_trips()
        load_complaints()

    def on_close(self):
        self.db.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = RideGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
