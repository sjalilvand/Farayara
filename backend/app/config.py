"""تنظیمات سامانه — مقادیر از متغیرهای محیطی یا فایل .env خوانده می‌شود"""
import os
import secrets
from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "فرایارا"
    app_name_en: str = "Farayara"
    version: str = "1.0.0"
    debug: bool = False

    # پایگاه داده
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'farayara.db'}"

    # امنیت
    secret_key: str = os.environ.get("FARAYARA_SECRET_KEY", "")
    access_token_expire_minutes: int = 120
    refresh_token_expire_days: int = 14
    algorithm: str = "HS256"

    # مسیر فایل‌ها
    upload_dir: str = str(BASE_DIR / "data" / "uploads")
    backup_dir: str = str(BASE_DIR / "data" / "backups")

    # محدودیت‌ها
    max_upload_size_mb: int = 20
    default_page_size: int = 20
    max_page_size: int = 100
    rate_limit_per_minute: int = 300

    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    class Config:
        env_prefix = "FARAYARA_"
        env_file = ".env"
        extra = "ignore"

    def ensure_dirs(self):
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        Path(self.backup_dir).mkdir(parents=True, exist_ok=True)
        Path(self.database_url.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
if not settings.secret_key:
    # کلید پیش‌فرض برای استقرار آزمایشی؛ در محیط عملیاتی حتماً FARAYARA_SECRET_KEY تنظیم شود
    settings.secret_key = secrets.token_hex(32)
settings.ensure_dirs()
