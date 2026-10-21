# -*- coding: utf-8 -*-
"""پشتیبان‌گیری برنامه‌ریزی‌شده فرایارا — استفاده در cron (بخش ۲۰ سند)

نمونه cron روزانه ساعت ۲ بامداد:
    0 2 * * * /path/to/Farayara/scripts/backup.py
"""
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DB = BASE / "backend" / "data" / "farayara.db"
OUT_DIR = BASE / "backend" / "data" / "backups"


def main():
    if not DB.exists():
        print("پایگاه داده یافت نشد:", DB)
        sys.exit(1)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out = OUT_DIR / f"farayara_backup_{ts}.db"
    src = sqlite3.connect(str(DB))
    dst = sqlite3.connect(str(out))
    with dst:
        src.backup(dst)
    src.close()
    dst.close()
    print("پشتیبان ذخیره شد:", out)
    # نگهداری ۳۰ نسخه آخر
    backups = sorted(OUT_DIR.glob("farayara_backup_*.db"))
    for old in backups[:-30]:
        old.unlink()


if __name__ == "__main__":
    main()
