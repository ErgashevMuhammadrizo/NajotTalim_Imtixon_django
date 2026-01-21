# Expense Tracker Web Ilova

**Expense Tracker** — bu foydalanuvchilarga kirim va chiqimlarni kuzatib borish, balansni hisoblash va moliyaviy holatini vizual tarzda ko‘rsatishga yordam beradigan web ilova. Loyihada Django backend va Bootstrap frontend ishlatilgan.

---

## Asosiy Xususiyatlar

- **Foydalanuvchi Ro‘yxatdan O‘tish va Kirish**
  - Email va foydalanuvchi nomi orqali ro‘yxatdan o‘tish.
  - Login va logout funksiyalari.
  
- **Kirim va Chiqimlarni Kuzatish**
  - Tez kirim/chiqim qo‘shish modallari.
  - Jami kirim, jami chiqim va joriy balansni ko‘rsatish.
  - Balans real vaqt rejimida yangilanadi (UZS va USD valyutalar).

- **Kategoriya Bo‘yicha Tahlil**
  - Kirim va chiqimlarni turkumlar bo‘yicha ajratish.
  - Dashboardda grafiklar bilan ko‘rsatish.

- **Hisobotlar**
  - XLS (Excel) faylga eksport qilish.
  - Statistikalar va o‘sish/ kamayish foizlarini ko‘rsatish.

- **Ko‘p tilli qo‘llab-quvvatlash**
  - Django `i18n` orqali sahifalarni turli tillarda ko‘rsatish.

---

## Texnologiyalar

- Backend: **Python 3.12**, **Django 6.0.1**
- Frontend: **HTML**, **CSS**, **Bootstrap 5**, **JavaScript**
- Database: **SQLite** (development uchun)
- Grafiklar: **Plotly.js**
- Fayl eksport: **xlwt**

---
# defolt userlar
1. admin ["user:admin , password:123"]
2. user ["user:rizo , password:Rizo1234"]

## O‘rnatish va Ishga Tushirish

1. **Virtual muhit yaratish va faollashtirish**

```bash
python -m venv venv
source venv/bin/activate   # Linux / macOS
venv\Scripts\activate      # Windows

