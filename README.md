# فرایارا (Farayara)

**سامانه یکپارچه مدیریت فرایندها، فرم‌ها، کاتالوگ داده، آزمون‌های مشاوره و قراردادها**

پیاده‌سازی نسخه نخست بر اساس «سند جامع نیازمندی‌ها و طراحی سامانه فرایارا» — نسخه ۱.۰

| مورد | انتخاب فنی |
|------|-----------|
| بک‌اند | Python 3.10+ / FastAPI / SQLAlchemy 2 / Pydantic v2 |
| پایگاه داده | SQLite (WAL + foreign_keys + busy_timeout) |
| احراز هویت | JWT (access/refresh) + هش رمز Argon2 |
| فرانت‌اند | React 18 + TypeScript + Vite |
| ویرایشگر BPMN | bpmn-js |
| فرم‌ساز | dnd-kit (کشیدن و رهاکردن) |
| ویرایشگر قرارداد | Tiptap (فارسی RTL) |
| نمودارها | Recharts |
| رابط کاربری | فارسی، راست‌به‌چپ، فونت وزیرمتن، تاریخ شمسی |

## ساختار پروژه

```
Farayara/
├── backend/                # بک‌اند FastAPI
│   ├── app/
│   │   ├── main.py         # نقطه ورود
│   │   ├── models.py       # ۴۶ جدول مطابق بخش ۱۷ سند
│   │   ├── engines/        # موتور اجرای BPMN، نمره‌گذاری امن، رندر قرارداد
│   │   ├── routers/        # APIهای /api/v1
│   │   └── seed.py         # داده اولیه نمونه
│   ├── migrations/         # Alembic
│   └── tests/              # ۳۲ تست pytest (معیارهای پذیرش سند)
├── frontend/               # فرانت‌اند React (RTL فارسی)
│   └── src/pages/          # ۲۰ صفحه کاربردی
├── docs/index.html         # راهنمای کامل نصب، اجرا و استفاده
└── scripts/                # اسکریپت‌های کمکی
```

## شروع سریع

### پیش‌نیازها
- Python 3.10 یا جدیدتر
- Node.js 18 یا جدیدتر + npm

### ۱) بک‌اند

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # ویندوز: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.seed               # ایجاد داده اولیه و کاربران نمونه
uvicorn app.main:app --reload --port 8000
```

مستندات تعاملی API: `http://localhost:8000/api/docs`

### ۲) فرانت‌اند

```bash
cd frontend
npm install
npm run dev
```

سامانه: `http://localhost:5173`

### حساب‌های نمونه (پس از seed)

| نقش | نام کاربری | رمز عبور |
|-----|-----------|----------|
| مدیر سامانه | `admin` | `Admin@1234` |
| مدیر سازمان | `orgadmin` | `Org@1234` |
| طراح فرایند | `pdesigner` | `Proc@1234` |
| طراح فرم | `fdesigner` | `Form@1234` |
| متولی داده | `steward` | `Data@1234` |
| متخصص آزمون | `assessor` | `Assess@1234` |
| کارشناس قرارداد | `contractx` | `Contract@1234` |
| کاربر اجرایی / پاسخ‌دهنده | `operator` | `Oper@1234` |
| ناظر/حسابرس | `auditor` | `Audit@1234` |

> ⚠️ این رمزها فقط برای استقرار آزمایشی هستند؛ در محیط عملیاتی حتماً تغییر دهید و `FARAYARA_SECRET_KEY` را تنظیم کنید.

## تست‌ها

```bash
cd backend
.venv/bin/python -m pytest tests/ -v
```

۳۲ تست شامل معیارهای پذیرش کلیدی سند (AC-01 تا AC-16): گردش نسخه‌بندی فرم و فرایند، جلوگیری از تکمیل تکراری وظیفه، فراوانی فیلدها، مثال‌های مرجع نمره‌گذاری، انجماد قرارداد، کنترل مجوز و ممیزی.

## مهاجرت دیتابیس (Alembic)

```bash
cd backend
alembic upgrade head          # اعمال مهاجرت‌ها
alembic revision --autogenerate -m "..."   # تولید مهاجرت جدید پس از تغییر مدل‌ها
```

## پشتیبان‌گیری

از رابط کاربری (تنظیمات → پشتیبان‌گیری) یا مستقیم:

```bash
curl -X POST http://localhost:8000/api/v1/admin/backup -H "Authorization: Bearer TOKEN" -o backup.db
```

## محدودیت‌های شناخته‌شده نسخه نخست

- موتور اجرای فرایند محدود به: رویداد شروع/پایان ساده، User Task، مسیر ترتیبی، Exclusive Gateway (مطابق بخش ۵.۲ سند). عناصر دیگر قابل طراحی‌اند اما در انتشار اجرایی با پیام روشن مسدود می‌شوند.
- خروجی قرارداد به‌صورت HTML آماده چاپ ارائه می‌شود؛ تولید PDF/DOCX فارسی در فاز بعد (بخش ۲۲ سند) اضافه می‌شود.
- صف پس‌زمینه پایدار (Jobها) به‌صورت جدول ردیابی پیاده شده و اجرای سنگین (OCR، PDF) به فازهای بعدی موکول است.
- جست‌وجوی اینترنتی آزمون‌ها فقط متادیتای منابع را می‌آورد؛ ورود محتوا نیازمند بررسی مجوز حقوقی و تأیید متخصص است.

راهنمای کامل نصب، اجرا و استفاده از هر بخش: **[docs/index.html](docs/index.html)**
