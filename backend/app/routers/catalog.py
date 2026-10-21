"""کاتالوگ مرکزی داده و فیلدها (بخش ۷ سند)

- دو موجودیت جدا: تعریف فیلد مرجع و نمونه استفاده در نسخه فرم
- فراوانی چندشاخصی: فرم‌های استفاده‌کننده، نسخه‌ها، جایگاه‌ها، پاسخ‌ها، نرخ تکمیل
- پیشنهاد فیلدهای مشابه بدون ادغام خودکار (بخش ۷.۳)
"""
import difflib

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..deps import RequirePermission, get_current_user
from ..models import (
    FieldDefinition, FieldDefinitionVersion, FieldAlias, FormFieldUsage, FormSubmission,
    SubmissionFieldValue, User,
)
from ..schemas import FieldCreate, FieldUpdate, paginate
from ..utils import next_code, normalize_fa

router = APIRouter(prefix="/catalog", tags=["catalog"])


def _field_out(f: FieldDefinition, db: Session) -> dict:
    ver = db.get(FieldDefinitionVersion, f.current_version_id) if f.current_version_id else None
    return {
        "id": f.id, "code": f.code, "tech_name": f.tech_name, "title_fa": f.title_fa,
        "description": f.description, "data_type": ver.data_type if ver else None,
        "version": ver.version_number if ver else None,
        "validation_rules": ver.validation_rules if ver else {},
        "allowed_values": ver.allowed_values if ver else [],
        "unit": f.unit, "category": f.category, "aliases": f.aliases or [],
        "sensitivity": f.sensitivity, "is_identity": f.is_identity, "is_health": f.is_health,
        "retention_policy": f.retention_policy, "status": f.status,
        "created_at": f.created_at, "updated_at": f.updated_at,
    }


@router.get("/fields")
def list_fields(
    query: str | None = None,
    category: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(FieldDefinition)
    fields = q.order_by(FieldDefinition.title_fa).all()
    if query:
        nq = normalize_fa(query)
        fields = [f for f in fields if nq in normalize_fa(f.title_fa) or nq in f.tech_name
                  or any(nq in normalize_fa(a) for a in (f.aliases or []))]
    if category:
        fields = [f for f in fields if f.category == category]
    if status:
        fields = [f for f in fields if f.status == status]
    out = [_field_out(f, db) for f in fields]
    # شمارش تعداد فرم‌های استفاده‌کننده برای نمایش فهرست
    usage_counts = dict(
        db.query(FormFieldUsage.field_id, func.count(func.distinct(FormFieldUsage.form_version_id)))
        .filter(FormFieldUsage.field_id.isnot(None))
        .group_by(FormFieldUsage.field_id).all()
    )
    for item in out:
        item["forms_count"] = usage_counts.get(item["id"], 0)
    return paginate(out, page, page_size)


@router.post("/fields")
def create_field(body: FieldCreate, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("catalog.manage"))):
    if db.query(FieldDefinition).filter(FieldDefinition.tech_name == body.tech_name).first():
        raise HTTPException(status_code=409, detail="نام فنی فیلد تکراری است؛ فیلد مشابه موجود را استفاده کنید")
    field = FieldDefinition(
        code=next_code(db, "field"),
        tech_name=body.tech_name,
        title_fa=body.title_fa.strip(),
        description=body.description,
        unit=body.unit,
        category=body.category,
        aliases=body.aliases or [],
        sensitivity=body.sensitivity,
        is_identity=body.is_identity,
        is_health=body.is_health,
        retention_policy=body.retention_policy,
        status="active",
        created_by=actor.id,
    )
    db.add(field)
    db.flush()
    ver = FieldDefinitionVersion(
        field_id=field.id, version_number=1, data_type=body.data_type,
        validation_rules=body.validation_rules or {}, allowed_values=body.allowed_values or [],
        description=body.description, created_by=actor.id,
    )
    db.add(ver)
    db.flush()
    field.current_version_id = ver.id
    for alias in (body.aliases or []):
        db.add(FieldAlias(field_id=field.id, alias=alias))
    log_action(db, actor, "create", "field", field.id, field.code)
    db.commit()
    return _field_out(field, db)


@router.get("/fields/{field_id}")
def get_field(field_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    f = db.get(FieldDefinition, field_id)
    if not f:
        raise HTTPException(status_code=404, detail="فیلد یافت نشد")
    out = _field_out(f, db)
    versions = db.query(FieldDefinitionVersion).filter(FieldDefinitionVersion.field_id == f.id).order_by(
        FieldDefinitionVersion.version_number).all()
    out["versions"] = [{"id": v.id, "version_number": v.version_number, "data_type": v.data_type,
                        "validation_rules": v.validation_rules, "created_at": v.created_at} for v in versions]
    return out


@router.put("/fields/{field_id}")
def update_field(field_id: str, body: FieldUpdate, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("catalog.manage"))):
    f = db.get(FieldDefinition, field_id)
    if not f:
        raise HTTPException(status_code=404, detail="فیلد یافت نشد")
    changed_type = False
    if body.title_fa is not None:
        f.title_fa = body.title_fa  # تغییر عنوان نمایشی هویت فیلد مرجع را تغییر نمی‌دهد (بخش ۷.۳)
    if body.description is not None:
        f.description = body.description
    if body.category is not None:
        f.category = body.category
    if body.unit is not None:
        f.unit = body.unit
    if body.aliases is not None:
        f.aliases = body.aliases
        db.query(FieldAlias).filter(FieldAlias.field_id == f.id).delete()
        for a in body.aliases:
            db.add(FieldAlias(field_id=f.id, alias=a))
    if body.sensitivity is not None:
        f.sensitivity = body.sensitivity
    if body.is_identity is not None:
        f.is_identity = body.is_identity
    if body.is_health is not None:
        f.is_health = body.is_health
    if body.retention_policy is not None:
        f.retention_policy = body.retention_policy

    cur = db.get(FieldDefinitionVersion, f.current_version_id) if f.current_version_id else None
    needs_new_version = (
        (body.data_type is not None and cur and body.data_type != cur.data_type)
        or (body.validation_rules is not None)
        or (body.allowed_values is not None)
    )
    if needs_new_version and cur is not None:
        # تغییر نوع یا قواعد فیلد منتشرشده با نسخه‌بندی انجام می‌شود (بخش ۷.۳)
        ver = FieldDefinitionVersion(
            field_id=f.id, version_number=cur.version_number + 1,
            data_type=body.data_type or cur.data_type,
            validation_rules=body.validation_rules if body.validation_rules is not None else cur.validation_rules,
            allowed_values=body.allowed_values if body.allowed_values is not None else cur.allowed_values,
            description=body.description if body.description is not None else cur.description,
            created_by=actor.id,
        )
        db.add(ver)
        db.flush()
        f.current_version_id = ver.id
        changed_type = True
    log_action(db, actor, "update", "field", f.id, f.code, {"new_version": changed_type})
    db.commit()
    return _field_out(f, db)


@router.post("/fields/{field_id}/deactivate")
def deactivate_field(field_id: str, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("catalog.manage"))):
    """فیلد استفاده‌شده حذف فیزیکی نمی‌شود؛ فقط غیرفعال می‌گردد (بخش ۷.۳)"""
    f = db.get(FieldDefinition, field_id)
    if not f:
        raise HTTPException(status_code=404, detail="فیلد یافت نشد")
    f.status = "inactive"
    log_action(db, actor, "deactivate", "field", f.id, f.code)
    db.commit()
    return {"ok": True}


@router.post("/fields/{field_id}/activate")
def activate_field(field_id: str, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("catalog.manage"))):
    f = db.get(FieldDefinition, field_id)
    if not f:
        raise HTTPException(status_code=404, detail="فیلد یافت نشد")
    f.status = "active"
    log_action(db, actor, "activate", "field", f.id, f.code)
    db.commit()
    return {"ok": True}


@router.get("/fields/{field_id}/usage")
def field_usage(field_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """مسیر استفاده: فیلد ← نسخه فرم (و فرم) (بخش ۷.۵)"""
    from ..models import Form, FormVersion
    rows = (
        db.query(FormFieldUsage, FormVersion, Form)
        .join(FormVersion, FormVersion.id == FormFieldUsage.form_version_id)
        .join(Form, Form.id == FormVersion.form_id)
        .filter(FormFieldUsage.field_id == field_id)
        .order_by(FormVersion.created_at.desc())
        .all()
    )
    return [
        {
            "usage_id": u.id,
            "form_id": form.id, "form_code": form.code, "form_title": form.title,
            "form_version_id": fv.id, "form_version": fv.version_number, "form_version_status": fv.status,
            "field_key": u.field_key, "label_override": u.label_override, "required": u.required,
        }
        for u, fv, form in rows
    ]


@router.get("/fields/{field_id}/statistics")
def field_statistics(field_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """فراوانی چندشاخصی فیلد (بخش ۷.۴)"""
    f = db.get(FieldDefinition, field_id)
    if not f:
        raise HTTPException(status_code=404, detail="فیلد یافت نشد")

    usages = db.query(FormFieldUsage).filter(FormFieldUsage.field_id == field_id).all()
    versions_count = len({u.form_version_id for u in usages})
    forms_count = 0
    if versions_count:
        from ..models import Form, FormVersion
        forms_count = (
            db.query(func.count(func.distinct(FormVersion.form_id)))
            .join(FormFieldUsage, FormFieldUsage.form_version_id == FormVersion.id)
            .filter(FormFieldUsage.field_id == field_id)
            .scalar() or 0
        )
    places_count = len(usages)

    total_values = db.query(SubmissionFieldValue).filter(
        SubmissionFieldValue.field_id == field_id).count()
    filled = db.query(SubmissionFieldValue).filter(
        SubmissionFieldValue.field_id == field_id, SubmissionFieldValue.is_empty == False).count()
    fill_rate = round(filled / total_values, 4) if total_values else None

    # فراوانی مقادیر (توزیع) — برای فیلدهای گزینه‌ای
    distribution = dict(
        db.query(SubmissionFieldValue.value_text, func.count(SubmissionFieldValue.id))
        .filter(SubmissionFieldValue.field_id == field_id, SubmissionFieldValue.is_empty == False)
        .group_by(SubmissionFieldValue.value_text).limit(20).all()
    )

    return {
        "field_id": field_id, "code": f.code, "title_fa": f.title_fa,
        "forms_count": forms_count,          # تعداد فرم‌های استفاده‌کننده
        "versions_count": versions_count,    # تعداد نسخه‌های استفاده‌کننده
        "places_count": places_count,        # تعداد جایگاه‌ها در ساختار فرم‌ها
        "submissions_count": total_values,   # تعداد پاسخ ثبت‌شده
        "filled_count": filled,              # تعداد مقادیر غیرخالی
        "fill_rate": fill_rate,              # نرخ تکمیل
        "value_distribution": distribution,  # فراوانی مقادیر
    }


@router.get("/similar")
def similar_fields(name: str = Query(..., min_length=2), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """پیشنهاد فیلدهای مشابه — بدون ادغام خودکار (بخش ۷.۳)"""
    nq = normalize_fa(name)
    fields = db.query(FieldDefinition).filter(FieldDefinition.status == "active").all()
    scored = []
    for f in fields:
        candidates = [f.title_fa, f.tech_name] + (f.aliases or [])
        best = 0.0
        for c in candidates:
            ratio = difflib.SequenceMatcher(None, nq, normalize_fa(c)).ratio()
            if nq and (nq in normalize_fa(c) or normalize_fa(c) in nq):
                ratio = max(ratio, 0.85)
            best = max(best, ratio)
        if best > 0.5:
            scored.append({"id": f.id, "code": f.code, "title_fa": f.title_fa, "tech_name": f.tech_name, "score": round(best, 3)})
    scored.sort(key=lambda x: -x["score"])
    return scored[:8]


@router.get("/categories")
def categories(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(FieldDefinition.category).distinct().all()
    return sorted({r[0] for r in rows if r[0]})
