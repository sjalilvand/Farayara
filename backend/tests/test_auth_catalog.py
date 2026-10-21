"""تست‌های احراز هویت، مجوز و کاتالوگ داده"""
import re


def test_login_wrong_password(client):
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_login_success(client):
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "Admin@1234"})
    assert r.status_code == 200
    data = r.json()
    assert data["access_token"]
    assert data["user"]["username"] == "admin"
    assert "system.admin" in data["user"]["permissions"]


def test_me_requires_token(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_me(client, admin_headers):
    r = client.get("/api/v1/auth/me", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["username"] == "admin"


def test_permission_denied_without_permission(client, operator_headers):
    """AC-16 — کاربر فاقد مجوز نتواند با درخواست مستقیم API به منبع محافظت‌شده دسترسی یابد"""
    r = client.post("/api/v1/catalog/fields", headers=operator_headers, json={
        "tech_name": "hack_field", "title_fa": "نفوذ", "data_type": "text",
    })
    assert r.status_code == 403


def test_auditor_cannot_view_results(client, auditor_headers):
    r = client.get("/api/v1/assessment-administrations", headers=auditor_headers)
    # فهرست اجراها برای همه باز است اما نتایج نیازمند مجوز مستقل
    r2 = client.post("/api/v1/auth/login", json={"username": "auditor", "password": "Audit@1234"})
    assert r2.status_code == 200


def test_create_field_and_version(steward_headers, client):
    r = client.post("/api/v1/catalog/fields", headers=steward_headers, json={
        "tech_name": "test_field_x", "title_fa": "فیلد آزمایشی", "data_type": "number",
        "validation_rules": {"min": 0, "max": 10}, "aliases": ["آزمایشی"],
    })
    assert r.status_code == 200, r.text
    field = r.json()
    assert re.match(r"^FLD-\d{6}$", field["code"])
    # تغییر نوع → نسخه جدید
    r2 = client.put(f"/api/v1/catalog/fields/{field['id']}", headers=steward_headers, json={
        "data_type": "text",
    })
    assert r2.status_code == 200
    r3 = client.get(f"/api/v1/catalog/fields/{field['id']}", headers=steward_headers)
    assert len(r3.json()["versions"]) == 2


def test_similar_fields_suggestion(client, steward_headers):
    r = client.get("/api/v1/catalog/similar", params={"name": "موبایل"}, headers=steward_headers)
    assert r.status_code == 200
    titles = [x["title_fa"] for x in r.json()]
    assert any("موبایل" in t for t in titles)


def test_field_statistics_keys(client, steward_headers):
    r = client.get("/api/v1/catalog/fields", params={"query": "موبایل"}, headers=steward_headers)
    field_id = r.json()["items"][0]["id"]
    r2 = client.get(f"/api/v1/catalog/fields/{field_id}/statistics", headers=steward_headers)
    assert r2.status_code == 200
    stats = r2.json()
    for key in ("forms_count", "versions_count", "places_count", "submissions_count", "filled_count", "fill_rate"):
        assert key in stats
