"""وابستگی‌های FastAPI: احراز هویت و کنترل دسترسی در سطح بک‌اند (بخش ۳.۲ سند)

دسترسی فقط با مجوز بک‌اند کنترل می‌شود؛ مخفی کردن دکمه در فرانت‌اند کافی نیست.
"""
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="احراز هویت لازم است")
    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="توکن نامعتبر یا منقضی است")
    user = db.get(User, payload.get("sub"))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="کاربر یافت نشد یا غیرفعال است")
    request.state.user = user
    return user


class RequirePermission:
    """سازنده وابستگی مجوز — نمونه: Depends(RequirePermission("form.publish"))"""

    def __init__(self, permission: str):
        self.permission = permission

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        codes = {p.code for role in (user.roles or []) for p in (role.permissions or [])}
        if "system.admin" not in codes and self.permission not in codes:
            raise HTTPException(
                status_code=403,
                detail=f"دسترسی مجاز نیست؛ مجوز لازم: {self.permission}",
            )
        return user


def user_permissions(user: User) -> list[str]:
    if not user:
        return []
    codes = set()
    for role in user.roles or []:
        for p in role.permissions or []:
            codes.add(p.code)
    return sorted(codes)
