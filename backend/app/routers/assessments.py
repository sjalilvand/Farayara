"""بانک آزمون‌ها، جست‌وجوی اینترنتی، اجرای آزمون و نمره‌گذاری (بخش‌های ۹ تا ۱۱ سند)"""
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..deps import RequirePermission, get_current_user
from ..engines.scoring import compute_scores, run_validation_cases
from ..models import (
    Assessment, AssessmentAdministration, AssessmentItem, AssessmentResult,
    AssessmentScoreRun, AssessmentSource, AssessmentValidationCase, AssessmentVersion, User,
)
from ..schemas import (
    AdministrationIn, AnswersIn, AssessmentContentIn, AssessmentCreate, AssessmentUpdate,
    DiscoveryImportIn, DiscoverySearchIn, PublishIn, ValidationCaseIn, VersionMetaIn, paginate,
)
from ..utils import next_code

router = APIRouter(tags=["assessments"])


def _assessment_out(a: Assessment, db: Session) -> dict:
    cur = db.get(AssessmentVersion, a.current_version_id) if a.current_version_id else None
    return {
        "id": a.id, "code": a.code, "title_fa": a.title_fa, "title_original": a.title_original,
        "abbreviation": a.abbreviation, "domain": a.domain, "author": a.author, "publisher": a.publisher,
        "rights_holder": a.rights_holder, "language": a.language, "target_group": a.target_group,
        "item_count": a.item_count, "duration_minutes": a.duration_minutes, "answer_mode": a.answer_mode,
        "scoring_method": a.scoring_method, "scientific_references": a.scientific_references,
        "norms_notes": a.norms_notes, "limitations": a.limitations,
        "license_terms": a.license_terms, "license_status": a.license_status,
        "approved_scientific": a.approved_scientific, "approved_legal": a.approved_legal,
        "approved_scientific_by": a.approved_scientific_by, "approved_legal_by": a.approved_legal_by,
        "category": a.category, "tags": a.tags or [], "status": a.status,
        "current_version_id": a.current_version_id,
        "current_version_number": cur.version_number if cur else None,
        "current_version_status": cur.status if cur else None,
        "created_at": a.created_at,
    }


@router.get("/assessments")
def list_assessments(query: str | None = None, status: str | None = None,
                     page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                     db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.query(Assessment).order_by(Assessment.created_at.desc()).all()
    if query:
        ql = query.strip().lower()
        items = [a for a in items if ql in a.title_fa.lower() or ql in (a.title_original or "").lower() or ql in (a.code or "").lower()]
    if status:
        items = [a for a in items if a.current_version_id and db.get(AssessmentVersion, a.current_version_id).status == status]
    return paginate([_assessment_out(a, db) for a in items], page, page_size)


@router.post("/assessments")
def create_assessment(body: AssessmentCreate, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("assessment.manage"))):
    a = Assessment(code=next_code(db, "assessment"), created_by=actor.id, **body.model_dump())
    db.add(a)
    db.flush()
    ver = AssessmentVersion(assessment_id=a.id, version_number=1, status="draft", created_by=actor.id,
                            items_config={"option_values": {}, "missing_policy": "skip", "reverse_items": [], "validity": {"min_answered_ratio": 0}},
                            scoring_rules={"scales": []}, norm_sets=[])
    db.add(ver)
    db.flush()
    a.current_version_id = ver.id
    log_action(db, actor, "create", "assessment", a.id, a.code)
    db.commit()
    return _assessment_out(a, db)


@router.get("/assessments/{assessment_id}")
def get_assessment(assessment_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    a = db.get(Assessment, assessment_id)
    if not a:
        raise HTTPException(status_code=404, detail="آزمون یافت نشد")
    out = _assessment_out(a, db)
    versions = db.query(AssessmentVersion).filter(AssessmentVersion.assessment_id == a.id).order_by(AssessmentVersion.version_number).all()
    out["versions"] = [{"id": v.id, "version_number": v.version_number, "status": v.status,
                        "year": v.year, "language": v.language, "published_at": v.published_at} for v in versions]
    sources = db.query(AssessmentSource).filter(AssessmentSource.assessment_id == a.id).all()
    out["sources"] = [{"id": s.id, "url": s.url, "title": s.title, "author": s.author,
                       "publisher": s.publisher, "retrieved_at": s.retrieved_at,
                       "source_type": s.source_type, "validation_status": s.validation_status,
                       "usage_terms": s.usage_terms, "approved_by": s.approved_by} for s in sources]
    return out


@router.put("/assessments/{assessment_id}")
def update_assessment(assessment_id: str, body: AssessmentUpdate, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("assessment.manage"))):
    a = db.get(Assessment, assessment_id)
    if not a:
        raise HTTPException(status_code=404, detail="آزمون یافت نشد")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(a, field, val)
    log_action(db, actor, "update", "assessment", a.id, a.code)
    db.commit()
    return _assessment_out(a, db)


@router.post("/assessments/{assessment_id}/versions")
def new_assessment_version(assessment_id: str, body: VersionMetaIn, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("assessment.manage"))):
    """نسخه جدید — ترجمه‌ها و فرم‌های کوتاه/بلند نباید مخلوط شوند (بخش ۹.۲)"""
    a = db.get(Assessment, assessment_id)
    if not a:
        raise HTTPException(status_code=404, detail="آزمون یافت نشد")
    latest = db.query(AssessmentVersion).filter(AssessmentVersion.assessment_id == a.id).order_by(
        AssessmentVersion.version_number.desc()).first()
    ver = AssessmentVersion(assessment_id=a.id, version_number=(latest.version_number + 1) if latest else 1,
                            status="draft", year=body.year, language=body.language or "فارسی",
                            items_config=latest.items_config if latest else {},
                            scoring_rules=latest.scoring_rules if latest else {},
                            norm_sets=latest.norm_sets if latest else [],
                            rules_version_note=body.note, created_by=actor.id)
    db.add(ver)
    db.flush()
    # کپی سؤال‌ها به نسخه جدید
    if latest:
        for it in db.query(AssessmentItem).filter(AssessmentItem.version_id == latest.id).all():
            db.add(AssessmentItem(version_id=ver.id, order=it.order, code=it.code, text=it.text,
                                  item_type=it.item_type, is_reverse=it.is_reverse, weight=it.weight,
                                  options=it.options, scale_codes=it.scale_codes))
    a.current_version_id = ver.id
    log_action(db, actor, "create_version", "assessment", a.id, a.code, {"version": ver.version_number})
    db.commit()
    return {"id": ver.id, "version_number": ver.version_number, "status": ver.status}


@router.get("/assessment-versions/{version_id}")
def get_assessment_version(version_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ver = db.get(AssessmentVersion, version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="نسخه آزمون یافت نشد")
    a = db.get(Assessment, ver.assessment_id)
    items = db.query(AssessmentItem).filter(AssessmentItem.version_id == ver.id).order_by(AssessmentItem.order).all()
    cases = db.query(AssessmentValidationCase).filter(AssessmentValidationCase.version_id == ver.id).all()
    return {
        "id": ver.id, "assessment_id": ver.assessment_id, "assessment_title": a.title_fa if a else None,
        "assessment_code": a.code if a else None,
        "version_number": ver.version_number, "status": ver.status, "year": ver.year,
        "items_config": ver.items_config, "scoring_rules": ver.scoring_rules,
        "norm_sets": ver.norm_sets, "report_template": ver.report_template,
        "rules_version_note": ver.rules_version_note, "published_at": ver.published_at,
        "items": [{"id": i.id, "order": i.order, "code": i.code, "text": i.text, "item_type": i.item_type,
                   "is_reverse": i.is_reverse, "weight": i.weight, "options": i.options,
                   "scale_codes": i.scale_codes} for i in items],
        "validation_cases": [{"id": c.id, "title": c.title, "input_answers": c.input_answers,
                              "expected": c.expected, "note": c.note} for c in cases],
    }


@router.put("/assessment-versions/{version_id}/content")
def save_content(version_id: str, body: AssessmentContentIn, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("assessment.manage"))):
    ver = db.get(AssessmentVersion, version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="نسخه آزمون یافت نشد")
    if ver.status == "published":
        raise HTTPException(status_code=409, detail="نسخه منتشرشده تغییرناپذیر است")
    ver.items_config = body.items_config or {}
    ver.scoring_rules = body.scoring_rules or {}
    ver.norm_sets = body.norm_sets or []
    ver.report_template = body.report_template
    ver.rules_version_note = body.rules_version_note or ver.rules_version_note
    # بازنویسی سؤال‌ها
    db.query(AssessmentItem).filter(AssessmentItem.version_id == ver.id).delete()
    codes = set()
    for idx, it in enumerate(body.items):
        code = it.get("code") or f"q{idx + 1}"
        if code in codes:
            raise HTTPException(status_code=422, detail=f"کد سؤال تکراری: {code}")
        codes.add(code)
        db.add(AssessmentItem(
            version_id=ver.id, order=idx, code=code, text=it.get("text", ""),
            item_type=it.get("item_type", "likert"), is_reverse=bool(it.get("is_reverse")),
            weight=float(it.get("weight") or 1.0), options=it.get("options"),
            scale_codes=it.get("scale_codes") or [],
        ))
    a = db.get(Assessment, ver.assessment_id)
    a.item_count = len(body.items)
    log_action(db, actor, "update_content", "assessment_version", ver.id, a.code, {"items": len(body.items)})
    db.commit()
    return {"ok": True, "items": len(body.items)}


@router.post("/assessment-versions/{version_id}/validation-cases")
def add_validation_case(version_id: str, body: ValidationCaseIn, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("assessment.manage"))):
    ver = db.get(AssessmentVersion, version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="نسخه آزمون یافت نشد")
    case = AssessmentValidationCase(version_id=ver.id, title=body.title, input_answers=body.input_answers,
                                    expected=body.expected, note=body.note)
    db.add(case)
    log_action(db, actor, "add_validation_case", "assessment_version", ver.id)
    db.commit()
    return {"id": case.id}


@router.post("/assessment-versions/{version_id}/validate")
def validate_assessment(version_id: str, db: Session = Depends(get_db), user: User = Depends(RequirePermission("assessment.manage"))):
    """اعتبارسنجی نمره‌گذاری با مثال‌های مرجع (بخش ۱۱.۳)"""
    ver = db.get(AssessmentVersion, version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="نسخه آزمون یافت نشد")
    items = db.query(AssessmentItem).filter(AssessmentItem.version_id == ver.id).order_by(AssessmentItem.order).all()
    problems = []
    if not items:
        problems.append("آزمون بدون سؤال است")
    scales = (ver.scoring_rules or {}).get("scales") or []
    if not scales:
        problems.append("قواعد نمره‌گذاری (مقیاس‌ها) تعریف نشده است")
    if (ver.items_config or {}).get("missing_policy") not in ("skip", "zero", "invalidate"):
        problems.append("سیاست پاسخ ناقص نامعتبر است")
    cases = db.query(AssessmentValidationCase).filter(AssessmentValidationCase.version_id == ver.id).all()
    case_report = None
    if cases and items:
        try:
            case_report = run_validation_cases(ver, items, cases)
            if not case_report["all_passed"]:
                problems.append("مثال‌های مرجع با خروجی سامانه مطابقت ندارند")
        except (ValueError, Exception) as e:
            problems.append(f"خطا در اجرای مثال‌های مرجع: {e}")
            case_report = {"all_passed": False, "error": str(e)}
    a = db.get(Assessment, ver.assessment_id)
    return {"problems": problems, "valid": len(problems) == 0, "cases": case_report}


@router.post("/assessment-versions/{version_id}/publish")
def publish_assessment_version(version_id: str, body: PublishIn, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("assessment.approve"))):
    """انتشار نسخه آزمون — نیازمند تأیید علمی و حقوقی (بخش ۱۰.۱ / AC-10)"""
    ver = db.get(AssessmentVersion, version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="نسخه آزمون یافت نشد")
    a = db.get(Assessment, ver.assessment_id)
    if not a.approved_scientific:
        raise HTTPException(status_code=422, detail="تأیید علمی آزمون ثبت نشده است؛ آزمون تأییدنشده قابل اجرای رسمی نیست")
    if a.license_status not in ("owned", "licensed", "public_domain"):
        raise HTTPException(status_code=422, detail="وضعیت حقوق استفاده آزمون معتبر نیست (owned/licensed/public_domain لازم است)")
    items = db.query(AssessmentItem).filter(AssessmentItem.version_id == ver.id).count()
    if items == 0:
        raise HTTPException(status_code=422, detail="آزمون بدون سؤال قابل انتشار نیست")
    scales = (ver.scoring_rules or {}).get("scales") or []
    if not scales:
        raise HTTPException(status_code=422, detail="قواعد نمره‌گذاری تعریف نشده است")
    ver.status = "published"
    ver.published_at = datetime.now(timezone.utc)
    if body.approved_scientific_by:
        a.approved_scientific_by = body.approved_scientific_by
    if body.approved_legal_by:
        a.approved_legal_by = body.approved_legal_by
    a.current_version_id = ver.id
    log_action(db, actor, "publish", "assessment_version", ver.id, a.code, {"version": ver.version_number})
    db.commit()
    return {"ok": True, "version_number": ver.version_number}


@router.post("/assessments/{assessment_id}/approve")
def approve_assessment(assessment_id: str, body: dict, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("assessment.approve"))):
    """ثبت تأیید علمی/حقوقی (بخش ۹.۱ — وضعیت تأیید علمی و حقوقی)"""
    a = db.get(Assessment, assessment_id)
    if not a:
        raise HTTPException(status_code=404, detail="آزمون یافت نشد")
    if body.get("scientific"):
        a.approved_scientific = True
        a.approved_scientific_by = body.get("by") or actor.full_name
    if body.get("legal"):
        a.approved_legal = True
        a.approved_legal_by = body.get("by") or actor.full_name
    log_action(db, actor, "approve", "assessment", a.id, a.code, body)
    db.commit()
    return {"ok": True}


# ===================== اجرای آزمون =====================

@router.post("/assessment-versions/{version_id}/administrations")
def create_administration(version_id: str, body: AdministrationIn, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("assessment.run"))):
    ver = db.get(AssessmentVersion, version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="نسخه آزمون یافت نشد")
    if ver.status != "published":
        raise HTTPException(status_code=422, detail="آزمون تأییدنشده قابل اجرای رسمی نیست (AC-10)")
    import secrets as _secrets
    admin = AssessmentAdministration(
        version_id=ver.id, respondent_name=body.respondent_name,
        respondent_identifier=body.respondent_identifier,
        assigned_to=body.assigned_to, conducted_by=actor.id,
        status="not_started", public_token=_secrets.token_urlsafe(24),
        token_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(admin)
    log_action(db, actor, "create_administration", "assessment_administration", admin.id, None,
               {"assessment": ver.assessment_id})
    db.commit()
    return {"id": admin.id, "status": admin.status, "public_token": admin.public_token}


@router.get("/assessment-administrations")
def list_administrations(status: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                         db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(AssessmentAdministration).order_by(AssessmentAdministration.created_at.desc())
    if status:
        q = q.filter(AssessmentAdministration.status == status)
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    out = []
    for adm in rows:
        ver = db.get(AssessmentVersion, adm.version_id)
        a = db.get(Assessment, ver.assessment_id) if ver else None
        result = db.query(AssessmentResult).filter(AssessmentResult.administration_id == adm.id).order_by(
            AssessmentResult.created_at.desc()).first()
        out.append({
            "id": adm.id, "status": adm.status, "respondent_name": adm.respondent_name,
            "assessment_title": a.title_fa if a else None, "assessment_code": a.code if a else None,
            "version_number": ver.version_number if ver else None,
            "created_at": adm.created_at, "completed_at": adm.completed_at,
            "has_result": result is not None, "is_valid": result.is_valid if result else None,
        })
    return paginate(out, page, page_size)


@router.get("/assessment-administrations/{admin_id}")
def get_administration(admin_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    adm = db.get(AssessmentAdministration, admin_id)
    if not adm:
        raise HTTPException(status_code=404, detail="اجرای آزمون یافت نشد")
    ver = db.get(AssessmentVersion, adm.version_id)
    a = db.get(Assessment, ver.assessment_id) if ver else None
    items = db.query(AssessmentItem).filter(AssessmentItem.version_id == ver.id).order_by(AssessmentItem.order).all()
    return {
        "id": adm.id, "status": adm.status, "respondent_name": adm.respondent_name,
        "respondent_identifier": adm.respondent_identifier,
        "answers": adm.answers, "started_at": adm.started_at, "completed_at": adm.completed_at,
        "public_token": adm.public_token,
        "assessment": {"id": a.id, "title_fa": a.title_fa, "code": a.code, "duration_minutes": a.duration_minutes} if a else None,
        "version": {"id": ver.id, "version_number": ver.version_number} if ver else None,
        "items": [{"code": i.code, "text": i.text, "item_type": i.item_type, "options": i.options,
                   "is_reverse": i.is_reverse, "order": i.order} for i in items],
    }


@router.post("/assessment-administrations/{admin_id}/start")
def start_administration(admin_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    adm = db.get(AssessmentAdministration, admin_id)
    if not adm:
        raise HTTPException(status_code=404, detail="اجرای آزمون یافت نشد")
    if adm.status == "completed":
        raise HTTPException(status_code=409, detail="این اجرا تکمیل شده است")
    adm.status = "in_progress"
    adm.started_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@router.post("/assessment-administrations/{admin_id}/submit")
def submit_answers(admin_id: str, body: AnswersIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """ثبت پاسخ و محاسبه نمره — ScoreRun با تصویر قواعد (بخش ۱۱)"""
    adm = db.get(AssessmentAdministration, admin_id)
    if not adm:
        raise HTTPException(status_code=404, detail="اجرای آزمون یافت نشد")
    if adm.status == "completed":
        raise HTTPException(status_code=409, detail="پاسخ این اجرا قبلاً ثبت شده است")
    ver = db.get(AssessmentVersion, adm.version_id)
    items = db.query(AssessmentItem).filter(AssessmentItem.version_id == ver.id).order_by(AssessmentItem.order).all()
    try:
        computed = compute_scores(ver, items, body.answers)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    adm.answers = body.answers
    adm.status = "completed"
    adm.completed_at = datetime.now(timezone.utc)

    run = AssessmentScoreRun(administration_id=adm.id,
                             rules_snapshot={"items_config": ver.items_config, "scoring_rules": ver.scoring_rules,
                                             "norm_sets": ver.norm_sets, "version_id": ver.id,
                                             "version_number": ver.version_number},
                             computed=computed, created_by=user.id)
    db.add(run)
    db.flush()
    result = AssessmentResult(
        administration_id=adm.id, score_run_id=run.id,
        raw_scores=computed["raw_scores"], converted_scores=computed["converted_scores"],
        interpretations=computed["interpretations"], completeness=computed["completeness"],
        is_valid=computed["is_valid"],
        report_text=_build_report(ver, computed),
    )
    db.add(result)
    log_action(db, user, "submit_assessment", "assessment_administration", adm.id)
    db.commit()
    return {"ok": True, "result_id": result.id, "computed": computed}


def _build_report(ver: AssessmentVersion, computed: dict) -> str:
    lines = ["نتیجه آزمون — نسخه سؤال‌ها و قواعد: " + str(ver.version_number)]
    for detail in computed.get("scale_details", []):
        lines.append(f"• {detail['title']}: نمره {detail['score']}"
                     + (f" ({detail['interpretation']})" if detail.get("interpretation") else ""))
    lines.append(f"میزان کامل بودن پاسخ‌ها: {computed['completeness']:.0%}")
    if not computed.get("is_valid"):
        lines.append("هشدار: " + (computed.get("invalid_reason") or "نتیجه نامعتبر است"))
    lines.append("توجه: خروجی سامانه ابزار کمک به متخصص است، نه تشخیص قطعی یا جایگزین ارزیابی بالینی.")
    return "\n".join(lines)


@router.get("/assessment-administrations/{admin_id}/results")
def get_results(admin_id: str, db: Session = Depends(get_db), user: User = Depends(RequirePermission("assessment.result.view"))):
    """مشاهده نتایج روان‌شناختی نیازمند مجوز مستقل است (بخش ۳.۲)"""
    adm = db.get(AssessmentAdministration, admin_id)
    if not adm:
        raise HTTPException(status_code=404, detail="اجرای آزمون یافت نشد")
    results = db.query(AssessmentResult).filter(AssessmentResult.administration_id == admin_id).order_by(
        AssessmentResult.created_at.desc()).all()
    runs = db.query(AssessmentScoreRun).filter(AssessmentScoreRun.administration_id == admin_id).order_by(
        AssessmentScoreRun.created_at.desc()).all()
    return {
        "administration_id": admin_id, "status": adm.status,
        "results": [{"id": r.id, "raw_scores": r.raw_scores, "converted_scores": r.converted_scores,
                     "interpretations": r.interpretations, "completeness": r.completeness,
                     "is_valid": r.is_valid, "report_text": r.report_text, "created_at": r.created_at}
                    for r in results],
        "score_runs": [{"id": run.id, "created_at": run.created_at, "created_by": run.created_by} for run in runs],
    }


@router.post("/assessment-administrations/{admin_id}/rescore")
def rescore(admin_id: str, db: Session = Depends(get_db), user: User = Depends(RequirePermission("assessment.result.view"))):
    """محاسبه مجدد — یک اجرای محاسباتی جدید ایجاد می‌کند؛ نتایج قبلی تغییر نمی‌کند"""
    adm = db.get(AssessmentAdministration, admin_id)
    if not adm or adm.status != "completed":
        raise HTTPException(status_code=409, detail="محاسبه مجدد فقط برای اجرای تکمیل‌شده مجاز است")
    ver = db.get(AssessmentVersion, adm.version_id)
    items = db.query(AssessmentItem).filter(AssessmentItem.version_id == ver.id).order_by(AssessmentItem.order).all()
    computed = compute_scores(ver, items, adm.answers or {})
    run = AssessmentScoreRun(administration_id=adm.id,
                             rules_snapshot={"items_config": ver.items_config, "scoring_rules": ver.scoring_rules},
                             computed=computed, created_by=user.id)
    db.add(run)
    db.flush()
    result = AssessmentResult(
        administration_id=adm.id, score_run_id=run.id, raw_scores=computed["raw_scores"],
        interpretations=computed["interpretations"], completeness=computed["completeness"],
        is_valid=computed["is_valid"], report_text=_build_report(ver, computed),
    )
    db.add(result)
    log_action(db, user, "rescore", "assessment_administration", adm.id)
    db.commit()
    return {"ok": True, "result_id": result.id}


# ===================== جست‌وجوی اینترنتی آزمون‌ها (بخش ۱۰) =====================

@router.post("/assessment-discovery/search")
def discovery_search(body: DiscoverySearchIn, db: Session = Depends(get_db), user: User = Depends(RequirePermission("assessment.manage"))):
    """جست‌وجوی نام آزمون در منابع باز — فقط نتایج متادیتا؛ ورود محتوا نیازمند بررسی مجوز است.
    نکته سند ۱۰.۲: یافتن نام آزمون به معنی مجاز بودن ذخیره یا بازنشر سؤال‌ها نیست.
    """
    query = body.query.strip()
    results = []
    errors = []
    # منبع ۱: Wikipedia (فارسی) — منبع باز و مناسب
    try:
        url = f"https://fa.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote_plus(query)}&format=json&srlimit=5"
        r = httpx.get(url, timeout=8, headers={"User-Agent": "Farayara/1.0 (assessment discovery)"})
        if r.status_code == 200:
            data = r.json()
            for hit in (data.get("query", {}).get("search") or []):
                results.append({
                    "title": hit.get("title"),
                    "url": f"https://fa.wikipedia.org/wiki/{quote_plus(str(hit.get('title', '')))}",
                    "snippet": BeautifulSoup(hit.get("snippet") or "", "html.parser").get_text(" ", strip=True),
                    "source": "wikipedia_fa",
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                })
    except Exception as e:
        errors.append(f"جست‌وجوی ویکی‌پدیا ناموفق بود: {type(e).__name__}")

    # منبع ۲: DuckDuckGo HTML (متادیتای نتایج)
    try:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query + ' پرسشنامه آزمون')}"
        r = httpx.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0 (Farayara discovery)"}, follow_redirects=True)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for res in soup.select(".result")[:8]:
                a = res.select_one(".result__a")
                snippet = res.select_one(".result__snippet")
                if a and a.get("href"):
                    results.append({
                        "title": a.get_text(" ", strip=True),
                        "url": a.get("href"),
                        "snippet": snippet.get_text(" ", strip=True) if snippet else "",
                        "source": "duckduckgo",
                        "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    })
    except Exception as e:
        errors.append(f"جست‌وجوی وب ناموفق بود: {type(e).__name__}")

    log_action(db, user, "assessment_discovery", "assessment", None, None, {"query": query, "count": len(results)})
    db.commit()
    return {"query": query, "results": results, "errors": errors,
            "notice": "این نتایج فقط برای بررسی اولیه است؛ ورود محتوای آزمون نیازمند بررسی مجوز حقوقی و تأیید متخصص است."}


@router.post("/assessment-discovery/import")
def discovery_import(body: DiscoveryImportIn, db: Session = Depends(get_db), user: User = Depends(RequirePermission("assessment.manage"))):
    """ورود پیش‌نویس کنترل‌شده از منبع انتخابی — وضعیت پیش‌فرض: عدم تأیید (بخش ۱۰.۱)"""
    a = Assessment(
        code=next_code(db, "assessment"), title_fa=body.title_fa, title_original=body.title_original,
        domain=body.domain, license_status=body.license_status, license_terms=body.license_terms,
        status="active", created_by=user.id,
    )
    db.add(a)
    db.flush()
    ver = AssessmentVersion(assessment_id=a.id, version_number=1, status="draft", created_by=user.id,
                            items_config={}, scoring_rules={"scales": []}, norm_sets=[],
                            rules_version_note="پیش‌نویس اولیه از جست‌وجوی اینترنتی")
    db.add(ver)
    db.flush()
    a.current_version_id = ver.id
    src = AssessmentSource(assessment_id=a.id, url=body.source_url, title=body.source_title,
                           retrieved_at=datetime.now(timezone.utc), source_type="website",
                           validation_status="pending", usage_terms=body.license_terms, note=body.note)
    db.add(src)
    log_action(db, user, "import_draft", "assessment", a.id, a.code, {"url": body.source_url})
    db.commit()
    return {"id": a.id, "code": a.code, "notice": "پیش‌نویس ایجاد شد؛ اجرای رسمی نیازمند تأیید علمی و حقوقی است."}
