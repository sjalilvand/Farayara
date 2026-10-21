"""کمک‌متن ممیزی — ثبت رویدادهای حساس (بخش ۱۹ سند)"""
from fastapi import Request
from sqlalchemy.orm import Session

from .models import AuditLog


def log_action(
    db: Session,
    actor=None,
    action: str = "",
    entity_type: str | None = None,
    entity_id: str | None = None,
    entity_code: str | None = None,
    detail: dict | None = None,
    request: Request | None = None,
):
    """ثبت رویداد ممیزی — هرگز خطا ایجاد نمی‌کند تا عملیات اصلی مختل نشود"""
    try:
        ip = None
        if request is not None:
            ip = request.client.host if request.client else None
        entry = AuditLog(
            actor_id=getattr(actor, "id", None),
            actor_username=getattr(actor, "username", None),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_code=entity_code,
            detail=detail,
            ip=ip,
        )
        db.add(entry)
        db.flush()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
