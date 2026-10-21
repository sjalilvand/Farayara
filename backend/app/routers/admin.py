"""ممیزی، تنظیمات، پشتیبان‌گیری و اعلان‌ها (بخش‌های ۱۹، ۲۰ سند)"""
import sqlite3

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..audit import log_action
from ..config import settings
from ..database import get_db, engine
from ..deps import RequirePermission, get_current_user
from ..models import Notification, SystemSetting, User
from ..schemas import SettingIn, paginate

router = APIRouter(tags=["admin"])


@router.get("/audit-logs")
def audit_logs(
    actor: str | None = None, action: str | None = None, entity_type: str | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(30, ge=1, le=200),
    db: Session = Depends(get_db), user: User = Depends(RequirePermission("audit.view")),
):
    from ..models import AuditLog
    q = db.query(AuditLog).order_by(AuditLog.created_at.desc())
    if actor:
        q = q.filter(AuditLog.actor_username.contains(actor))
    if action:
        q = q.filter(AuditLog.action == action)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [{
            "id": a.id, "actor_username": a.actor_username, "action": a.action,
            "entity_type": a.entity_type, "entity_id": a.entity_id, "entity_code": a.entity_code,
            "detail": a.detail, "ip": a.ip, "created_at": a.created_at,
        } for a in rows],
        "total": total, "page": page, "page_size": page_size,
    }


@router.get("/audit-logs/actions")
def audit_actions(db: Session = Depends(get_db), user: User = Depends(RequirePermission("audit.view"))):
    from ..models import AuditLog
    rows = db.query(AuditLog.action, func.count(AuditLog.id)).group_by(AuditLog.action).all()
    return [{"action": a, "count": c} for a, c in rows]


@router.get("/settings")
def get_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(SystemSetting).all()
    return {r.key: {"value": r.value, "description": r.description, "updated_at": r.updated_at} for r in rows}


@router.put("/settings")
def put_setting(body: SettingIn, db: Session = Depends(get_db), user: User = Depends(RequirePermission("system.settings"))):
    row = db.get(SystemSetting, body.key)
    if row is None:
        row = SystemSetting(key=body.key)
        db.add(row)
    row.value = body.value if isinstance(body.value, dict) else {"value": body.value}
    row.description = body.description or row.description
    row.updated_by = user.username
    log_action(db, user, "update_setting", "system_setting", body.key)
    db.commit()
    return {"ok": True}


@router.post("/admin/backup")
def backup(db: Session = Depends(get_db), user: User = Depends(RequirePermission("system.admin"))):
    """پشتیبان‌گیری سازگار با SQLite از طریق backup API — کپی ساده فایل در حین WAL روش اصلی نیست (بخش ۱۶/۲۰)"""
    import os
    from datetime import datetime, timezone
    from pathlib import Path
    settings.ensure_dirs()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = Path(settings.backup_dir) / f"farayara_backup_{ts}.db"
    src = sqlite3.connect(settings.database_url.replace("sqlite:///", ""))
    dst = sqlite3.connect(str(out_path))
    with dst:
        src.backup(dst)
    src.close()
    dst.close()
    log_action(db, user, "backup", "system", None, None, {"file": out_path.name})
    db.commit()
    data = Path(out_path).read_bytes()
    return Response(
        content=data, media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={out_path.name}"},
    )


@router.get("/notifications")
def my_notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Notification).filter(Notification.user_id == user.id).order_by(
        Notification.created_at.desc()).limit(50).all()
    return [{"id": n.id, "title": n.title, "body": n.body, "link": n.link,
             "is_read": n.is_read, "created_at": n.created_at} for n in rows]


@router.post("/notifications/{notification_id}/read")
def read_notification(notification_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    n = db.get(Notification, notification_id)
    if n and n.user_id == user.id:
        n.is_read = True
        db.commit()
    return {"ok": True}


@router.get("/system/info")
def system_info(user: User = Depends(get_current_user)):
    from .. import __version__
    return {
        "app_name": settings.app_name, "app_name_en": settings.app_name_en,
        "version": __version__, "database": "SQLite (WAL)",
        "max_upload_size_mb": settings.max_upload_size_mb,
    }
