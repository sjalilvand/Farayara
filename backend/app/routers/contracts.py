"""مدیریت الگوهای قرارداد و تولید قرارداد (بخش ۱۲ سند)"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..deps import RequirePermission, get_current_user
from ..engines.contracts import find_variables, render_template, sanitize_html
from ..models import Contract, ContractRevision, ContractTemplate, ContractTemplateVersion, ContractVariable, User
from ..schemas import ContractCreate, PreviewIn, TemplateBodyIn, TemplateCreate, TemplatePublishIn, VariablesIn, paginate
from ..utils import flatten_dict, next_code, sha256_text

router = APIRouter(tags=["contracts"])


def _template_out(t: ContractTemplate, db: Session) -> dict:
    cur = db.get(ContractTemplateVersion, t.current_version_id) if t.current_version_id else None
    return {
        "id": t.id, "code": t.code, "title": t.title, "contract_type": t.contract_type,
        "description": t.description, "unit": t.unit, "status": t.status,
        "current_version_id": t.current_version_id,
        "current_version_number": cur.version_number if cur else None,
        "current_version_status": cur.status if cur else None,
        "created_at": t.created_at, "updated_at": t.updated_at,
    }


@router.get("/contract-templates")
def list_templates(query: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    templates = db.query(ContractTemplate).order_by(ContractTemplate.created_at.desc()).all()
    if query:
        ql = query.strip().lower()
        templates = [t for t in templates if ql in t.title.lower() or ql in (t.code or "").lower()]
    return paginate([_template_out(t, db) for t in templates], page, page_size)


@router.post("/contract-templates")
def create_template(body: TemplateCreate, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("contract.manage"))):
    t = ContractTemplate(code=next_code(db, "contract_template"), title=body.title.strip(),
                         contract_type=body.contract_type, description=body.description,
                         unit=body.unit, created_by=actor.id)
    db.add(t)
    db.flush()
    ver = ContractTemplateVersion(template_id=t.id, version_number=1, status="draft", created_by=actor.id)
    db.add(ver)
    db.flush()
    t.current_version_id = ver.id
    log_action(db, actor, "create", "contract_template", t.id, t.code)
    db.commit()
    return _template_out(t, db)


@router.get("/contract-templates/{template_id}")
def get_template(template_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = db.get(ContractTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="الگو یافت نشد")
    out = _template_out(t, db)
    versions = db.query(ContractTemplateVersion).filter(ContractTemplateVersion.template_id == t.id).order_by(
        ContractTemplateVersion.version_number).all()
    out["versions"] = [{"id": v.id, "version_number": v.version_number, "status": v.status,
                        "published_at": v.published_at, "legal_approver": v.legal_approver} for v in versions]
    variables = db.query(ContractVariable).filter(ContractVariable.template_id == t.id).order_by(ContractVariable.key).all()
    out["variables"] = [{"id": v.id, "key": v.key, "label": v.label, "data_type": v.data_type,
                         "required": v.required, "default_value": v.default_value} for v in variables]
    return out


@router.post("/contract-templates/{template_id}/versions")
def new_template_version(template_id: str, body: dict | None = None, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("contract.manage"))):
    """ویرایش الگو منتشرشده → نسخه پیش‌نویس جدید"""
    t = db.get(ContractTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="الگو یافت نشد")
    latest = db.query(ContractTemplateVersion).filter(ContractTemplateVersion.template_id == t.id).order_by(
        ContractTemplateVersion.version_number.desc()).first()
    ver = ContractTemplateVersion(
        template_id=t.id, version_number=(latest.version_number + 1) if latest else 1, status="draft",
        body_html=latest.body_html if latest else None,
        header_html=latest.header_html if latest else None,
        footer_html=latest.footer_html if latest else None,
        change_note=(body or {}).get("change_note") if body else None,
        created_by=actor.id,
    )
    db.add(ver)
    db.flush()
    t.current_version_id = ver.id
    log_action(db, actor, "create_version", "contract_template", t.id, t.code, {"version": ver.version_number})
    db.commit()
    return {"id": ver.id, "version_number": ver.version_number, "status": ver.status}


@router.get("/contract-template-versions/{version_id}")
def get_template_version(version_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ver = db.get(ContractTemplateVersion, version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="نسخه الگو یافت نشد")
    t = db.get(ContractTemplate, ver.template_id)
    variables = db.query(ContractVariable).filter(ContractVariable.template_id == ver.template_id).all()
    return {
        "id": ver.id, "template_id": ver.template_id, "template_title": t.title if t else None,
        "template_code": t.code if t else None,
        "version_number": ver.version_number, "status": ver.status,
        "body_html": ver.body_html, "header_html": ver.header_html, "footer_html": ver.footer_html,
        "legal_approver": ver.legal_approver, "valid_from": ver.valid_from,
        "published_at": ver.published_at,
        "variables": [{"key": v.key, "label": v.label, "data_type": v.data_type,
                       "required": v.required, "default_value": v.default_value} for v in variables],
        "detected_variables": find_variables(ver.body_html or ""),
    }


@router.put("/contract-template-versions/{version_id}/body")
def save_body(version_id: str, body: TemplateBodyIn, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("contract.manage"))):
    ver = db.get(ContractTemplateVersion, version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="نسخه الگو یافت نشد")
    if ver.status == "published":
        raise HTTPException(status_code=409, detail="نسخه منتشرشده تغییرناپذیر است")
    # پاکسازی HTML الگو (بخش ۱۹)
    ver.body_html = sanitize_html(body.body_html)
    ver.header_html = sanitize_html(body.header_html) if body.header_html else None
    ver.footer_html = sanitize_html(body.footer_html) if body.footer_html else None
    ver.change_note = body.change_note or ver.change_note
    log_action(db, actor, "update_body", "contract_template_version", ver.id)
    db.commit()
    return {"ok": True, "detected_variables": find_variables(ver.body_html or "")}


@router.put("/contract-template-versions/{version_id}/variables")
def save_variables(version_id: str, body: VariablesIn, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("contract.manage"))):
    ver = db.get(ContractTemplateVersion, version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="نسخه الگو یافت نشد")
    if ver.status == "published":
        raise HTTPException(status_code=409, detail="نسخه منتشرشده تغییرناپذیر است")
    db.query(ContractVariable).filter(ContractVariable.template_id == ver.template_id).delete()
    keys = set()
    for v in body.variables:
        key = (v.get("key") or "").strip()
        if not key or key in keys:
            continue
        keys.add(key)
        db.add(ContractVariable(
            template_id=ver.template_id, key=key, label=v.get("label") or key,
            data_type=v.get("data_type", "text"), required=bool(v.get("required")),
            default_value=v.get("default_value"),
        ))
    log_action(db, actor, "update_variables", "contract_template_version", ver.id, None, {"count": len(keys)})
    db.commit()
    return {"ok": True}


@router.post("/contract-template-versions/{version_id}/publish")
def publish_template(version_id: str, body: TemplatePublishIn, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("contract.approve"))):
    ver = db.get(ContractTemplateVersion, version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="نسخه الگو یافت نشد")
    if ver.status == "published":
        raise HTTPException(status_code=409, detail="این نسخه قبلاً منتشر شده است")
    if not (ver.body_html or "").strip():
        raise HTTPException(status_code=422, detail="بدنه الگو خالی است")
    ver.status = "published"
    ver.published_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    ver.legal_approver = body.legal_approver
    ver.valid_from = body.valid_from
    t = db.get(ContractTemplate, ver.template_id)
    t.current_version_id = ver.id
    log_action(db, actor, "publish", "contract_template_version", ver.id, t.code)
    db.commit()
    return {"ok": True, "version_number": ver.version_number}


@router.post("/contract-template-versions/{version_id}/preview")
def preview_template(version_id: str, body: PreviewIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ver = db.get(ContractTemplateVersion, version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="نسخه الگو یافت نشد")
    variables = db.query(ContractVariable).filter(ContractVariable.template_id == ver.template_id).all()
    data = {}
    for v in variables:
        if v.default_value:
            data[v.key] = v.default_value
    data.update(flatten_dict(body.data))
    rendered, missing = render_template(ver.body_html or "", data)
    required_missing = [v.key for v in variables if v.required and v.key in missing]
    return {"html": rendered, "missing": missing, "required_missing": required_missing}


@router.post("/contracts")
def generate_contract(body: ContractCreate, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("contract.generate"))):
    """تولید قرارداد — متغیر الزامی خالی مانع تولید نهایی است (AC-14) و متن منجمد می‌شود (AC-15)"""
    ver = db.get(ContractTemplateVersion, body.template_version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="نسخه الگو یافت نشد")
    if ver.status != "published":
        raise HTTPException(status_code=422, detail="تولید قرارداد فقط از نسخه منتشرشده الگو مجاز است")
    variables = db.query(ContractVariable).filter(ContractVariable.template_id == ver.template_id).all()
    data = {}
    for v in variables:
        val = body.data.get(v.key)
        if val is None and v.default_value:
            val = v.default_value
        data[v.key] = val
    # کنترل متغیرهای الزامی
    missing_required = [v.key for v in variables if v.required and (data.get(v.key) is None or str(data.get(v.key)).strip() == "")]
    if missing_required:
        raise HTTPException(status_code=422, detail={
            "message": "متغیرهای الزامی خالی هستند",
            "missing": missing_required,
        })
    rendered, missing = render_template(ver.body_html or "", data)
    final_html = sanitize_html(rendered)
    t = db.get(ContractTemplate, ver.template_id)
    contract = Contract(
        code=next_code(db, "contract"),
        template_version_id=ver.id,
        title=body.title or f"{t.title} — {data.get('party_b.full_name') or ''}".strip(),
        status="active",
        data=data,
        body_html=final_html,
        file_hash=sha256_text(final_html),
        party_a_name=str(data.get("party_a.full_name") or "") or None,
        party_b_name=str(data.get("party_b.full_name") or "") or None,
        amount=float(data.get("contract.amount")) if str(data.get("contract.amount") or "").replace(".", "", 1).isdigit() else None,
        contract_date=str(data.get("contract.date") or "") or None,
        duration=str(data.get("contract.duration") or "") or None,
        generated_by=actor.id,
    )
    db.add(contract)
    db.flush()
    db.add(ContractRevision(contract_id=contract.id, revision_number=1, body_html=final_html,
                            data=data, created_by=actor.id))
    log_action(db, actor, "generate_contract", "contract", contract.id, contract.code,
               {"template_version": ver.id, "hash": contract.file_hash[:16]})
    db.commit()
    return {"id": contract.id, "code": contract.code, "file_hash": contract.file_hash}


@router.get("/contracts")
def list_contracts(query: str | None = None, status: str | None = None,
                   page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    contracts = db.query(Contract).order_by(Contract.generated_at.desc()).all()
    if query:
        ql = query.strip().lower()
        contracts = [c for c in contracts if ql in (c.title or "").lower() or ql in (c.code or "").lower()
                     or ql in (c.party_b_name or "").lower()]
    if status:
        contracts = [c for c in contracts if c.status == status]
    out = [{
        "id": c.id, "code": c.code, "title": c.title, "status": c.status,
        "party_a_name": c.party_a_name, "party_b_name": c.party_b_name,
        "amount": c.amount, "contract_date": c.contract_date, "duration": c.duration,
        "file_hash": c.file_hash, "generated_at": c.generated_at,
    } for c in contracts]
    return paginate(out, page, page_size)


@router.get("/contracts/{contract_id}")
def get_contract(contract_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.get(Contract, contract_id)
    if not c:
        raise HTTPException(status_code=404, detail="قرارداد یافت نشد")
    ver = db.get(ContractTemplateVersion, c.template_version_id)
    t = db.get(ContractTemplate, ver.template_id) if ver else None
    revisions = db.query(ContractRevision).filter(ContractRevision.contract_id == c.id).order_by(
        ContractRevision.revision_number).all()
    return {
        "id": c.id, "code": c.code, "title": c.title, "status": c.status,
        "data": c.data, "body_html": c.body_html, "file_hash": c.file_hash,
        "party_a_name": c.party_a_name, "party_b_name": c.party_b_name,
        "amount": c.amount, "contract_date": c.contract_date, "duration": c.duration,
        "generated_at": c.generated_at,
        "template": {"code": t.code if t else None, "title": t.title if t else None,
                     "version_number": ver.version_number if ver else None},
        "revisions": [{"revision_number": r.revision_number, "created_at": r.created_at,
                       "change_note": r.change_note} for r in revisions],
    }


@router.get("/contracts/{contract_id}/download")
def download_contract(contract_id: str, db: Session = Depends(get_db), user: User = Depends(RequirePermission("file.download"))):
    """دریافت سند قرارداد — ثبت در ممیزی (بخش ۱۹)"""
    c = db.get(Contract, contract_id)
    if not c:
        raise HTTPException(status_code=404, detail="قرارداد یافت نشد")
    ver = db.get(ContractTemplateVersion, c.template_version_id)
    header = (ver.header_html or "") if ver else ""
    footer = (ver.footer_html or "") if ver else ""
    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8">
<title>{c.code}</title>
<style>
body {{ font-family: Vazirmatn, Tahoma, sans-serif; direction: rtl; max-width: 800px; margin: 0 auto; padding: 24px; color: #1e293b; line-height: 2; }}
h1,h2,h3 {{ color: #0f172a; }}
table {{ width: 100%; border-collapse: collapse; }} td,th {{ border: 1px solid #cbd5e1; padding: 8px; }}
.meta {{ background:#f1f5f9; border:1px solid #e2e8f0; border-radius:8px; padding:10px 16px; margin-bottom:16px; font-size:12px; color:#475569; }}
@page {{ margin: 2cm; }}
</style></head><body>
<div class="meta">کد قرارداد: {c.code} | تاریخ تولید: {str(c.generated_at)[:19]} | هش سند: {c.file_hash}</div>
{header}
{c.body_html}
{footer}
</body></html>"""
    log_action(db, user, "download_contract", "contract", c.id, c.code)
    db.commit()
    return Response(content=html, media_type="text/html; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename={c.code}.html"})
