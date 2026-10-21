"""داشبوردها — شاخص‌ها با تعریف محاسباتی روشن (بخش ۱۳ سند)"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import (
    Assessment, AssessmentAdministration, Contract, ContractTemplate, FieldDefinition,
    Form, FormSubmission, FormVersion, Process, ProcessInstance, ProcessTask, ProcessVersion, User,
)

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """داشبورد عمومی — هر شاخص تعریف محاسباتی مشخص دارد"""
    def ver_status(model, table_status_col, status_value):
        return db.query(func.count(model.id)).join(
            type(table_status_col), table_status_col.id == model.current_version_id
        ).filter(table_status_col.status == status_value).scalar() or 0

    processes_total = db.query(func.count(Process.id)).scalar() or 0
    forms_total = db.query(func.count(Form.id)).scalar() or 0
    forms_published = db.query(func.count(FormVersion.id)).filter(FormVersion.status == "published").scalar() or 0
    processes_published = db.query(func.count(ProcessVersion.id)).filter(ProcessVersion.status == "published").scalar() or 0
    fields_active = db.query(func.count(FieldDefinition.id)).filter(FieldDefinition.status == "active").scalar() or 0
    submissions_total = db.query(func.count(FormSubmission.id)).filter(FormSubmission.status == "final").scalar() or 0
    assessments_total = db.query(func.count(Assessment.id)).scalar() or 0
    administrations_total = db.query(func.count(AssessmentAdministration.id)).scalar() or 0
    templates_total = db.query(func.count(ContractTemplate.id)).scalar() or 0
    contracts_total = db.query(func.count(Contract.id)).scalar() or 0
    open_tasks = db.query(func.count(ProcessTask.id)).filter(ProcessTask.status == "pending").scalar() or 0
    my_open_tasks = db.query(func.count(ProcessTask.id)).filter(
        ProcessTask.status == "pending", ProcessTask.assignee_id == user.id).scalar() or 0

    # روند پاسخ‌های ۱۴ روز اخیر
    since = datetime.now(timezone.utc) - timedelta(days=14)
    subs = db.query(FormSubmission.submitted_at).filter(FormSubmission.submitted_at >= since).all()
    by_day: dict = {}
    for (dt,) in subs:
        key = str(dt)[:10] if dt else ""
        by_day[key] = by_day.get(key, 0) + 1
    trend = [{"date": d, "count": by_day.get(d, 0)}
             for d in sorted({str((datetime.now(timezone.utc) - timedelta(days=i)))[:10] for i in range(14)})]

    # وضعیت نسخه‌های فرایند
    proc_status = dict(db.query(ProcessVersion.status, func.count(ProcessVersion.id)).group_by(ProcessVersion.status).all())
    form_status = dict(db.query(FormVersion.status, func.count(FormVersion.id)).group_by(FormVersion.status).all())

    # پراستفاده‌ترین فیلدها (بر اساس تعداد فرم‌های منطقی متمایز — تعریف داشبورد اصلی سند)
    from ..models import FormFieldUsage
    top_fields = (
        db.query(FieldDefinition.title_fa, FieldDefinition.code, func.count(func.distinct(FormVersion.form_id)).label("cnt"))
        .join(FormFieldUsage, FormFieldUsage.field_id == FieldDefinition.id)
        .join(FormVersion, FormVersion.id == FormFieldUsage.form_version_id)
        .group_by(FieldDefinition.id).order_by(func.count(func.distinct(FormVersion.form_id)).desc())
        .limit(8).all()
    )

    return {
        "counts": {
            "processes": processes_total,
            "processes_published_versions": processes_published,
            "forms": forms_total,
            "forms_published_versions": forms_published,
            "fields_active": fields_active,
            "submissions": submissions_total,
            "assessments": assessments_total,
            "assessment_administrations": administrations_total,
            "contract_templates": templates_total,
            "contracts": contracts_total,
            "open_tasks": open_tasks,
            "my_open_tasks": my_open_tasks,
        },
        "charts": {
            "process_version_status": [{"status": k, "count": v} for k, v in proc_status.items()],
            "form_version_status": [{"status": k, "count": v} for k, v in form_status.items()],
            "submissions_trend": trend,
            "top_fields": [{"title": t, "code": c, "forms_count": n} for t, c, n in top_fields],
        },
    }


@router.get("/processes")
def process_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """داشبورد فرایند (بخش ۱۳.۲)"""
    instances_total = db.query(func.count(ProcessInstance.id)).scalar() or 0
    by_status = dict(db.query(ProcessInstance.status, func.count(ProcessInstance.id)).group_by(ProcessInstance.status).all())
    # میانگین زمان تکمیل (ثانیه)
    completed = db.query(ProcessInstance.started_at, ProcessInstance.ended_at).filter(
        ProcessInstance.status == "completed", ProcessInstance.ended_at.isnot(None)).all()
    durations = [(e - s).total_seconds() for s, e in completed if s and e]
    avg_seconds = round(sum(durations) / len(durations), 1) if durations else None
    # توزیع وظایف
    task_status = dict(db.query(ProcessTask.status, func.count(ProcessTask.id)).group_by(ProcessTask.status).all())
    # مراحل پرمشغله (وظایف در انتظار به تفکیک گره)
    busy_nodes = (
        db.query(ProcessTask.node_name, func.count(ProcessTask.id))
        .filter(ProcessTask.status == "pending").group_by(ProcessTask.node_name)
        .order_by(func.count(ProcessTask.id).desc()).limit(8).all()
    )
    return {
        "instances": {"total": instances_total, "by_status": by_status},
        "avg_completion_seconds": avg_seconds,
        "tasks_by_status": task_status,
        "busy_nodes": [{"node": n or "—", "pending": c} for n, c in busy_nodes],
    }


@router.get("/catalog")
def catalog_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """داشبورد کاتالوگ (بخش ۱۳.۳)"""
    from ..models import FormFieldUsage
    total_fields = db.query(func.count(FieldDefinition.id)).scalar() or 0
    active_fields = db.query(func.count(FieldDefinition.id)).filter(FieldDefinition.status == "active").scalar() or 0
    # فیلدهای بدون استفاده
    used_ids = {r[0] for r in db.query(FormFieldUsage.field_id).filter(FormFieldUsage.field_id.isnot(None)).distinct().all()}
    all_fields = db.query(FieldDefinition).all()
    unused = [{"id": f.id, "code": f.code, "title_fa": f.title_fa}
              for f in all_fields if f.id not in used_ids and f.status == "active"]
    # حساس‌ها
    sensitive = [{"code": f.code, "title_fa": f.title_fa, "sensitivity": f.sensitivity}
                 for f in all_fields if f.sensitivity in ("sensitive", "highly_sensitive")]
    by_category: dict = {}
    for f in all_fields:
        cat = f.category or "بدون دسته"
        by_category[cat] = by_category.get(cat, 0) + 1
    return {
        "total_fields": total_fields, "active_fields": active_fields,
        "unused_fields": unused[:20], "unused_count": len(unused),
        "sensitive_fields": sensitive,
        "by_category": [{"category": k, "count": v} for k, v in by_category.items()],
    }
