#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def dialog():
    """Ikki shaxs o'rtasidagi oddiy dialog"""
    
    shaxs1 = "Ali"
    shaxs2 = "Vali"
    
    dialog_malumotlari = [
        (shaxs1, "Salom Vali, qandaysan?"),
        (shaxs2, "Salom Ali! Yaxshiman, rahmat. Sizchi?"),
        (shaxs1, "Men ham yaxshi. Bugun nima qilmoqchisiz?"),
        (shaxs2, "Kutubxonaga bormoqchiman. Sizga ham qo'shilib bormoqchimisiz?"),
        (shaxs1, "Albatta, men ham kitob o'qimoqchiman. Keling birga bormiz."),
        (shaxs2, "Yaxshi fikr! Keling, yo'lga tushamiz."),
    ]
    
    print("=" * 40)
    print("DIALOG: Ali va Vali")
    print("=" * 40)
    
    for shaxs, soz in dialog_malumotlari:
        print(f"{shaxs}: {soz}")
    
    print("=" * 40)


def interaktiv_dialog():
    """Foydalanuvchi kiritishi bilan interaktiv dialog"""
    
    print("\n--- INTERAKTIV DIALOG ---")
    ism1 = input("1-shaxs ismini kiriting: ")
    ism2 = input("2-shaxs ismini kiriting: ")
    
    print(f"\n{ism1} va {ism2} o'rtasidagi dialogni boshlaymiz:")
    print("(To'xtatish uchun 'stop' deb yozing)\n")
    
    joriy_shaxs = ism1
    boshqa_shaxs = ism2
    
    while True:
        soz = input(f"{joriy_shaxs}: ")
        if soz.lower() == 'stop':
            print("Dialog tugatildi.")
            break
        
        # Shaxslarni almashtirish
        joriy_shaxs, boshqa_shaxs = boshqa_shaxs, joriy_shaxs


if __name__ == "__main__":
    # Oddiy dialog
    dialog()
    
    # Interaktiv dialog (ixtiyoriy)
    javob = input("\nInteraktiv dialogni boshlaysizmi? (ha/yo'q): ")
    if javob.lower() in ['ha', 'yes', 'y']:
        interaktiv_dialog()