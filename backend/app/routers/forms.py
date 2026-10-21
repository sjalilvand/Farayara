"""مدیریت فرم‌ها، نسخه‌ها، پاسخ‌ها و خروجی‌ها (بخش ۶ و ۸ سند)"""
import csv
import io
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..deps import RequirePermission, get_current_user
from ..models import (
    FieldDefinition, Form, FormFieldUsage, FormSubmission, FormVersion,
    SubmissionFieldValue, SubmissionRevision, User,
)
from ..schemas import FormCreate, SchemaIn, SubmissionIn, paginate
from ..utils import new_trace_code, next_code

router = APIRouter(tags=["forms"])


def _usage_sync(db: Session, form_version: FormVersion, schema: dict):
    """همگام‌سازی FormFieldUsage از روی schema فرم — ارتباط فیلدهای کاتالوگ"""
    db.query(FormFieldUsage).filter(FormFieldUsage.form_version_id == form_version.id).delete()
    fields = (schema or {}).get("fields") or []
    for idx, f in enumerate(fields):
        db.add(FormFieldUsage(
            form_version_id=form_version.id,
            field_id=f.get("field_id"),
            field_key=f.get("key") or "",
            label_override=f.get("label"),
            required=bool(f.get("required", False)),
            position=idx,
            config=f,
        ))


def _form_out(form: Form, db: Session) -> dict:
    cur = db.get(FormVersion, form.current_version_id) if form.current_version_id else None
    return {
        "id": form.id, "code": form.code, "title": form.title, "description": form.description,
        "purpose": form.purpose, "category": form.category, "tags": form.tags or [],
        "confidentiality": form.confidentiality, "audience": form.audience,
        "retention_policy": form.retention_policy, "status": form.status,
        "current_version_id": form.current_version_id,
        "current_version_number": cur.version_number if cur else None,
        "current_version_status": cur.status if cur else None,
        "created_at": form.created_at, "updated_at": form.updated_at,
    }


@router.get("/forms")
def list_forms(
    query: str | None = None, status: str | None = None, category: str | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    forms = db.query(Form).order_by(Form.created_at.desc()).all()
    if query:
        ql = query.strip().lower()
        forms = [f for f in forms if ql in f.title.lower() or ql in (f.code or "").lower()]
    if status:
        forms = [f for f in forms if f.current_version_id and db.get(FormVersion, f.current_version_id).status == status]
    if category:
        forms = [f for f in forms if f.category == category]
    out = [_form_out(f, db) for f in forms]
    return paginate(out, page, page_size)


@router.post("/forms")
def create_form(body: FormCreate, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("form.create"))):
    form = Form(code=next_code(db, "form"), title=body.title.strip(), description=body.description,
                purpose=body.purpose, category=body.category, tags=body.tags or [],
                confidentiality=body.confidentiality, audience=body.audience,
                retention_policy=body.retention_policy, created_by=actor.id)
    db.add(form)
    db.flush()
    ver = FormVersion(form_id=form.id, version_number=1, status="draft",
                      schema_json={"fields": []}, ui_schema_json={}, rules_json={}, created_by=actor.id)
    db.add(ver)
    db.flush()
    form.current_version_id = ver.id
    log_action(db, actor, "create", "form", form.id, form.code)
    db.commit()
    return _form_out(form, db)


@router.get("/forms/{form_id}")
def get_form(form_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    form = db.get(Form, form_id)
    if not form:
        raise HTTPException(status_code=404, detail="فرم یافت نشد")
    out = _form_out(form, db)
    versions = db.query(FormVersion).filter(FormVersion.form_id == form.id).order_by(FormVersion.version_number).all()
    out["versions"] = [
        {"id": v.id, "version_number": v.version_number, "status": v.status, "created_at": v.created_at,
         "published_at": v.published_at, "change_note": v.change_note}
        for v in versions
    ]
    return out


@router.post("/forms/{form_id}/versions")
def new_form_version(form_id: str, body: dict | None = None, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("form.create"))):
    """ویرایش فرم منتشرشده باعث ایجاد نسخه پیش‌نویس جدید می‌شود (بخش ۶.۵ / AC-06)"""
    form = db.get(Form, form_id)
    if not form:
        raise HTTPException(status_code=404, detail="فرم یافت نشد")
    latest = db.query(FormVersion).filter(FormVersion.form_id == form.id).order_by(
        FormVersion.version_number.desc()).first()
    ver = FormVersion(
        form_id=form.id, version_number=(latest.version_number + 1) if latest else 1,
        status="draft",
        schema_json=(latest.schema_json if latest else {"fields": []}) or {"fields": []},
        ui_schema_json=(latest.ui_schema_json if latest else {}) or {},
        rules_json=(latest.rules_json if latest else {}) or {},
        change_note=(body or {}).get("change_note") if body else None,
        created_by=actor.id,
    )
    db.add(ver)
    db.flush()
    form.current_version_id = ver.id
    log_action(db, actor, "create_version", "form", form.id, form.code, {"version": ver.version_number})
    db.commit()
    return {"id": ver.id, "version_number": ver.version_number, "status": ver.status}


@router.get("/form-versions/{version_id}")
def get_form_version(version_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ver = db.get(FormVersion, version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="نسخه فرم یافت نشد")
    form = db.get(Form, ver.form_id)
    usages = db.query(FormFieldUsage).filter(FormFieldUsage.form_version_id == ver.id).all()
    return {
        "id": ver.id, "form_id": ver.form_id, "form_code": form.code if form else None,
        "form_title": form.title if form else None,
        "version_number": ver.version_number, "status": ver.status,
        "schema_json": ver.schema_json, "ui_schema_json": ver.ui_schema_json, "rules_json": ver.rules_json,
        "published_at": ver.published_at, "change_note": ver.change_note,
        "usages": [{"field_id": u.field_id, "field_key": u.field_key} for u in usages],
    }


@router.put("/form-versions/{version_id}/schema")
def save_schema(version_id: str, body: SchemaIn, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("form.create"))):
    ver = db.get(FormVersion, version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="نسخه فرم یافت نشد")
    if ver.status == "published":
        raise HTTPException(status_code=409, detail="نسخه منتشرشده تغییرناپذیر است؛ نسخه جدید بسازید")
    # کنترل یکتایی کلید فیلدها
    keys = [f.get("key") for f in (body.schema_json or {}).get("fields", []) if f.get("key")]
    if len(keys) != len(set(keys)):
        raise HTTPException(status_code=422, detail="کلید فیلدها باید یکتا باشد")
    ver.schema_json = body.schema_json
    if body.rules_json is not None:
        ver.rules_json = body.rules_json
    ver.change_note = body.change_note or ver.change_note
    _usage_sync(db, ver, body.schema_json)
    log_action(db, actor, "update_schema", "form_version", ver.id, None, {"form": ver.form_id})
    db.commit()
    return {"ok": True, "fields_count": len((body.schema_json or {}).get("fields", []))}


@router.post("/form-versions/{version_id}/publish")
def publish_form_version(version_id: str, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("form.publish"))):
    from datetime import datetime, timezone
    ver = db.get(FormVersion, version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="نسخه فرم یافت نشد")
    if ver.status == "published":
        raise HTTPException(status_code=409, detail="این نسخه قبلاً منتشر شده است")
    fields = ((ver.schema_json or {}).get("fields") or [])
    if not fields:
        raise HTTPException(status_code=422, detail="فرم بدون فیلد قابل انتشار نیست")
    # فرم باید حداقل یک فیلد الزامی مرتبط با کاتالوگ یا فیلد ساده داشته باشد
    ver.status = "published"
    ver.published_at = datetime.now(timezone.utc)
    ver.published_by = actor.id
    form = db.get(Form, ver.form_id)
    form.current_version_id = ver.id
    log_action(db, actor, "publish", "form_version", ver.id, form.code if form else None,
               {"version": ver.version_number, "fields": len(fields)})
    db.commit()
    return {"ok": True, "version_number": ver.version_number}


@router.post("/forms/{form_id}/export")
def export_form_definition(form_id: str, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("form.create"))):
    """خروجی تعریف فرم — JSON قابل ورود مجدد (بخش ۶.۵)"""
    form = db.get(Form, form_id)
    if not form:
        raise HTTPException(status_code=404, detail="فرم یافت نشد")
    ver = db.get(FormVersion, form.current_version_id) if form.current_version_id else None
    payload = {
        "farayara_export": "form_definition", "version": 1,
        "form": {"code": form.code, "title": form.title, "description": form.description,
                 "purpose": form.purpose, "category": form.category},
        "form_version": {"version_number": ver.version_number if ver else 1,
                         "schema_json": ver.schema_json if ver else {}, "rules_json": ver.rules_json if ver else {}},
    }
    log_action(db, actor, "export", "form", form.id, form.code)
    db.commit()
    return payload


@router.post("/form-versions/{version_id}/submissions")
def create_submission(version_id: str, body: SubmissionIn, db: Session = Depends(get_db),
                      actor: User = Depends(RequirePermission("form.submit"))):
    """ثبت پاسخ — تصویر JSON و مقادیر گزارش‌پذیر در یک تراکنش (بخش ۸)"""
    from datetime import datetime, timezone
    ver = db.get(FormVersion, version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="نسخه فرم یافت نشد")
    if ver.status != "published":
        raise HTTPException(status_code=409, detail="پاسخ‌گیری فقط روی نسخه منتشرشده مجاز است")

    schema_fields = ((ver.schema_json or {}).get("fields") or [])
    # اعتبارسنجی الزامی‌ها
    errors = []
    for f in schema_fields:
        key = f.get("key")
        val = body.data.get(key)
        if f.get("required") and (val is None or val == "" or (isinstance(val, list) and not val)):
            errors.append(f"فیلد «{f.get('label') or key}» الزامی است")
    if errors:
        raise HTTPException(status_code=422, detail=errors)

    sub = FormSubmission(
        trace_code=new_trace_code(db, "TRK"),
        form_version_id=ver.id,
        submitted_by=actor.id,
        respondent_name=body.respondent_name,
        status=body.status if body.status in ("draft", "final") else "final",
        data=body.data,
        rules_version=f"{ver.form_id}:{ver.version_number}",
        started_at=datetime.now(timezone.utc),
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(sub)
    db.flush()
    # مقادیر گزارش‌پذیر
    for f in schema_fields:
        key = f.get("key")
        val = body.data.get(key)
        is_empty = val is None or val == "" or (isinstance(val, (list, dict)) and not val)
        num = None
        try:
            num = float(val) if not is_empty and isinstance(val, (int, float, str)) and str(val).replace(".", "", 1).replace("-", "", 1).isdigit() else None
        except (ValueError, TypeError):
            num = None
        db.add(SubmissionFieldValue(
            submission_id=sub.id, field_id=f.get("field_id"), field_key=key,
            value_text=None if isinstance(val, (list, dict)) else ("" if is_empty else str(val)),
            value_number=num, value_bool=val if isinstance(val, bool) else None,
            is_empty=is_empty,
        ))
    log_action(db, actor, "submit", "form_submission", sub.id, sub.trace_code, {"form": ver.form_id})
    db.commit()
    return {"id": sub.id, "trace_code": sub.trace_code, "status": sub.status}


@router.get("/forms/{form_id}/submissions")
def list_submissions(form_id: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                     db: Session = Depends(get_db), user: User = Depends(RequirePermission("form.submissions.view"))):
    versions = db.query(FormVersion).filter(FormVersion.form_id == form_id).all()
    version_ids = [v.id for v in versions]
    if not version_ids:
        return {"items": [], "total": 0, "page": page, "page_size": page_size}
    q = db.query(FormSubmission).filter(FormSubmission.form_version_id.in_(version_ids)).order_by(
        FormSubmission.submitted_at.desc())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    ver_map = {v.id: v.version_number for v in versions}
    return {
        "items": [
            {"id": s.id, "trace_code": s.trace_code, "status": s.status,
             "version_number": ver_map.get(s.form_version_id),
             "submitted_by": s.submitted_by, "respondent_name": s.respondent_name,
             "submitted_at": s.submitted_at, "data": s.data}
            for s in rows
        ],
        "total": total, "page": page, "page_size": page_size,
    }


@router.get("/submissions/{submission_id}")
def get_submission(submission_id: str, db: Session = Depends(get_db), user: User = Depends(RequirePermission("form.submissions.view"))):
    s = db.get(FormSubmission, submission_id)
    if not s:
        raise HTTPException(status_code=404, detail="پاسخ یافت نشد")
    ver = db.get(FormVersion, s.form_version_id)
    form = db.get(Form, ver.form_id) if ver else None
    revisions = db.query(SubmissionRevision).filter(SubmissionRevision.submission_id == s.id).all()
    return {
        "id": s.id, "trace_code": s.trace_code, "status": s.status,
        "form_id": form.id if form else None, "form_title": form.title if form else None,
        "version_number": ver.version_number if ver else None,
        "data": s.data, "submitted_at": s.submitted_at, "respondent_name": s.respondent_name,
        "revisions": [{"reason": r.reason, "created_at": r.created_at} for r in revisions],
    }


@router.get("/forms/{form_id}/submissions/export")
def export_submissions(form_id: str, format: str = "csv", db: Session = Depends(get_db),
                       user: User = Depends(RequirePermission("export.data"))):
    """خروجی پاسخ‌ها — CSV/Excel/JSON با محافظت فرمول‌تزریقی (بخش ۱۹)"""
    from ..models import FormVersion
    versions = db.query(FormVersion).filter(FormVersion.form_id == form_id).order_by(FormVersion.version_number).all()
    if not versions:
        raise HTTPException(status_code=404, detail="فرم یافت نشد")
    form = db.get(Form, form_id)
    subs = (db.query(FormSubmission)
            .filter(FormSubmission.form_version_id.in_([v.id for v in versions]),
                    FormSubmission.status == "final")
            .order_by(FormSubmission.submitted_at.desc()).all())
    latest_ver = {s.form_version_id for s in subs}
    ver = next((v for v in versions if v.id in latest_ver), versions[-1])
    fields = ((ver.schema_json or {}).get("fields") or [])

    def safe_cell(v):
        """محافظت در برابر فرمول‌تزریقی CSV/Excel"""
        s = "" if v is None else str(v)
        if s.startswith(("=", "+", "-", "@")):
            s = "'" + s
        return s

    if format == "json":
        payload = {
            "form": {"code": form.code, "title": form.title},
            "version": ver.version_number,
            "count": len(subs),
            "submissions": [{"trace_code": s.trace_code, "submitted_at": str(s.submitted_at), "data": s.data} for s in subs],
        }
        log_action(db, user, "export", "form", form_id, form.code, {"format": "json"})
        db.commit()
        return payload

    headers = ["کد رهگیری", "تاریخ ثبت", "نسخه"] + [f.get("label") or f.get("key") for f in fields]
    if format == "xlsx":
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "پاسخ‌ها"
        ws.append(headers)
        for s in subs:
            row = [s.trace_code, str(s.submitted_at)[:19], f"v{ver.version_number}"]
            for f in fields:
                row.append(safe_cell((s.data or {}).get(f.get("key"))))
            ws.append(row)
        bio = io.BytesIO()
        wb.save(bio)
        log_action(db, user, "export", "form", form_id, form.code, {"format": "xlsx", "rows": len(subs)})
        db.commit()
        return Response(
            content=bio.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={form.code}_submissions.xlsx"},
        )

    # CSV با BOM برای نمایش صحیح فارسی در Excel
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for s in subs:
        row = [s.trace_code, str(s.submitted_at)[:19], f"v{ver.version_number}"]
        for f in fields:
            row.append(safe_cell((s.data or {}).get(f.get("key"))))
        writer.writerow(row)
    log_action(db, user, "export", "form", form_id, form.code, {"format": "csv", "rows": len(subs)})
    db.commit()
    return Response(content="\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename={form.code}_submissions.csv"})


@router.post("/submissions/{submission_id}/revise")
def revise_submission(submission_id: str, body: dict, db: Session = Depends(get_db),
                      user: User = Depends(RequirePermission("form.submissions.revise"))):
    """اصلاح پاسخ نهایی — به‌صورت نسخه اصلاحی با ثبت سابقه (بخش ۸)"""
    s = db.get(FormSubmission, submission_id)
    if not s:
        raise HTTPException(status_code=404, detail="پاسخ یافت نشد")
    if s.status != "final":
        raise HTTPException(status_code=409, detail="فقط پاسخ نهایی اصلاح می‌شود")
    old = dict(s.data or {})
    new = dict(body.get("data") or {})
    db.add(SubmissionRevision(
        submission_id=s.id, revised_by=user.id, reason=body.get("reason"),
        old_data=old, new_data=new,
    ))
    s.data = new
    # به‌روزرسانی مقادیر گزارش‌پذیر
    db.query(SubmissionFieldValue).filter(SubmissionFieldValue.submission_id == s.id).delete()
    ver = db.get(FormVersion, s.form_version_id)
    for f in ((ver.schema_json or {}).get("fields") or []):
        key = f.get("key")
        val = new.get(key)
        is_empty = val is None or val == "" or (isinstance(val, (list, dict)) and not val)
        db.add(SubmissionFieldValue(
            submission_id=s.id, field_id=f.get("field_id"), field_key=key,
            value_text="" if is_empty else str(val), is_empty=is_empty,
        ))
    log_action(db, user, "revise", "form_submission", s.id, s.trace_code, {"reason": body.get("reason")})
    db.commit()
    return {"ok": True}
