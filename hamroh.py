#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Toshkent-viloyat yo'nalish tizimi uchun yagona ishga tushirish fayli."""

import sys


def main():
    """GUI yoki terminal interfeysini ishga tushiradi."""
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "web"

    if mode in ("web", "browser", "server"):
        from web_app import app

        app.run(host="127.0.0.1", port=5000, debug=True)
        return

    if mode in ("cli", "terminal", "console"):
        from app import RideApp

        RideApp().main()
        return

    if mode in ("gui", "desktop"):
        import tkinter as tk

        from gui_app import RideGUI

        root = tk.Tk()
        app = RideGUI(root)
        root.protocol("WM_DELETE_WINDOW", app.on_close)
        root.mainloop()
        return

    print("Noto'g'ri rejim. Foydalanish:")
    print("  python hamroh.py web")
    print("  python hamroh.py gui")
    print("  python hamroh.py cli")


if __name__ == "__main__":
    main()
