"""موتور اجرای محدود فرایند — نسخه نخست (بخش ۵.۲ سند)

دامنه اجرایی پشتیبانی‌شده:
- رویداد شروع ساده / رویداد پایان ساده
- User Task
- مسیر ترتیبی (Sequence Flow)
- Exclusive Gateway با شرط کنترل‌شده روی داده‌های فرم

هر عنصر دیگر (Parallel/Inclusive/Event-Based Gateway، Timer، Service Task،
Subprocess، پیام‌ها و ...) خارج از دامنه اجراست و در validate با پیام روشن
گزارش می‌شود (اصل جداسازی طراحی از اجرا — بخش ۱ سند).
"""
import re
import xml.etree.ElementTree as ET

from sqlalchemy.orm import Session

from ..engines.safe_eval import SafeEvalError, safe_eval
from ..models import (
    Notification, ProcessEvent, ProcessInstance, ProcessNodeBinding, ProcessTask, ProcessVersion,
)
from ..utils import new_trace_code

MAX_STEPS = 200

SUPPORTED_TYPES = {"startEvent", "endEvent", "userTask", "sequenceFlow", "exclusiveGateway"}

WARN_TYPES = {
    "task": "Task ساده — برای اجرا به User Task تبدیل شود",
    "serviceTask": "Service Task — خارج از دامنه اجرای نسخه نخست",
    "manualTask": "Manual Task — خارج از دامنه اجرای نسخه نخست",
    "scriptTask": "Script Task — خارج از دامنه اجرای نسخه نخست",
    "businessRuleTask": "Business Rule Task — خارج از دامنه اجرای نسخه نخست",
    "sendTask": "Send Task — خارج از دامنه اجرای نسخه نخست",
    "receiveTask": "Receive Task — خارج از دامنه اجرای نسخه نخست",
    "parallelGateway": "Parallel Gateway — اجرای موازی در توسعه بعدی",
    "inclusiveGateway": "Inclusive Gateway — خارج از دامنه اجرای نسخه نخست",
    "eventBasedGateway": "Event-Based Gateway — خارج از دامنه اجرای نسخه نخست",
    "intermediateCatchEvent": "رویداد میانی — خارج از دامنه اجرای نسخه نخست",
    "intermediateThrowEvent": "رویداد میانی — خارج از دامنه اجرای نسخه نخست",
    "boundaryEvent": "Boundary Event — خارج از دامنه اجرای نسخه نخست",
    "subProcess": "زیرفرایند — در توسعه بعدی",
    "callActivity": "Call Activity — در توسعه بعدی",
    "timerStartEvent": "رویداد شروع زمان‌دار — در توسعه بعدی",
    "messageStartEvent": "رویداد شروع پیامی — در توسعه بعدی",
}


def _local(tag: str) -> str:
    return tag.split("}")[-1]


def parse_bpmn(xml_text: str) -> dict:
    """پارس BPMN XML و استخراج گره‌ها و یال‌ها — مقاوم در برابر namespaceهای مختلف"""
    result = {"nodes": {}, "flows": {}, "process_id": None, "errors": []}
    if not xml_text or not xml_text.strip():
        result["errors"].append("نمودار BPMN خالی است")
        return result
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        result["errors"].append(f"XML نامعتبر است: {e}")
        return result

    process = None
    for el in root.iter():
        if _local(el.tag) == "process":
            process = el
            break
    if process is None:
        result["errors"].append("عنصر process در نمودار یافت نشد")
        return result

    result["process_id"] = process.get("id")

    def walk(parent):
        for child in parent:
            t = _local(child.tag)
            if t == "sequenceFlow":
                result["flows"][child.get("id")] = {
                    "id": child.get("id"),
                    "name": child.get("name"),
                    "sourceRef": child.get("sourceRef"),
                    "targetRef": child.get("targetRef"),
                }
                cond = None
                for sub in child:
                    if _local(sub.tag) == "conditionExpression":
                        cond = (sub.text or "").strip()
                if cond:
                    result["flows"][child.get("id")]["condition"] = cond
            elif t in ("laneSet", "lane", "dataObject", "dataStore", "textAnnotation", "extensionElements", "documentation", "ioSpecification", "multiInstanceLoopCharacteristics", "standardLoopCharacteristics"):
                pass  # عناصر غیراجرایی — نادیده گرفته می‌شوند
            elif t in SUPPORTED_TYPES or t in WARN_TYPES:
                result["nodes"][child.get("id")] = {"id": child.get("id"), "type": t, "name": child.get("name") or t}
                walk(child)  # برای رویدادهای تخصصی مثل timerStartEvent
            else:
                walk(child)

    walk(process)
    return result


def analyze_version(xml_text: str) -> dict:
    """اعتبارسنجی ساختاری + شناسایی عناصر خارج از دامنه اجرا (AC-02)"""
    parsed = parse_bpmn(xml_text)
    errors = list(parsed["errors"])
    warnings = []
    unsupported = []
    nodes = parsed["nodes"]
    flows = parsed["flows"]

    types_count: dict[str, int] = {}
    for node in nodes.values():
        types_count[node["type"]] = types_count.get(node["type"], 0) + 1
        if node["type"] not in SUPPORTED_TYPES and node["type"] not in ("startEvent", "endEvent", "userTask"):
            # رویدادهای تخصصی مثل timerStartEvent هم نوعشان متفاوت گزارش شود
            if node["type"] not in SUPPORTED_TYPES:
                unsupported.append({"node_id": node["id"], "type": node["type"], "name": node["name"],
                                    "message": WARN_TYPES.get(node["type"], "عنصر خارج از دامنه اجرا")})
        if node["type"] == "task":
            pass

    starts = [n for n in nodes.values() if n["type"] == "startEvent"]
    ends = [n for n in nodes.values() if n["type"] == "endEvent"]
    if parsed["errors"]:
        return {"valid": False, "errors": errors, "warnings": warnings, "unsupported": unsupported, "stats": {}}
    if len(starts) == 0:
        errors.append("رویداد شروع (Start Event) یافت نشد")
    if len(ends) == 0:
        errors.append("رویداد پایان (End Event) یافت نشد")
    if len(starts) > 1:
        errors.append("نسخه نخست فقط یک رویداد شروع ساده را پشتیبانی می‌کند")

    # بررسی اتصال یال‌ها
    for flow_id, flow in flows.items():
        if flow["sourceRef"] not in nodes:
            warnings.append(f"یال {flow_id} به گره مبدأ نامعلوم اشاره می‌کند")
        if flow["targetRef"] not in nodes:
            warnings.append(f"یال {flow_id} به گره مقصد نامعلوم اشاره می‌کند")

    # بررسی شرط‌های مسیرهای خروجی gateway
    for flow_id, flow in flows.items():
        src = nodes.get(flow["sourceRef"])
        if src and src["type"] == "exclusiveGateway":
            if not flow.get("condition"):
                warnings.append(f"مسیر «{flow.get('name') or flow_id}» خروجی gateway بدون شرط است")

    stats = {"nodes": len(nodes), "flows": len(flows)}
    for t, c in types_count.items():
        stats[t] = c
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "unsupported": unsupported,
        "stats": stats,
    }


class WorkflowEngine:
    """موتور اجرای محدود فرایند"""

    def __init__(self, db: Session):
        self.db = db

    # ---------- کمکی‌ها ----------
    def _load(self, version: ProcessVersion):
        parsed = parse_bpmn(version.bpmn_xml or "")
        bindings = {}
        for b in self.db.query(ProcessNodeBinding).filter(
            ProcessNodeBinding.process_version_id == version.id
        ).all():
            bindings[b.node_id] = b
        return parsed, bindings

    def _event(self, instance: ProcessInstance, event_type: str, node_id=None, message=None, actor_id=None, data=None):
        self.db.add(ProcessEvent(
            instance_id=instance.id, event_type=event_type, node_id=node_id,
            message=message, actor_id=actor_id, data=data or None,
        ))

    def _notify(self, user_id, title, body, link=None):
        if user_id:
            self.db.add(Notification(user_id=user_id, title=title, body=body, link=link))

    # ---------- شروع نمونه ----------
    def start(self, version: ProcessVersion, started_by: str | None, variables: dict | None, title: str | None = None) -> ProcessInstance:
        if version.status != "published":
            raise ValueError("شروع فرایند فقط روی نسخه منتشرشده مجاز است (AC-03)")
        analysis = analyze_version(version.bpmn_xml or "")
        if not analysis["valid"]:
            raise ValueError("نمودار نسخه معتبر نیست: " + "؛ ".join(analysis["errors"]))
        if analysis["unsupported"]:
            names = "؛ ".join(u["message"] for u in analysis["unsupported"])
            raise ValueError("این نسخه شامل عناصر خارج از دامنه اجراست و قابل اجرای خودکار نیست: " + names)

        parsed, bindings = self._load(version)
        start_nodes = [n for n in parsed["nodes"].values() if n["type"] == "startEvent"]
        if not start_nodes:
            raise ValueError("رویداد شروع یافت نشد")
        start = start_nodes[0]

        instance = ProcessInstance(
            trace_code=new_trace_code(self.db, "INS"),
            process_id=version.process_id,
            process_version_id=version.id,
            title=title,
            status="running",
            current_node_id=start["id"],
            variables=dict(variables or {}),
            started_by=started_by,
        )
        self.db.add(instance)
        self.db.flush()
        self._event(instance, "started", node_id=start["id"], message="نمونه فرایند آغاز شد", actor_id=started_by)
        self._advance(version, instance, parsed, bindings, start["id"], actor_id=started_by)
        return instance

    # ---------- پیشروی موتور ----------
    def _advance(self, version, instance: ProcessInstance, parsed, bindings, from_node: str, actor_id=None):
        """پیاده‌سازی مسیر تا رسیدن به وظیفه کاربری یا پایان (حالت انتظار)"""
        current = from_node
        for _ in range(MAX_STEPS):
            node = parsed["nodes"].get(current)
            if node is None:
                raise ValueError(f"گره {current} در نمودار یافت نشد")
            t = node["type"]

            if t == "userTask" or t == "task":
                self._create_task(version, instance, node, bindings, actor_id)
                instance.current_node_id = current
                return

            if t == "endEvent":
                instance.status = "completed"
                instance.current_node_id = current
                instance.ended_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
                self._event(instance, "completed", node_id=current, message="فرایند با موفقیت خاتمه یافت", actor_id=actor_id)
                return

            if t == "exclusiveGateway":
                outgoing = [f for f in parsed["flows"].values() if f["sourceRef"] == current]
                chosen = self._choose_flow(outgoing, instance.variables or {})
                self._event(instance, "flow_taken", node_id=chosen["id"],
                            message=f"انتخاب مسیر: {chosen.get('name') or chosen['id']}",
                            actor_id=actor_id, data={"condition": chosen.get("condition")})
                current = chosen["targetRef"]
                continue

            if t == "startEvent":
                outgoing = [f for f in parsed["flows"].values() if f["sourceRef"] == current]
                if not outgoing:
                    raise ValueError("رویداد شروع به هیچ مسیری متصل نیست")
                current = outgoing[0]["targetRef"]
                continue

            # عناصر پشتیبانی‌نشده که به هر حال به اینجا رسیده‌اند
            raise ValueError(f"عنصر «{t}» در دامنه اجرای موتور نسخه نخست نیست")

        raise ValueError("تعداد گام‌های اجرا از حد مجاز گذشت — احتمال حلقه در نمودار")

    def _choose_flow(self, outgoing: list, variables: dict) -> dict:
        """انتخاب مسیر در Exclusive Gateway بر اساس شرط‌ها"""
        evaluated = []
        for flow in outgoing:
            cond = flow.get("condition")
            if not cond:
                evaluated.append((flow, True))  # مسیر پیش‌فرض بدون شرط
                continue
            try:
                ok = bool(safe_eval(cond, variables))
            except SafeEvalError as e:
                raise ValueError(f"خطا در ارزیابی شرط مسیر «{flow.get('name') or flow['id']}»: {e}")
            evaluated.append((flow, bool(ok)))
        true_flows = [f for f, ok in evaluated if ok]
        if len(true_flows) == 1:
            return true_flows[0]
        if len(true_flows) > 1:
            raise ValueError("چند مسیر هم‌زمان درست ارزیابی شد؛ شرط‌ها را اصلاح کنید")
        defaults = [f for f, ok in evaluated if ok]
        if defaults:
            return defaults[0]
        raise ValueError("هیچ مسیری با شرط‌های فعلی برقرار نیست")

    def _create_task(self, version, instance, node, bindings, actor_id=None):
        existing = self.db.query(ProcessTask).filter(
            ProcessTask.instance_id == instance.id,
            ProcessTask.node_id == node["id"],
            ProcessTask.status == "pending",
        ).first()
        if existing:
            return existing
        binding = bindings.get(node["id"])
        task = ProcessTask(
            instance_id=instance.id,
            node_id=node["id"],
            node_name=node.get("name"),
            form_version_id=binding.form_version_id if binding else None,
            role_id=binding.role_id if binding else None,
            assignee_id=binding.assignee_id if binding else None,
            status="pending",
            payload={"binding": dict(binding.config or {}) if binding and binding.config else {}},
        )
        self.db.add(task)
        self.db.flush()
        self._event(instance, "task_created", node_id=node["id"], message=f"وظیفه «{node.get('name')}» ایجاد شد", actor_id=actor_id)
        if binding and binding.assignee_id:
            self._notify(binding.assignee_id, "وظیفه جدید", f"وظیفه «{node.get('name') or node['id']}» برای شما ایجاد شد", link=f"/tasks")
        return task

    # ---------- تکمیل وظیفه ----------
    def complete_task(self, task: ProcessTask, data: dict | None, actor_id: str | None):
        """تکمیل وظیفه — با جلوگیری از انتقال تکراری (AC-04) و ثبت در تراکنش"""
        if task.status != "pending":
            raise ValueError("این وظیفه قبلاً تکمیل یا لغو شده است؛ تکمیل تکراری مجاز نیست")
        if task.instance.status != "running":
            raise ValueError("نمونه فرایند در وضعیت قابل پیشروی نیست")

        task.status = "completed"
        task.completed_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        task.completed_by = actor_id
        merged = dict(task.instance.variables or {})
        for k, v in (data or {}).items():
            merged[k] = v
        task.instance.variables = merged
        task.payload = {**(task.payload or {}), "data": data or {}}

        self._event(task.instance, "task_completed", node_id=task.node_id,
                    message=f"وظیفه «{task.node_name or task.node_id}» تکمیل شد", actor_id=actor_id)

        version = self.db.get(ProcessVersion, task.instance.process_version_id)
        parsed, bindings = self._load(version)
        outgoing = [f for f in parsed["flows"].values() if f["sourceRef"] == task.node_id]
        if not outgoing:
            raise ValueError("وظیفه به مسیر خروجی متصل نیست")
        nxt = outgoing[0]["targetRef"]
        self._advance(version, task.instance, parsed, bindings, nxt, actor_id=actor_id)
