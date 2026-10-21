"""ابزارهای مشترک: تولید کد نمایشی، کد رهگیری، یکسان‌سازی متن فارسی، هش فایل"""
import hashlib
import re

from sqlalchemy.orm import Session

from .models import SequenceCounter

CODE_PREFIXES = {
    "process": "PRC",
    "form": "FRM",
    "field": "FLD",
    "assessment": "ASM",
    "contract_template": "CTR-TPL",
    "contract": "CTR",
}


def next_code(db: Session, entity: str) -> str:
    """تولید کد نمایشی ترتیبی مانند PRC-000125"""
    key = CODE_PREFIXES.get(entity, entity.upper())
    counter = db.get(SequenceCounter, key)
    if counter is None:
        counter = SequenceCounter(key=key, value=0)
        db.add(counter)
    counter.value = int(counter.value or 0) + 1
    db.flush()
    width = 6 if key.startswith("CTR") else 6
    return f"{key}-{counter.value:0{width}d}"


def new_trace_code(db: Session, prefix: str = "TRK") -> str:
    counter = db.get(SequenceCounter, f"trace_{prefix}")
    if counter is None:
        counter = SequenceCounter(key=f"trace_{prefix}", value=0)
        db.add(counter)
    counter.value = int(counter.value or 0) + 1
    db.flush()
    return f"{prefix}-{counter.value:08d}"


# یکسان‌سازی «ی/ي» و «ک/ك» برای جست‌وجوی فارسی (بخش ۱۴)
_YK_MAP = str.maketrans({"ي": "ی", "ك": "ک", "ۀ": "ه", "ة": "ه", "أ": "ا", "إ": "ا", "ؤ": "و", "ئ": "ی"})


def normalize_fa(text: str | None) -> str:
    if not text:
        return ""
    t = text.translate(_YK_MAP)
    t = t.replace("\u200c", " ")  # نیم‌فاصله → فاصله
    t = re.sub(r"[\u064B-\u065F\u0670]", "", t)  # اعراب
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def flatten_dict(d: dict, parent: str = "") -> dict:
    """تبدیل دیکشنری تو در تو به کلیدهای نقطه‌ای: party_a.full_name"""
    items: dict = {}
    for k, v in (d or {}).items():
        key = f"{parent}.{k}" if parent else k
        if isinstance(v, dict):
            items.update(flatten_dict(v, key))
        else:
            items[key] = v
    return items
