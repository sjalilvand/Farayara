"""داده اولیه (Seed) — سازمان، نقش‌ها، مجوزها، کاربران نمونه، فرم، فرایند، آزمون و الگوی قرارداد

اجرا:  python -m app.seed
"""
import json

from .database import Base, SessionLocal, engine
from .models import (
    Assessment, AssessmentItem, AssessmentValidationCase, AssessmentVersion,
    ContractTemplate, ContractTemplateVersion, ContractVariable,
    FieldDefinition, FieldDefinitionVersion, Form, FormVersion, FormFieldUsage,
    Organization, Permission, Process, ProcessNodeBinding, ProcessVersion, Role,
    RolePermission, SystemSetting, User, UserRole,
)
from .security import hash_password

# ================= مجوزها (بخش ۳ سند) =================
PERMISSIONS = [
    ("system.admin", "مدیریت کل سامانه", "سیستم"),
    ("system.settings", "تنظیمات سامانه", "سیستم"),
    ("user.manage", "مدیریت کاربران", "دسترسی"),
    ("role.manage", "مدیریت نقش‌ها و مجوزها", "دسترسی"),
    ("audit.view", "مشاهده سوابق تغییرات", "دسترسی"),
    ("dashboard.view", "مشاهده داشبوردها", "گزارش"),
    ("export.data", "خروجی گرفتن داده‌ها", "گزارش"),
    ("file.download", "دریافت فایل‌ها و اسناد", "گزارش"),
    ("process.create", "ایجاد و ویرایش فرایند", "فرایند"),
    ("process.publish", "انتشار نسخه فرایند", "فرایند"),
    ("process.start", "شروع اجرای فرایند", "فرایند"),
    ("process.admin", "لغو و مدیریت اجرای فرایند", "فرایند"),
    ("form.create", "ایجاد و ویرایش فرم", "فرم"),
    ("form.publish", "انتشار نسخه فرم", "فرم"),
    ("form.submit", "ثبت پاسخ فرم", "فرم"),
    ("form.submissions.view", "مشاهده پاسخ‌های ثبت‌شده", "فرم"),
    ("form.submissions.revise", "اصلاح پاسخ ثبت‌شده", "فرم"),
    ("catalog.manage", "مدیریت کاتالوگ داده", "کاتالوگ"),
    ("catalog.approve", "تأیید و ادغام فیلدها (متولی داده)", "کاتالوگ"),
    ("assessment.manage", "مدیریت بانک آزمون‌ها", "آزمون"),
    ("assessment.approve", "تأیید علمی/حقوقی آزمون", "آزمون"),
    ("assessment.run", "اجرای آزمون و ثبت پاسخ", "آزمون"),
    ("assessment.result.view", "مشاهده نتایج آزمون (مجوز مستقل)", "آزمون"),
    ("contract.manage", "طراحی الگوی قرارداد", "قرارداد"),
    ("contract.approve", "تأیید حقوقی الگو و انتشار", "قرارداد"),
    ("contract.generate", "تولید قرارداد از الگو", "قرارداد"),
]

# ================= نقش‌ها (بخش ۳.۱ سند) =================
ROLES = [
    ("sys_admin", "مدیر سامانه", ["system.admin", "system.settings", "user.manage", "role.manage", "audit.view", "dashboard.view", "export.data", "file.download"]),
    ("org_admin", "مدیر سازمان", ["dashboard.view", "user.manage", "export.data", "file.download", "audit.view", "process.admin"]),
    ("process_designer", "طراح فرایند", ["dashboard.view", "process.create", "process.start"]),
    ("form_designer", "طراح فرم", ["dashboard.view", "form.create", "form.publish"]),
    ("data_steward", "متولی داده", ["dashboard.view", "catalog.manage", "catalog.approve", "form.create"]),
    ("assessment_specialist", "متخصص آزمون", ["dashboard.view", "assessment.manage", "assessment.approve", "assessment.run", "assessment.result.view"]),
    ("contract_expert", "کارشناس قرارداد", ["dashboard.view", "contract.manage", "contract.approve", "contract.generate", "file.download"]),
    ("operator", "کاربر اجرایی", ["dashboard.view", "form.submit", "process.start"]),
    ("respondent", "پاسخ‌دهنده آزمون", ["assessment.run"]),
    ("report_manager", "مدیر گزارش", ["dashboard.view", "export.data", "form.submissions.view", "assessment.result.view", "file.download"]),
    ("auditor", "ناظر یا حسابرس", ["audit.view", "dashboard.view"]),
]

# ================= کاربران نمونه =================
USERS = [
    ("admin", "Admin@1234", "مدیر سامانه فرایارا", ["sys_admin"], "فناوری اطلاعات"),
    ("orgadmin", "Org@1234", "مریم محمدی", ["org_admin"], "مدیریت"),
    ("pdesigner", "Proc@1234", "علی رضایی", ["process_designer"], "بهبود فرایندها"),
    ("fdesigner", "Form@1234", "زهرا کریمی", ["form_designer"], "تحلیل و طراحی"),
    ("steward", "Data@1234", "حسین موسوی", ["data_steward"], "داده و اطلاعات"),
    ("assessor", "Assess@1234", "دکتر سارا احمدی", ["assessment_specialist"], "مشاوره"),
    ("contractx", "Contract@1234", "مهدی نوری", ["contract_expert"], "حقوق و قراردادها"),
    ("operator", "Oper@1234", "فاطمه حسینی", ["operator", "respondent"], "پشتیبانی"),
    ("auditor", "Audit@1234", "ناصر قاسمی", ["auditor"], "حسابرسی داخلی"),
]

EMPTY_BPMN = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" id="Defs_farayara" targetNamespace="http://farayara.local/bpmn">
  <bpmn:process id="Process_new" isExecutable="true">
    <bpmn:startEvent id="Start_1" name="شروع">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:userTask id="Task_1" name="وظیفه اول">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:endEvent id="End_1" name="پایان">
      <bpmn:incoming>Flow_2</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="Start_1" targetRef="Task_1" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_1" targetRef="End_1" />
  </bpmn:process>
  <bpmndi:BPMNDiagram id="Diagram_1">
    <bpmndi:BPMNPlane id="Plane_1" bpmnElement="Process_new">
      <bpmndi:BPMNShape id="Start_1_di" bpmnElement="Start_1">
        <dc:Bounds x="182" y="162" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Task_1_di" bpmnElement="Task_1">
        <dc:Bounds x="270" y="140" width="120" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="End_1_di" bpmnElement="End_1">
        <dc:Bounds x="460" y="162" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="Flow_1_di" bpmnElement="Flow_1">
        <di:waypoint x="218" y="180" />
        <di:waypoint x="270" y="180" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_2_di" bpmnElement="Flow_2">
        <di:waypoint x="390" y="180" />
        <di:waypoint x="460" y="180" />
      </bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>
"""

SERVICE_REQUEST_BPMN = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" id="Defs_sr" targetNamespace="http://farayara.local/bpmn">
  <bpmn:process id="Process_service_request" isExecutable="true">
    <bpmn:startEvent id="Start_1" name="ثبت درخواست">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:userTask id="Task_review" name="بررسی درخواست">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:exclusiveGateway id="GW_1" name="نتیجه بررسی؟" />
    <bpmn:userTask id="Task_approve" name="تأیید نهایی">
      <bpmn:incoming>Flow_3</bpmn:incoming>
      <bpmn:outgoing>Flow_5</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:userTask id="Task_reject" name="اعلام رد درخواست">
      <bpmn:incoming>Flow_4</bpmn:incoming>
      <bpmn:outgoing>Flow_6</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:endEvent id="End_ok" name="تأیید شد" />
    <bpmn:endEvent id="End_rej" name="رد شد" />
    <bpmn:sequenceFlow id="Flow_1" sourceRef="Start_1" targetRef="Task_review" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_review" targetRef="GW_1" />
    <bpmn:sequenceFlow id="Flow_3" name="موافق" sourceRef="GW_1" targetRef="Task_approve">
      <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">${review_result == "yes"}</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    <bpmn:sequenceFlow id="Flow_4" name="مخالف" sourceRef="GW_1" targetRef="Task_reject">
      <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">${review_result == "no"}</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    <bpmn:sequenceFlow id="Flow_5" sourceRef="Task_approve" targetRef="End_ok" />
    <bpmn:sequenceFlow id="Flow_6" sourceRef="Task_reject" targetRef="End_rej" />
  </bpmn:process>
  <bpmndi:BPMNDiagram id="Diagram_sr">
    <bpmndi:BPMNPlane id="Plane_sr" bpmnElement="Process_service_request">
      <bpmndi:BPMNShape id="Start_1_di" bpmnElement="Start_1">
        <dc:Bounds x="152" y="182" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Task_review_di" bpmnElement="Task_review">
        <dc:Bounds x="240" y="160" width="120" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="GW_1_di" bpmnElement="GW_1" isMarkerVisible="true">
        <dc:Bounds x="415" y="175" width="50" height="50" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Task_approve_di" bpmnElement="Task_approve">
        <dc:Bounds x="530" y="90" width="120" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Task_reject_di" bpmnElement="Task_reject">
        <dc:Bounds x="530" y="240" width="120" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="End_ok_di" bpmnElement="End_ok">
        <dc:Bounds x="712" y="112" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="End_rej_di" bpmnElement="End_rej">
        <dc:Bounds x="712" y="262" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="Flow_1_di" bpmnElement="Flow_1">
        <di:waypoint x="188" y="200" /><di:waypoint x="240" y="200" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_2_di" bpmnElement="Flow_2">
        <di:waypoint x="360" y="200" /><di:waypoint x="415" y="200" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_3_di" bpmnElement="Flow_3">
        <di:waypoint x="440" y="175" /><di:waypoint x="440" y="130" /><di:waypoint x="530" y="130" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_4_di" bpmnElement="Flow_4">
        <di:waypoint x="440" y="225" /><di:waypoint x="440" y="280" /><di:waypoint x="530" y="280" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_5_di" bpmnElement="Flow_5">
        <di:waypoint x="650" y="130" /><di:waypoint x="712" y="130" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_6_di" bpmnElement="Flow_6">
        <di:waypoint x="650" y="280" /><di:waypoint x="712" y="280" />
      </bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>
"""

CONTRACT_BODY = """<h2>قرارداد ارائه خدمات مشاوره</h2>
<p>این قرارداد به شماره <b>{{contract.number}}</b> و در تاریخ <b>{{contract.date}}</b> میان <b>{{party_a.full_name}}</b> به‌عنوان طرف اول (کارفرما) و <b>{{party_b.full_name}}</b> به‌عنوان طرف دوم (پیمانکار) با مشخصات زیر منعقد می‌گردد.</p>
<h3>ماده ۱ — موضوع قرارداد</h3>
<p>موضوع این قرارداد ارائه خدمات مشاوره تخصصی در حوزه تعیین‌شده به مدت <b>{{contract.duration}}</b> است.</p>
<h3>ماده ۲ — مبلغ قرارداد</h3>
<p>مبلغ کل این قرارداد معادل <b>{{contract.amount}}</b> ریال است که به‌صورت توافقی پرداخت می‌شود.</p>
<h3>ماده ۳ — تعهدات طرفین</h3>
<ul><li>طرف اول موضوع، اطلاعات و دسترسی‌های لازم را فراهم می‌کند.</li><li>طرف دوم خدمات را با کیفیت متعارف حرفه‌ای و در مواعد مقرر ارائه می‌کند.</li></ul>
<h3>ماده ۴ — حل اختلاف</h3>
<p>هرگونه اختلاف ناشی از تفسیر یا اجرای این قرارداد ابتدا از طریق مذاکره و در غیر این‌صورت از طریق مراجع قانونی حل و فصل می‌شود.</p>
<p>این قرارداد در ۴ ماده و با امضای طرفین تنظیم و ملاک عمل خواهد بود.</p>
"""


def seed():
    print("در حال ایجاد داده اولیه فرایارا ...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Organization).first():
            print("داده اولیه قبلاً بارگذاری شده است (seed عمداً تکرار نمی‌شود).")
            return

        org = Organization(code="ORG-001", name="سازمان نمونه فرایارا")
        db.add(org)
        db.flush()

        # مجوزها
        perms = {}
        for code, title, group in PERMISSIONS:
            p = Permission(code=code, title=title, group=group)
            db.add(p)
            perms[code] = p
        db.flush()

        # نقش‌ها
        roles = {}
        for code, name, perm_codes in ROLES:
            r = Role(code=code, name=name, is_system=True)
            db.add(r)
            db.flush()
            for pc in perm_codes:
                db.add(RolePermission(role_id=r.id, permission_id=perms[pc].id))
            roles[code] = r
        db.flush()

        # کاربران
        users = {}
        for username, password, full_name, role_codes, unit in USERS:
            u = User(username=username, full_name=full_name, unit=unit,
                     hashed_password=hash_password(password),
                     email=f"{username}@farayara.local", org_id=org.id)
            db.add(u)
            db.flush()
            for rc in role_codes:
                db.add(UserRole(user_id=u.id, role_id=roles[rc].id))
            users[username] = u
        db.flush()

        # ---------- کاتالوگ فیلدها ----------
        FIELDS = [
            ("full_name", "نام و نام خانوادگی", "text", "اطلاعات هویتی", True, None, {"required": False}, ["نام کامل", "نام"], "identity"),
            ("national_code", "کد ملی", "national_code", "اطلاعات هویتی", True, None, {"pattern": r"^[0-9]{10}$"}, ["کدپستی شخص", "شماره ملی"], "identity"),
            ("mobile_number", "شماره موبایل", "phone", "اطلاعات تماس", True, None, {"pattern": r"^09[0-9]{9}$"}, ["تلفن همراه", "موبایل"], "identity"),
            ("email_address", "نشانی ایمیل", "email", "اطلاعات تماس", False, None, {"pattern": r"^[^@\s]+@[^@\s]+\.[^@\s]+$"}, ["ایمیل"], None),
            ("request_amount", "مبلغ درخواست (ریال)", "money", "مالی", False, "ریال", {"min": 0}, ["مبلغ"], None),
            ("request_date", "تاریخ درخواست", "date", "عمومی", False, None, {}, [], None),
            ("has_manager_approval", "تأیید مدیر", "yes_no", "عمومی", False, None, {}, ["موافقت مدیر"], None),
            ("request_description", "شرح درخواست", "textarea", "عمومی", False, None, {}, ["توضیحات"], None),
            ("contract_amount", "مبلغ قرارداد (ریال)", "money", "مالی", False, "ریال", {"min": 0}, ["مبلغ کل"], None),
            ("contract_duration", "مدت قرارداد", "text", "قراردادها", False, None, {}, ["مدت"], None),
            ("work_satisfaction", "رضایت شغلی (نمره)", "number", "آزمون‌ها", False, None, {"min": 0, "max": 100}, [], "health"),
        ]
        from .utils import next_code
        fields = {}
        for tech, title, dtype, cat, is_id, unit, rules, aliases, sens in FIELDS:
            f = FieldDefinition(code=next_code(db, "field"), tech_name=tech, title_fa=title, category=cat,
                                is_identity=(sens == "identity"), is_health=(sens == "health"),
                                sensitivity=sens or "normal", aliases=aliases, unit=unit,
                                created_by=users["steward"].id)
            db.add(f)
            db.flush()
            ver = FieldDefinitionVersion(field_id=f.id, version_number=1, data_type=dtype,
                                         validation_rules=rules, created_by=users["steward"].id)
            db.add(ver)
            db.flush()
            f.current_version_id = ver.id
            fields[tech] = f
        db.flush()

        # ---------- فرم نمونه ----------
        form = Form(code=next_code(db, "form"), title="فرم درخواست خدمات",
                    description="فرم ثبت درخواست خدمات کارکنان",
                    purpose="ثبت ساختارمند درخواست‌ها و پیگیری آن‌ها در فرایند",
                    category="خدمات", audience="کارکنان سازمان", created_by=users["fdesigner"].id)
        db.add(form)
        db.flush()

        def fld(tech, label, required=False, override=None):
            f = fields[tech]
            item = {"key": tech, "field_id": f.id, "type": None,
                    "label": label or f.title_fa, "required": required, "help": ""}
            return item, f

        form_fields = []
        usages = [
            ("full_name", "نام و نام خانوادگی درخواست‌کننده", True),
            ("mobile_number", "شماره تماس", True),
            ("email_address", "ایمیل (اختیاری)", False),
            ("request_date", "تاریخ درخواست", True),
            ("request_amount", "مبلغ تقریبی درخواست (ریال)", False),
            ("request_description", "شرح کامل درخواست", True),
        ]
        schema_fields = []
        usage_rows = []
        for i, (tech, label, req) in enumerate(usages):
            item, f = fld(tech, label, req)
            ver0 = db.get(FieldDefinitionVersion, f.current_version_id)
            item["type"] = ver0.data_type
            item["validations"] = ver0.validation_rules or {}
            schema_fields.append(item)
            usage_rows.append((f.id, tech, label, req, i))
        fver = FormVersion(form_id=form.id, version_number=1, status="draft",
                           schema_json={"fields": schema_fields, "layout": {"columns": 1}},
                           ui_schema_json={}, rules_json={},
                           created_by=users["fdesigner"].id)
        db.add(fver)
        db.flush()
        form.current_version_id = fver.id
        for field_id, tech, label, req, pos in usage_rows:
            db.add(FormFieldUsage(form_version_id=fver.id, field_id=field_id, field_key=tech,
                                  label_override=label, required=req, position=pos))
        # انتشار فرم
        from datetime import datetime, timezone
        fver.status = "published"
        fver.published_at = datetime.now(timezone.utc)
        fver.published_by = users["fdesigner"].id

        # ---------- فرایند نمونه ----------
        proc = Process(code=next_code(db, "process"), title="فرایند بررسی و تأیید درخواست خدمات",
                       description="دریافت درخواست، بررسی توسط کاربر اجرایی و تصمیم‌گیری تأیید/رد",
                       purpose="استانداردسازی بررسی درخواست‌های خدمات",
                       category="خدمات", unit="پشتیبانی", owner_id=users["pdesigner"].id,
                       created_by=users["pdesigner"].id)
        db.add(proc)
        db.flush()
        pver = ProcessVersion(process_id=proc.id, version_number=1, status="draft",
                              bpmn_xml=SERVICE_REQUEST_BPMN, exec_config={},
                              created_by=users["pdesigner"].id)
        db.add(pver)
        db.flush()
        proc.current_version_id = pver.id
        # اتصال گره‌ها
        db.add(ProcessNodeBinding(process_version_id=pver.id, node_id="Task_review", node_type="userTask",
                                  node_name="بررسی درخواست", form_version_id=fver.id,
                                  role_id=roles["operator"].id, config={}))
        db.add(ProcessNodeBinding(process_version_id=pver.id, node_id="Task_approve", node_type="userTask",
                                  node_name="تأیید نهایی", role_id=roles["org_admin"].id, config={}))
        db.add(ProcessNodeBinding(process_version_id=pver.id, node_id="Task_reject", node_type="userTask",
                                  node_name="اعلام رد درخواست", role_id=roles["operator"].id, config={}))
        # انتشار
        pver.status = "published"
        pver.published_at = datetime.now(timezone.utc)
        pver.published_by = users["pdesigner"].id

        # ---------- آزمون نمونه (محتوای ساخته‌شده داخلی — بدون محدودیت حقوقی) ----------
        asm = Assessment(code=next_code(db, "assessment"),
                         title_fa="پرسش‌نامه کوتاه رضایت شغلی (نمونه داخلی)",
                         title_original=None, abbreviation="JSS-Sample",
                         domain="سنجش نگرش شغلی", author="تیم فرایارا",
                         publisher="سازمان نمونه (محتوای داخلی)",
                         rights_holder="سازمان نمونه",
                         language="فارسی", target_group="کارکنان شاغل",
                         item_count=6, duration_minutes=5, answer_mode="self",
                         scoring_method="جمع نمرات گزینه‌ها با یک گویه معکوس",
                         scientific_references="محتوای آموزشی نمونه ساخته‌شده برای آزمایش سامانه",
                         norms_notes="هنجار نمونه — برای استقرار واقعی نیاز به هنجارسازی دارد",
                         limitations="ابزار نمایشی است و جایگزین ابزارهای استاندارد و معتبر نیست",
                         license_terms="محتوای ساخته‌شده داخلی؛ بدون محدودیت استفاده",
                         license_status="owned", approved_scientific=True,
                         approved_legal=True, approved_scientific_by="دکتر سارا احمدی",
                         approved_legal_by="مهدی نوری", category="آزمون‌های نمونه",
                         created_by=users["assessor"].id)
        db.add(asm)
        db.flush()
        options = [{"value": "1", "label": "هرگز", "score": 1}, {"value": "2", "label": "به‌ندرت", "score": 2},
                   {"value": "3", "label": "گاهی", "score": 3}, {"value": "4", "label": "بیشتر وقت‌ها", "score": 4},
                   {"value": "5", "label": "همیشه", "score": 5}]
        ITEMS = [
            ("q1", "به‌طور کلی از شغل خود راضی هستم.", False),
            ("q2", "کار خود را برای دیگران مفید می‌دانم.", False),
            ("q3", "از شرایط محیط کارم ناراضی هستم.", True),
            ("q4", "روابط من با همکارانم خوب است.", False),
            ("q5", "به رشد و پیشرفت در این شغل امیدوارم.", False),
            ("q6", "در پایان روز کاری احساس خستگی و بی‌انگیزگی شدید دارم.", True),
        ]
        aver = AssessmentVersion(assessment_id=asm.id, version_number=1, status="draft", year="1404",
                                 language="فارسی",
                                 items_config={"option_values": {}, "missing_policy": "skip",
                                               "reverse_items": ["q3", "q6"],
                                               "validity": {"min_answered_ratio": 0.6}},
                                 scoring_rules={"scales": [
                                     {"code": "total", "title": "نمره کل رضایت",
                                      "items": ["q1", "q2", "q3", "q4", "q5", "q6"],
                                      "min": 6, "max": 30,
                                      "interpretations": [
                                          {"min": 6, "max": 13, "label": "رضایت پایین", "description": "نیازمند بررسی و گفت‌وگوی تخصصی"},
                                          {"min": 14, "max": 21, "label": "رضایت متوسط", "description": "وضعیت قابل قبول با زمینه بهبود"},
                                          {"min": 22, "max": 30, "label": "رضایت بالا", "description": "نگرش مثبت به شغل"}]},
                                     {"code": "mean", "title": "میانگین نمره",
                                      "expression": "round(total / 6, 2)", "min": 1, "max": 5}]},
                                 norm_sets=[{"title": "هنجار نمونه", "conditions": {},
                                             "table": {"total": [
                                                 {"raw_min": 6, "raw_max": 13, "converted": "پایین"},
                                                 {"raw_min": 14, "raw_max": 21, "converted": "متوسط"},
                                                 {"raw_min": 22, "raw_max": 30, "converted": "بالا"}]}}],
                                 rules_version_note="نسخه اولیه قواعد", created_by=users["assessor"].id)
        db.add(aver)
        db.flush()
        for i, (code, text, rev) in enumerate(ITEMS):
            db.add(AssessmentItem(version_id=aver.id, order=i, code=code, text=text,
                                  item_type="likert", is_reverse=rev, weight=1.0,
                                  options=options, scale_codes=["total"]))
        db.add(AssessmentValidationCase(version_id=aver.id, title="حالت مرجع ۱ — پاسخ کامل",
                                        input_answers={"q1": "4", "q2": "5", "q3": "1", "q4": "4", "q5": "5", "q6": "1"},
                                        expected={"total": 28}, note="q3 و q6 معکوس؛ 5+1-1=5 برای هر دو؛ 4+5+5+4+5+5=28"))
        db.add(AssessmentValidationCase(version_id=aver.id, title="حالت مرجع ۲ — پاسخ ناقص",
                                        input_answers={"q1": "4", "q2": "4", "q3": "1", "q4": "4", "q5": "4"},
                                        expected={"total": 21}, note="q6 پاسخ داده نشده؛ سیاست skip؛ 4+4+5+4+4=21"))
        asm.current_version_id = aver.id
        aver.status = "published"
        aver.published_at = datetime.now(timezone.utc)

        # ---------- الگوی قرارداد ----------
        tpl = ContractTemplate(code=next_code(db, "contract_template"), title="قرارداد ارائه خدمات مشاوره",
                               contract_type="خدمات مشاوره", unit="حقوق و قراردادها",
                               description="الگوی استاندارد قرارداد خدمات مشاوره",
                               created_by=users["contractx"].id)
        db.add(tpl)
        db.flush()
        tver = ContractTemplateVersion(template_id=tpl.id, version_number=1, status="draft",
                                       body_html=CONTRACT_BODY, created_by=users["contractx"].id)
        db.add(tver)
        db.flush()
        tpl.current_version_id = tver.id
        VARIABLES = [
            ("party_a.full_name", "نام طرف اول (کارفرما)", "text", True),
            ("party_b.full_name", "نام طرف دوم (پیمانکار)", "text", True),
            ("contract.number", "شماره قرارداد", "text", True),
            ("contract.date", "تاریخ قرارداد", "date", True),
            ("contract.amount", "مبلغ قرارداد (ریال)", "money", True),
            ("contract.duration", "مدت قرارداد", "text", True),
        ]
        for key, label, dtype, req in VARIABLES:
            db.add(ContractVariable(template_id=tpl.id, key=key, label=label, data_type=dtype, required=req))
        tver.status = "published"
        tver.published_at = datetime.now(timezone.utc)
        tver.legal_approver = "مهدی نوری"

        # ---------- تنظیمات ----------
        db.add(SystemSetting(key="site_title", value={"value": "فرایارا"}, description="عنوان سامانه"))
        db.add(SystemSetting(key="max_upload_mb", value={"value": 20}, description="حداکثر حجم فایل (مگابایت)"))
        db.add(SystemSetting(key="search_normalize_yk", value={"value": True},
                             description="یکسان‌سازی ی/ي و ک/ك در جست‌وجو"))

        db.commit()
        print("✔ داده اولیه با موفقیت بارگذاری شد.")
        print("  کاربران نمونه: admin / orgadmin / pdesigner / fdesigner / steward / assessor / contractx / operator / auditor")
        print("  رمز همه: طبق مستند README (مثلاً Admin@1234 برای admin)")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
