"""تست‌های قراردادها (AC-14، AC-15) و ممیزی"""


def test_required_variable_blocks_generation(client, contract_headers):
    """AC-14 — متغیر الزامی خالی، مانع تولید نهایی قرارداد شود"""
    templates = client.get("/api/v1/contract-templates", headers=contract_headers).json()["items"]
    tpl = templates[0]
    ver_id = tpl["current_version_id"]
    r = client.post("/api/v1/contracts", headers=contract_headers, json={
        "template_version_id": ver_id,
        "data": {"party_a.full_name": "شرکت نمونه"},
        # بقیه متغیرهای الزامی خالی
    })
    assert r.status_code == 422
    missing = r.json()["details"]["missing"]
    assert "party_b.full_name" in missing


def test_generate_contract_freezes_content(client, contract_headers):
    """AC-15 — تغییر الگو، قرارداد تولیدشده قبلی را تغییر ندهد"""
    templates = client.get("/api/v1/contract-templates", headers=contract_headers).json()["items"]
    tpl = templates[0]
    ver_id = tpl["current_version_id"]
    data = {
        "party_a.full_name": "شرکت فرایارا",
        "party_b.full_name": "آقای تست پیمانکار",
        "contract.number": "1404-001",
        "contract.date": "1404/07/01",
        "contract.amount": "500000000",
        "contract.duration": "شش ماه",
    }
    r = client.post("/api/v1/contracts", headers=contract_headers, json={
        "template_version_id": ver_id, "data": data,
    })
    assert r.status_code == 200, r.text
    contract = r.json()
    assert contract["file_hash"]

    detail = client.get(f"/api/v1/contracts/{contract['id']}", headers=contract_headers).json()
    assert "شرکت فرایارا" in detail["body_html"]
    assert "{{" not in detail["body_html"]

    # نسخه جدید الگو با تغییر متن
    r2 = client.post(f"/api/v1/contract-templates/{tpl['id']}/versions", headers=contract_headers, json={})
    new_ver = r2.json()
    client.put(f"/api/v1/contract-template-versions/{new_ver['id']}/body", headers=contract_headers, json={
        "body_html": "<h2>متن کاملاً جدید</h2>",
    })
    # قرارداد قبلی تغییری نکرده باشد
    detail2 = client.get(f"/api/v1/contracts/{contract['id']}", headers=contract_headers).json()
    assert "شرکت فرایارا" in detail2["body_html"]
    assert "متن کاملاً جدید" not in detail2["body_html"]
    assert detail2["file_hash"] == contract["file_hash"]


def test_contract_download(client, contract_headers):
    contracts = client.get("/api/v1/contracts", headers=contract_headers).json()["items"]
    r = client.get(f"/api/v1/contracts/{contracts[0]['id']}/download", headers=contract_headers)
    assert r.status_code == 200
    assert "فرایارا" in r.text or "قرارداد" in r.text


def test_audit_logs_recorded(client, admin_headers):
    r = client.get("/api/v1/audit-logs", headers=admin_headers)
    assert r.status_code == 200
    actions = {item["action"] for item in r.json()["items"]}
    assert "login" in actions or "create" in actions


def test_auditor_can_view_audit_but_not_manage_users(client, auditor_headers):
    assert client.get("/api/v1/audit-logs", headers=auditor_headers).status_code == 200
    assert client.get("/api/v1/users", headers=auditor_headers).status_code == 403


def test_dashboard_overview(client, admin_headers):
    r = client.get("/api/v1/dashboards/overview", headers=admin_headers)
    assert r.status_code == 200
    counts = r.json()["counts"]
    for key in ("processes", "forms", "fields_active", "submissions", "contracts", "open_tasks"):
        assert key in counts


def test_backup_download(client, admin_headers):
    r = client.post("/api/v1/admin/backup", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.content) > 1000
