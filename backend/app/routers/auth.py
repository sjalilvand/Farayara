"""روت‌های احراز هویت — ورود، تازه‌سازی توکن، خروج (بخش ۱۸ سند)"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..deps import get_current_user, user_permissions
from ..models import User
from ..schemas import LoginIn, RefreshIn
from ..security import create_access_token, create_refresh_token, decode_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

MAX_LOGIN_ATTEMPTS_NOTE = "محدودیت تلاش ورود در لایه reverse-proxy/Nginx قابل اعمال است"


def _user_payload(user: User, db: Session) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "unit": user.unit,
        "is_active": user.is_active,
        "roles": [{"code": r.code, "name": r.name} for r in (user.roles or [])],
        "permissions": user_permissions(user),
    }


@router.post("/login")
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username.strip()).first()
    if user is None or not verify_password(body.password, user.hashed_password):
        # ثبت تلاش ناموفق در ممیزی (بخش ۱۹)
        try:
            log_action(db, None, "login_failed", "user", None, body.username[:80],
                       {"ip": request.client.host if request.client else None}, request)
            db.commit()
        except Exception:
            db.rollback()
        raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور نادرست است")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="حساب کاربری غیرفعال است")

    user.last_login_at = datetime.now(timezone.utc)
    tokens = {
        "access_token": create_access_token(user.id, user.username),
        "refresh_token": create_refresh_token(user.id, user.username),
        "token_type": "bearer",
        "user": _user_payload(user, db),
    }
    log_action(db, user, "login", "user", user.id, user.username, None, request)
    db.commit()
    return tokens


@router.post("/refresh")
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="توکن تازه‌سازی نامعتبر است")
    user = db.get(User, payload.get("sub"))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="کاربر نامعتبر است")
    return {
        "access_token": create_access_token(user.id, user.username),
        "refresh_token": create_refresh_token(user.id, user.username),
        "token_type": "bearer",
    }


@router.post("/logout")
def logout(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    log_action(db, user, "logout", "user", user.id, user.username, None, request)
    db.commit()
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _user_payload(user, db)
