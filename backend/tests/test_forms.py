"""تست‌های فرم‌ساز، انتشار، ثبت پاسخ و نسخه‌بندی (AC-05، AC-06، AC-07، AC-08، AC-09)"""


def _make_form(client, headers, title="فرم تست"):
    r = client.post("/api/v1/forms", headers=headers, json={"title": title, "category": "تست"})
    assert r.status_code == 200, r.text
    return r.json()


def _get_fields(client, headers, query):
    r = client.get("/api/v1/catalog/fields", params={"query": query}, headers=headers)
    return r.json()["items"][0]


def test_form_lifecycle(client, fdesigner_headers, operator_headers, admin_headers):
    """AC-05 — فرم از طریق فرم‌ساز ساخته، منتشر و بدون کدنویسی تکمیل شود"""
    form = _make_form(client, fdesigner_headers)
    fid = form["id"]
    ver_id = form["current_version_id"]
    f1 = _get_fields(client, fdesigner_headers, "موبایل")
    f2 = _get_fields(client, fdesigner_headers, "نام و نام خانوادگی")

    schema = {
        "fields": [
            {"key": "full_name", "field_id": f2["id"], "type": "text", "label": "نام", "required": True},
            {"key": "mobile", "field_id": f1["id"], "type": "phone", "label": "موبایل", "required": True,
             "validations": {"pattern": r"^09[0-9]{9}$"}},
        ]
    }
    r = client.put(f"/api/v1/form-versions/{ver_id}/schema", headers=fdesigner_headers, json={"schema_json": schema})
    assert r.status_code == 200, r.text
    r = client.post(f"/api/v1/form-versions/{ver_id}/publish", headers=fdesigner_headers)
    assert r.status_code == 200, r.text

    # ثبت پاسخ معتبر (کاربر اجرایی مجوز form.submit دارد)
    r = client.post(f"/api/v1/form-versions/{ver_id}/submissions", headers=operator_headers, json={
        "data": {"full_name": "علی رضایی", "mobile": "09121234567"},
    })
    assert r.status_code == 200, r.text
    sub = r.json()
    assert sub["trace_code"].startswith("TRK-")

    # ثبت پاسخ نامعتبر (full_name الزامی خالی)
    r3 = client.post(f"/api/v1/form-versions/{ver_id}/submissions", headers=operator_headers, json={
        "data": {"mobile": "09121234567"},
    })
    assert r3.status_code == 422  # full_name الزامی

    # AC-06 — ویرایش فرم منتشرشده → نسخه جدید
    r4 = client.post(f"/api/v1/forms/{fid}/versions", headers=fdesigner_headers, json={})
    assert r4.status_code == 200
    new_ver = r4.json()
    assert new_ver["version_number"] == 2
    # پاسخ قبلی نسخه ۱ باقی است
    r5 = client.get(f"/api/v1/forms/{fid}/submissions", headers=admin_headers)
    assert r5.json()["total"] >= 1


def test_field_usage_in_three_forms_counts_three(client, fdesigner_headers, steward_headers):
    """AC-07 — استفاده یک فیلد در سه فرم فعال، در شاخص مربوط عدد سه نمایش دهد"""
    field = _get_fields(client, steward_headers, "ایمیل")
    # فرم نمونه seed از ایمیل استفاده کرده؛ دو فرم دیگر می‌سازیم
    for i in range(2):
        form = _make_form(client, fdesigner_headers, f"فرم ایمیل {i}")
        ver_id = form["current_version_id"]
        client.put(f"/api/v1/form-versions/{ver_id}/schema", headers=fdesigner_headers, json={
            "schema_json": {"fields": [{"key": "email_address", "field_id": field["id"],
                                        "type": "email", "label": "ایمیل", "required": False}]},
        })
        client.post(f"/api/v1/form-versions/{ver_id}/publish", headers=fdesigner_headers)
    r = client.get(f"/api/v1/catalog/fields/{field['id']}/statistics", headers=steward_headers)
    stats = r.json()
    assert stats["forms_count"] >= 3
    assert stats["versions_count"] >= stats["forms_count"]


def test_versions_and_submissions_separate_metrics(client, steward_headers):
    """AC-08 — تعداد نسخه‌ها و تعداد پاسخ‌های فیلد جداگانه گزارش شود"""
    field = _get_fields(client, steward_headers, "موبایل")
    r = client.get(f"/api/v1/catalog/fields/{field['id']}/statistics", headers=steward_headers)
    stats = r.json()
    assert "versions_count" in stats and "submissions_count" in stats


def test_export_submissions_csv(client, admin_headers):
    forms = client.get("/api/v1/forms", headers=admin_headers).json()["items"]
    form = forms[0]
    r = client.get(f"/api/v1/forms/{form['id']}/submissions/export?format=csv", headers=admin_headers)
    assert r.status_code == 200
    assert "کد رهگیری" in r.text


def test_form_definition_export(client, fdesigner_headers):
    forms = client.get("/api/v1/forms", headers=fdesigner_headers).json()["items"]
    r = client.post(f"/api/v1/forms/{forms[0]['id']}/export", headers=fdesigner_headers)
    assert r.status_code == 200
    assert r.json()["farayara_export"] == "form_definition"


def test_draft_form_cannot_accept_submissions(client, fdesigner_headers, operator_headers):
    form = _make_form(client, fdesigner_headers, "فرم پیش‌نویس")
    r = client.post(f"/api/v1/form-versions/{form['current_version_id']}/submissions",
                    headers=operator_headers, json={"data": {}})
    assert r.status_code == 409
