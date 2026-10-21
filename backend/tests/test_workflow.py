"""تست‌های موتور اجرای فرایند (AC-01 تا AC-04)"""

SAMPLE_BPMN = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" id="Defs1" targetNamespace="http://x">
  <bpmn:process id="P1" isExecutable="true">
    <bpmn:startEvent id="S1" name="شروع"><bpmn:outgoing>F1</bpmn:outgoing></bpmn:startEvent>
    <bpmn:userTask id="T1" name="بررسی"><bpmn:incoming>F1</bpmn:incoming><bpmn:outgoing>F2</bpmn:outgoing></bpmn:userTask>
    <bpmn:exclusiveGateway id="G1" name="تصمیم" />
    <bpmn:userTask id="T2" name="تأیید"><bpmn:incoming>F3</bpmn:incoming><bpmn:outgoing>F5</bpmn:outgoing></bpmn:userTask>
    <bpmn:userTask id="T3" name="رد"><bpmn:incoming>F4</bpmn:incoming><bpmn:outgoing>F6</bpmn:outgoing></bpmn:userTask>
    <bpmn:endEvent id="E1" /><bpmn:endEvent id="E2" />
    <bpmn:sequenceFlow id="F1" sourceRef="S1" targetRef="T1" />
    <bpmn:sequenceFlow id="F2" sourceRef="T1" targetRef="G1" />
    <bpmn:sequenceFlow id="F3" sourceRef="G1" targetRef="T2">
      <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">${result == "yes"}</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    <bpmn:sequenceFlow id="F4" sourceRef="G1" targetRef="T3">
      <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">${result == "no"}</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    <bpmn:sequenceFlow id="F5" sourceRef="T2" targetRef="E1" />
    <bpmn:sequenceFlow id="F6" sourceRef="T3" targetRef="E2" />
  </bpmn:process>
</bpmn:definitions>
"""

UNSAFE_BPMN = SAMPLE_BPMN.replace(
    '<bpmn:userTask id="T3" name="رد">',
    '<bpmn:parallelGateway id="P_GW" /><bpmn:userTask id="T3" name="رد">'
)


def test_saved_diagram_roundtrip(client, pdesigner_headers):
    """AC-01 — فرایند طراحی‌شده پس از ذخیره و بازگشایی، ساختار خود را حفظ کند"""
    r = client.post("/api/v1/processes", headers=pdesigner_headers, json={"title": "فرایند تست ذخیره"})
    proc = r.json()
    ver_id = proc["current_version_id"]
    r2 = client.put(f"/api/v1/process-versions/{ver_id}/diagram", headers=pdesigner_headers,
                    json={"bpmn_xml": SAMPLE_BPMN})
    assert r2.status_code == 200, r2.text
    r3 = client.get(f"/api/v1/process-versions/{ver_id}", headers=pdesigner_headers)
    assert r3.json()["bpmn_xml"] == SAMPLE_BPMN
    assert "T1" in r3.json()["bpmn_xml"]


def test_validate_detects_unsupported(client, admin_headers, pdesigner_headers):
    """AC-02 — خروجی BPMN معتبر باشد و عناصر خارج از دامنه اجرا مشخص شوند"""
    r = client.post("/api/v1/processes", headers=pdesigner_headers, json={"title": "فرایند غیرقابل اجرا"})
    ver_id = r.json()["current_version_id"]
    client.put(f"/api/v1/process-versions/{ver_id}/diagram", headers=pdesigner_headers,
               json={"bpmn_xml": UNSAFE_BPMN})
    r2 = client.post(f"/api/v1/process-versions/{ver_id}/validate", headers=pdesigner_headers)
    data = r2.json()
    types = [u["type"] for u in data["unsupported"]]
    assert "parallelGateway" in types
    # انتشار اجرایی باید با پیام روشن ناموفق باشد (تأیید انتشار مجوز اختصاصی دارد — بخش ۳.۲)
    r3 = client.post(f"/api/v1/process-versions/{ver_id}/publish", headers=pdesigner_headers)
    assert r3.status_code == 403  # طراح فرایند مجوز انتشار ندارد
    r4 = client.post(f"/api/v1/process-versions/{ver_id}/publish", headers=admin_headers)
    assert r4.status_code == 422
    detail = r4.json()["details"] if "details" in r4.json() else r4.json()
    assert "parallelGateway" in str(detail) or "unsupported" in str(detail)


def test_start_only_on_published(client, pdesigner_headers):
    """AC-03 — شروع فرایند فقط روی نسخه منتشرشده ممکن باشد"""
    r = client.post("/api/v1/processes", headers=pdesigner_headers, json={"title": "فرایند پیش‌نویس"})
    ver_id = r.json()["current_version_id"]
    client.put(f"/api/v1/process-versions/{ver_id}/diagram", headers=pdesigner_headers,
               json={"bpmn_xml": SAMPLE_BPMN})
    r2 = client.post(f"/api/v1/process-versions/{ver_id}/instances", headers=pdesigner_headers, json={})
    assert r2.status_code == 422


def test_full_execution_and_idempotent_task(client, admin_headers, operator_headers):
    """اجرای کامل مسیر + جلوگیری از دو انتقال با تکمیل تکراری (AC-04)"""
    procs = client.get("/api/v1/processes", headers=admin_headers).json()["items"]
    proc = next(p for p in procs if "درخواست خدمات" in p["title"])
    ver_id = proc["current_version_id"]

    # شروع نمونه روی نسخه منتشرشده seed
    r = client.post(f"/api/v1/process-versions/{ver_id}/instances", headers=operator_headers,
                    json={"variables": {}, "title": "درخواست تست فرایند"})
    assert r.status_code == 200, r.text
    inst = r.json()
    assert inst["trace_code"].startswith("INS-")
    assert inst["status"] == "running"

    # وظیفه اول (بررسی درخواست) برای نقش operator
    tasks = client.get("/api/v1/tasks/my", headers=operator_headers).json()
    task = next(t for t in tasks if t["instance_id"] == inst["id"] and t["status"] == "pending")
    assert task["node_name"] == "بررسی درخواست"

    # تکمیل وظیفه با داده فرم (متغیر مسیر: review_result)
    r2 = client.post(f"/api/v1/tasks/{task['id']}/complete", headers=operator_headers,
                     json={"data": {"full_name": "تست", "mobile": "09121234567", "review_result": "yes"}})
    assert r2.status_code == 200, r2.text

    # AC-04 — تکمیل تکراری نباید دو انتقال ایجاد کند
    r3 = client.post(f"/api/v1/tasks/{task['id']}/complete", headers=operator_headers, json={"data": {}})
    assert r3.status_code == 409

    # وظیفه دوم باید روی مسیر تأیید ایجاد شده باشد (برای نقش org_admin)
    orgadmin = client.post("/api/v1/auth/login", json={"username": "orgadmin", "password": "Org@1234"}).json()
    org_headers = {"Authorization": f"Bearer {orgadmin['access_token']}"}
    tasks2 = client.get("/api/v1/tasks/my", headers=org_headers).json()
    task2 = next(t for t in tasks2 if t["instance_id"] == inst["id"] and t["status"] == "pending")
    assert task2["node_name"] == "تأیید نهایی"

    # تکمیل وظیفه دوم → پایان فرایند
    r4 = client.post(f"/api/v1/tasks/{task2['id']}/complete", headers=org_headers, json={"data": {"final_note": "ok"}})
    assert r4.status_code == 200
    detail = client.get(f"/api/v1/process-instances/{inst['id']}", headers=admin_headers).json()
    assert detail["status"] == "completed"
    # تاریخچه اجرا ثبت شده باشد
    event_types = [e["type"] for e in detail["events"]]
    assert "started" in event_types and "flow_taken" in event_types and "completed" in event_types


def test_task_assignment_protection(client, auditor_headers, operator_headers):
    """وظیفه تخصیص‌یافته به نقش دیگر قابل تکمیل توسط کاربر بی‌ربط نیست"""
    procs = client.get("/api/v1/processes", headers=operator_headers).json()["items"]
    proc = next(p for p in procs if "درخواست خدمات" in p["title"])
    ver_id = proc["current_version_id"]
    r = client.post(f"/api/v1/process-versions/{ver_id}/instances", headers=operator_headers, json={})
    inst = r.json()
    # auditor نقش operator را ندارد → نباید وظیفه ببیند یا تکمیل کند
    my_tasks = client.get("/api/v1/tasks/my", headers=auditor_headers).json()
    assert all(t["instance_id"] != inst["id"] for t in my_tasks)
    tasks = client.get("/api/v1/tasks/my", headers=operator_headers).json()
    task = next(t for t in tasks if t["instance_id"] == inst["id"])
    r2 = client.post(f"/api/v1/tasks/{task['id']}/complete", headers=auditor_headers, json={"data": {}})
    assert r2.status_code == 403
