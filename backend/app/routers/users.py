"""مدیریت کاربران، نقش‌ها و مجوزها (بخش ۳ سند)"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..deps import RequirePermission, get_current_user
from ..models import Permission, Role, User, UserRole, RolePermission
from ..schemas import RoleIn, UserCreate, UserUpdate, paginate
from ..security import hash_password
from ..utils import normalize_fa

router = APIRouter(tags=["users"])


def _user_out(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "unit": user.unit,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
        "roles": [{"code": r.code, "name": r.name} for r in (user.roles or [])],
    }


@router.get("/users/me")
def me(user: User = Depends(get_current_user)):
    return _user_out(user)


@router.get("/users")
def list_users(
    query: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(RequirePermission("user.manage")),
):
    q = db.query(User)
    if query:
        nq = normalize_fa(query)
        users = [u for u in q.all() if nq in normalize_fa(u.username) or nq in normalize_fa(u.full_name)]
    else:
        users = q.order_by(User.created_at).all()
    return paginate([_user_out(u) for u in users], page, page_size)


@router.post("/users")
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(RequirePermission("user.manage")),
):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=409, detail="نام کاربری تکراری است")
    user = User(
        username=body.username.strip(),
        full_name=body.full_name.strip(),
        email=body.email,
        unit=body.unit,
        hashed_password=hash_password(body.password),
        is_active=True,
    )
    db.add(user)
    db.flush()
    _assign_roles(db, user, body.role_codes)
    log_action(db, actor, "create", "user", user.id, user.username, {"roles": body.role_codes})
    db.commit()
    return _user_out(user)


@router.put("/users/{user_id}")
def update_user(
    user_id: str,
    body: UserUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(RequirePermission("user.manage")),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.email is not None:
        user.email = body.email
    if body.unit is not None:
        user.unit = body.unit
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password:
        user.hashed_password = hash_password(body.password)
    if body.role_codes is not None:
        _assign_roles(db, user, body.role_codes)
    log_action(db, actor, "update", "user", user.id, user.username, {"roles": body.role_codes})
    db.commit()
    return _user_out(user)


def _assign_roles(db: Session, user: User, role_codes: list[str]):
    db.query(UserRole).filter(UserRole.user_id == user.id).delete()
    for code in role_codes or []:
        role = db.query(Role).filter(Role.code == code).first()
        if role:
            db.add(UserRole(user_id=user.id, role_id=role.id))


@router.get("/roles")
def list_roles(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    roles = db.query(Role).order_by(Role.code).all()
    return [
        {
            "id": r.id, "code": r.code, "name": r.name, "description": r.description,
            "is_system": r.is_system,
            "permissions": [p.code for p in (r.permissions or [])],
        }
        for r in roles
    ]


@router.post("/roles")
def create_role(body: RoleIn, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("role.manage"))):
    if db.query(Role).filter(Role.code == body.code).first():
        raise HTTPException(status_code=409, detail="کد نقش تکراری است")
    role = Role(code=body.code, name=body.name, description=body.description)
    db.add(role)
    db.flush()
    for code in body.permission_codes:
        perm = db.query(Permission).filter(Permission.code == code).first()
        if perm:
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    log_action(db, actor, "create", "role", role.id, role.code)
    db.commit()
    return {"ok": True}


@router.put("/roles/{role_id}")
def update_role(role_id: str, body: RoleIn, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("role.manage"))):
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="نقش یافت نشد")
    role.name = body.name
    role.description = body.description
    db.query(RolePermission).filter(RolePermission.role_id == role.id).delete()
    for code in body.permission_codes:
        perm = db.query(Permission).filter(Permission.code == code).first()
        if perm:
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    log_action(db, actor, "update", "role", role.id, role.code)
    db.commit()
    return {"ok": True}


@router.get("/permissions")
def list_permissions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    perms = db.query(Permission).order_by(Permission.group, Permission.code).all()
    return [{"code": p.code, "title": p.title, "group": p.group} for p in perms]
