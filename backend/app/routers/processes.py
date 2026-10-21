"""مدیریت فرایندها، نسخه‌ها، نمودار BPMN، اجرا و کارتابل (بخش ۴، ۵ سند)"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..deps import RequirePermission, get_current_user
from ..engines.workflow import WorkflowEngine, analyze_version, parse_bpmn
from ..models import (
    Form, FormVersion, Process, ProcessEvent, ProcessInstance, ProcessNodeBinding,
    ProcessTask, ProcessVersion, Role, User,
)
from ..schemas import (
    BindingsIn, CompleteTaskIn, DiagramIn, ProcessCreate, StartInstanceIn, paginate,
)
from ..utils import next_code

router = APIRouter(tags=["processes"])


def _process_out(p: Process, db: Session) -> dict:
    cur = db.get(ProcessVersion, p.current_version_id) if p.current_version_id else None
    owner = db.get(User, p.owner_id) if p.owner_id else None
    return {
        "id": p.id, "code": p.code, "title": p.title, "description": p.description,
        "purpose": p.purpose, "category": p.category, "tags": p.tags or [], "unit": p.unit,
        "owner": {"id": owner.id, "full_name": owner.full_name} if owner else None,
        "inputs_desc": p.inputs_desc, "outputs_desc": p.outputs_desc,
        "expected_duration_days": p.expected_duration_days, "confidentiality": p.confidentiality,
        "status": p.status,
        "current_version_id": p.current_version_id,
        "current_version_number": cur.version_number if cur else None,
        "current_version_status": cur.status if cur else None,
        "created_at": p.created_at, "updated_at": p.updated_at,
    }


@router.get("/processes")
def list_processes(query: str | None = None, status: str | None = None, category: str | None = None,
                   page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    procs = db.query(Process).order_by(Process.created_at.desc()).all()
    if query:
        ql = query.strip().lower()
        procs = [p for p in procs if ql in p.title.lower() or ql in (p.code or "").lower()]
    if category:
        procs = [p for p in procs if p.category == category]
    if status:
        procs = [p for p in procs if p.current_version_id and db.get(ProcessVersion, p.current_version_id).status == status]
    return paginate([_process_out(p, db) for p in procs], page, page_size)


@router.post("/processes")
def create_process(body: ProcessCreate, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("process.create"))):
    p = Process(code=next_code(db, "process"), title=body.title.strip(), description=body.description,
                purpose=body.purpose, category=body.category, tags=body.tags or [], unit=body.unit,
                owner_id=body.owner_id, expected_duration_days=body.expected_duration_days,
                confidentiality=body.confidentiality, created_by=actor.id)
    db.add(p)
    db.flush()
    ver = ProcessVersion(process_id=p.id, version_number=1, status="draft", bpmn_xml=None,
                         exec_config={}, created_by=actor.id)
    db.add(ver)
    db.flush()
    p.current_version_id = ver.id
    log_action(db, actor, "create", "process", p.id, p.code)
    db.commit()
    return _process_out(p, db)


@router.get("/processes/{process_id}")
def get_process(process_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.get(Process, process_id)
    if not p:
        raise HTTPException(status_code=404, detail="فرایند یافت نشد")
    out = _process_out(p, db)
    versions = db.query(ProcessVersion).filter(ProcessVersion.process_id == p.id).order_by(ProcessVersion.version_number).all()
    out["versions"] = [
        {"id": v.id, "version_number": v.version_number, "status": v.status, "created_at": v.created_at,
         "published_at": v.published_at, "notes": v.notes}
        for v in versions
    ]
    instances = db.query(ProcessInstance).filter(ProcessInstance.process_id == p.id).order_by(
        ProcessInstance.started_at.desc()).limit(20).all()
    out["recent_instances"] = [
        {"id": i.id, "trace_code": i.trace_code, "status": i.status, "started_at": i.started_at,
         "ended_at": i.ended_at, "title": i.title}
        for i in instances
    ]
    return out


@router.put("/processes/{process_id}")
def update_process(process_id: str, body: ProcessCreate, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("process.create"))):
    p = db.get(Process, process_id)
    if not p:
        raise HTTPException(status_code=404, detail="فرایند یافت نشد")
    for field in ("title", "description", "purpose", "category", "unit", "confidentiality"):
        val = getattr(body, field)
        if val is not None:
            setattr(p, field, val)
    if body.owner_id is not None:
        p.owner_id = body.owner_id
    if body.expected_duration_days is not None:
        p.expected_duration_days = body.expected_duration_days
    if body.tags is not None:
        p.tags = body.tags
    log_action(db, actor, "update", "process", p.id, p.code)
    db.commit()
    return _process_out(p, db)


@router.post("/processes/{process_id}/versions")
def new_process_version(process_id: str, body: dict | None = None, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("process.create"))):
    p = db.get(Process, process_id)
    if not p:
        raise HTTPException(status_code=404, detail="فرایند یافت نشد")
    latest = db.query(ProcessVersion).filter(ProcessVersion.process_id == p.id).order_by(
        ProcessVersion.version_number.desc()).first()
    ver = ProcessVersion(
        process_id=p.id, version_number=(latest.version_number + 1) if latest else 1, status="draft",
        bpmn_xml=latest.bpmn_xml if latest else None, exec_config=latest.exec_config if latest else {},
        notes=(body or {}).get("note") if body else None, created_by=actor.id,
    )
    db.add(ver)
    db.flush()
    p.current_version_id = ver.id
    log_action(db, actor, "create_version", "process", p.id, p.code, {"version": ver.version_number})
    db.commit()
    return {"id": ver.id, "version_number": ver.version_number, "status": ver.status}


@router.get("/process-versions/{version_id}")
def get_process_version(version_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ver = db.get(ProcessVersion, version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="نسخه فرایند یافت نشد")
    p = db.get(Process, ver.process_id)
    bindings = db.query(ProcessNodeBinding).filter(ProcessNodeBinding.process_version_id == ver.id).all()
    return {
        "id": ver.id, "process_id": ver.process_id, "process_code": p.code if p else None,
        "process_title": p.title if p else None,
        "version_number": ver.version_number, "status": ver.status,
        "bpmn_xml": ver.bpmn_xml, "diagram_svg": ver.diagram_svg,
        "exec_config": ver.exec_config, "notes": ver.notes, "published_at": ver.published_at,
        "bindings": [
            {"node_id": b.node_id, "node_type": b.node_type, "node_name": b.node_name,
             "form_version_id": b.form_version_id, "role_id": b.role_id, "assignee_id": b.assignee_id,
             "condition": b.condition, "config": b.config}
            for b in bindings
        ],
    }


@router.put("/process-versions/{version_id}/diagram")
def save_diagram(version_id: str, body: DiagramIn, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("process.create"))):
    """ذخیره BPMN XML + تصویر SVG — ساختار پس از ذخیره و بازگشایی حفظ می‌شود (AC-01)"""
    ver = db.get(ProcessVersion, version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="نسخه فرایند یافت نشد")
    if ver.status == "published":
        raise HTTPException(status_code=409, detail="نسخه منتشرشده تغییرناپذیر است؛ نسخه جدید بسازید")
    analysis = analyze_version(body.bpmn_xml)
    if not analysis["valid"]:
        raise HTTPException(status_code=422, detail=analysis["errors"])
    ver.bpmn_xml = body.bpmn_xml
    if body.svg:
        ver.diagram_svg = body.svg
    log_action(db, actor, "save_diagram", "process_version", ver.id, None, analysis["stats"])
    db.commit()
    return {"ok": True, "analysis": analysis}


@router.post("/process-versions/{version_id}/validate")
def validate_version(version_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """اعتبارسنجی + شناسایی عناصر خارج از دامنه اجرا (AC-02)"""
    ver = db.get(ProcessVersion, version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="نسخه فرایند یافت نشد")
    analysis = analyze_version(ver.bpmn_xml or "")
    bindings = db.query(ProcessNodeBinding).filter(ProcessNodeBinding.process_version_id == ver.id).all()
    bound_nodes = {b.node_id for b in bindings}
    parsed = parse_bpmn(ver.bpmn_xml or "")
    missing_forms = []
    for node in parsed["nodes"].values():
        if node["type"] == "userTask" and node["id"] not in bound_nodes:
            missing_forms.append(f"وظیفه «{node.get('name') or node['id']}» فرم یا مجری ندارد")
    analysis["warnings"].extend(missing_forms)
    return analysis


@router.put("/process-versions/{version_id}/bindings")
def save_bindings(version_id: str, body: BindingsIn, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("process.create"))):
    ver = db.get(ProcessVersion, version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="نسخه فرایند یافت نشد")
    if ver.status == "published":
        raise HTTPException(status_code=409, detail="نسخه منتشرشده تغییرناپذیر است")
    db.query(ProcessNodeBinding).filter(ProcessNodeBinding.process_version_id == ver.id).delete()
    for b in body.bindings:
        if not b.get("node_id"):
            continue
        db.add(ProcessNodeBinding(
            process_version_id=ver.id,
            node_id=b["node_id"], node_type=b.get("node_type", "userTask"),
            node_name=b.get("node_name"),
            form_version_id=b.get("form_version_id"),
            role_id=b.get("role_id"),
            assignee_id=b.get("assignee_id"),
            condition=b.get("condition"),
            config=b.get("config") or {},
        ))
    log_action(db, actor, "update_bindings", "process_version", ver.id, None, {"count": len(body.bindings)})
    db.commit()
    return {"ok": True}


@router.post("/process-versions/{version_id}/publish")
def publish_version(version_id: str, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("process.publish"))):
    ver = db.get(ProcessVersion, version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="نسخه فرایند یافت نشد")
    if ver.status == "published":
        raise HTTPException(status_code=409, detail="این نسخه قبلاً منتشر شده است")
    analysis = analyze_version(ver.bpmn_xml or "")
    if not analysis["valid"]:
        raise HTTPException(status_code=422, detail=analysis["errors"])
    if analysis["unsupported"]:
        # پیام روشن برای عناصر خارج از دامنه اجرا (بخش ۴.۲)
        raise HTTPException(status_code=422, detail={
            "message": "انتشار اجرایی ناموفق؛ عناصر خارج از دامنه موتور اجرا:",
            "unsupported": analysis["unsupported"],
        })
    ver.status = "published"
    ver.published_at = datetime.now(timezone.utc)
    ver.published_by = actor.id
    p = db.get(Process, ver.process_id)
    p.current_version_id = ver.id
    log_action(db, actor, "publish", "process_version", ver.id, p.code, {"version": ver.version_number})
    db.commit()
    return {"ok": True, "version_number": ver.version_number}


@router.post("/process-versions/{version_id}/instances")
def start_instance(version_id: str, body: StartInstanceIn, db: Session = Depends(get_db),
                   actor: User = Depends(RequirePermission("process.start"))):
    engine = WorkflowEngine(db)
    ver = db.get(ProcessVersion, version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="نسخه فرایند یافت نشد")
    try:
        instance = engine.start(ver, actor.id, body.variables, body.title)
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e))
    log_action(db, actor, "start_instance", "process_instance", instance.id, instance.trace_code)
    db.commit()
    return {"id": instance.id, "trace_code": instance.trace_code, "status": instance.status}


@router.get("/process-instances/{instance_id}")
def get_instance(instance_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inst = db.get(ProcessInstance, instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail="نمونه یافت نشد")
    events = db.query(ProcessEvent).filter(ProcessEvent.instance_id == inst.id).order_by(ProcessEvent.created_at).all()
    tasks = db.query(ProcessTask).filter(ProcessTask.instance_id == inst.id).order_by(ProcessTask.created_at).all()
    return {
        "id": inst.id, "trace_code": inst.trace_code, "status": inst.status, "title": inst.title,
        "variables": inst.variables, "current_node_id": inst.current_node_id,
        "started_at": inst.started_at, "ended_at": inst.ended_at,
        "events": [{"type": e.event_type, "node_id": e.node_id, "message": e.message,
                    "created_at": e.created_at, "data": e.data} for e in events],
        "tasks": [{"id": t.id, "node_id": t.node_id, "node_name": t.node_name, "status": t.status,
                   "assignee_id": t.assignee_id, "role_id": t.role_id, "form_version_id": t.form_version_id,
                   "created_at": t.created_at, "completed_at": t.completed_at} for t in tasks],
    }


@router.post("/process-instances/{instance_id}/cancel")
def cancel_instance(instance_id: str, db: Session = Depends(get_db), actor: User = Depends(RequirePermission("process.admin"))):
    inst = db.get(ProcessInstance, instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail="نمونه یافت نشد")
    if inst.status != "running":
        raise HTTPException(status_code=409, detail="فقط نمونه در حال اجرا لغو می‌شود")
    inst.status = "cancelled"
    inst.ended_at = datetime.now(timezone.utc)
    db.query(ProcessTask).filter(ProcessTask.instance_id == inst.id, ProcessTask.status == "pending").update(
        {"status": "cancelled"}, synchronize_session=False)
    db.add(ProcessEvent(instance_id=inst.id, event_type="cancelled", message="نمونه لغو شد", actor_id=actor.id))
    log_action(db, actor, "cancel_instance", "process_instance", inst.id, inst.trace_code)
    db.commit()
    return {"ok": True}


# ===================== کارتابل (بخش ۱۴) =====================

@router.get("/tasks/my")
def my_tasks(status: str = "pending", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(ProcessTask).filter(ProcessTask.status == status)
    role_ids = [r.id for r in (user.roles or [])]
    from sqlalchemy import or_
    q = q.filter(or_(ProcessTask.assignee_id == user.id, ProcessTask.role_id.in_(role_ids) if role_ids else False))
    tasks = q.order_by(ProcessTask.created_at.desc()).all()
    out = []
    for t in tasks:
        inst = db.get(ProcessInstance, t.instance_id)
        form_version = db.get(FormVersion, t.form_version_id) if t.form_version_id else None
        out.append({
            "id": t.id, "node_name": t.node_name, "status": t.status,
            "instance_id": t.instance_id, "trace_code": inst.trace_code if inst else None,
            "instance_title": inst.title if inst else None,
            "process_title": (db.get(Process, inst.process_id).title if inst and inst.process_id else None),
            "form_version_id": t.form_version_id,
            "form_title": form_version and (db.get(Form, form_version.form_id).title if form_version.form_id else None),
            "created_at": t.created_at, "completed_at": t.completed_at,
        })
    return out


@router.get("/tasks/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = db.get(ProcessTask, task_id)
    if not t:
        raise HTTPException(status_code=404, detail="وظیفه یافت نشد")
    inst = db.get(ProcessInstance, t.instance_id)
    form_version = db.get(FormVersion, t.form_version_id) if t.form_version_id else None
    return {
        "id": t.id, "node_name": t.node_name, "status": t.status, "created_at": t.created_at,
        "instance": {"id": inst.id, "trace_code": inst.trace_code, "title": inst.title, "status": inst.status} if inst else None,
        "form_version": ({"id": form_version.id, "version_number": form_version.version_number,
                          "schema_json": form_version.schema_json} if form_version else None),
        "payload": t.payload,
    }


@router.post("/tasks/{task_id}/complete")
def complete_task(task_id: str, body: CompleteTaskIn, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    """تکمیل وظیفه — جلوگیری از دو انتقال تکراری (AC-04) + ثبت پاسخ فرم مرتبط"""
    t = db.get(ProcessTask, task_id)
    if not t:
        raise HTTPException(status_code=404, detail="وظیفه یافت نشد")
    # کنترل مجری: خود کاربر یا نقش او
    role_ids = {r.id for r in (actor.roles or [])}
    if t.assignee_id and t.assignee_id != actor.id:
        raise HTTPException(status_code=403, detail="این وظیفه به کاربر دیگری تخصیص یافته است")
    if not t.assignee_id and t.role_id and t.role_id not in role_ids:
        raise HTTPException(status_code=403, detail="وظیفه مربوط به نقش دیگری است")

    engine = WorkflowEngine(db)
    try:
        # ثبت پاسخ فرم در صورت اتصال فرم به وظیفه
        if t.form_version_id and body.data:
            form_ver = db.get(FormVersion, t.form_version_id)
            if form_ver and form_ver.status == "published":
                from ..models import FormSubmission
                from ..utils import new_trace_code
                sub = FormSubmission(
                    trace_code=new_trace_code(db, "TRK"), form_version_id=form_ver.id,
                    submitted_by=actor.id, process_instance_id=t.instance_id, process_task_id=t.id,
                    status="final", data=body.data,
                )
                db.add(sub)
                db.flush()
        engine.complete_task(t, body.data, actor.id)
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    log_action(db, actor, "complete_task", "process_task", t.id, t.node_name)
    db.commit()
    inst = db.get(ProcessInstance, t.instance_id)
    return {"ok": True, "instance_status": inst.status, "trace_code": inst.trace_code}
