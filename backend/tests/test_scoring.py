"""تست‌های موتور نمره‌گذاری (AC-10 تا AC-13)"""


def test_validation_cases_pass(client, assessor_headers):
    """AC-11 — نمره‌گذاری با مثال‌های مرجع تطابق داشته باشد"""
    assessments = client.get("/api/v1/assessments", headers=assessor_headers).json()["items"]
    asm = next(a for a in assessments if "رضایت شغلی" in a["title_fa"])
    ver_id = asm["current_version_id"]
    r = client.post(f"/api/v1/assessment-versions/{ver_id}/validate", headers=assessor_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["valid"], data
    assert data["cases"]["all_passed"], data["cases"]


def test_unpublished_cannot_run(client, assessor_headers):
    """AC-10 — آزمون تأییدنشده قابل اجرای رسمی نباشد"""
    r = client.post("/api/v1/assessments", headers=assessor_headers, json={
        "title_fa": "آزمون بدون مجوز", "license_status": "unknown",
    })
    ver_id = r.json()["current_version_id"]
    r2 = client.post(f"/api/v1/assessment-versions/{ver_id}/administrations", headers=assessor_headers, json={})
    assert r2.status_code == 422


def test_license_check_on_publish(client, assessor_headers):
    r = client.post("/api/v1/assessments", headers=assessor_headers, json={
        "title_fa": "آزمون با مجوز نامشخص", "license_status": "unknown",
    })
    ver_id = r.json()["current_version_id"]
    client.put(f"/api/v1/assessment-versions/{ver_id}/content", headers=assessor_headers, json={
        "items": [{"code": "q1", "text": "سؤال تست"}],
        "scoring_rules": {"scales": [{"code": "total", "items": ["q1"]}]},
        "items_config": {"option_values": {}, "missing_policy": "skip", "reverse_items": [], "validity": {}},
    })
    r2 = client.post(f"/api/v1/assessment-versions/{ver_id}/publish", headers=assessor_headers, json={})
    assert r2.status_code == 422
    msg = str(r2.json())
    assert "حقوق" in msg or "علمی" in msg


def test_full_assessment_run_and_scoring(client, assessor_headers):
    """اجرای کامل آزمون منتشرشده + نمره معکوس + سیاست پاسخ ناقص"""
    assessments = client.get("/api/v1/assessments", headers=assessor_headers).json()["items"]
    asm = next(a for a in assessments if "رضایت شغلی" in a["title_fa"])
    ver_id = asm["current_version_id"]

    r = client.post(f"/api/v1/assessment-versions/{ver_id}/administrations", headers=assessor_headers,
                    json={"respondent_name": "مراجع تست", "respondent_identifier": "ID-001"})
    assert r.status_code == 200, r.text
    adm_id = r.json()["id"]

    # q3 معکوس است: پاسخ "1" (هرگز ناراضی) → نمره 5؛ q6 معکوس
    answers = {"q1": "4", "q2": "5", "q3": "1", "q4": "4", "q5": "5"}  # q6 پاسخ داده نشده → skip
    r2 = client.post(f"/api/v1/assessment-administrations/{adm_id}/submit", headers=assessor_headers,
                     json={"answers": answers})
    assert r2.status_code == 200, r2.text
    computed = r2.json()["computed"]
    # 4+5+5+4+5 = 23 (با معکوس q3)
    assert computed["raw_scores"]["total"] == 23
    assert computed["completeness"] > 0.8
    assert computed["is_valid"] is True
    assert computed["interpretations"]["total"]["label"] == "رضایت بالا"

    # مشاهده نتایج با مجوز مستقل
    r3 = client.get(f"/api/v1/assessment-administrations/{adm_id}/results", headers=assessor_headers)
    assert r3.status_code == 200
    assert len(r3.json()["results"]) == 1

    # AC-13 — محاسبه مجدد، اجرای محاسباتی جدید ایجاد می‌کند
    r4 = client.post(f"/api/v1/assessment-administrations/{adm_id}/rescore", headers=assessor_headers)
    assert r4.status_code == 200
    r5 = client.get(f"/api/v1/assessment-administrations/{adm_id}/results", headers=assessor_headers)
    assert len(r5.json()["results"]) == 2
    assert len(r5.json()["score_runs"]) == 2


def test_results_require_separate_permission(client, operator_headers):
    """مشاهده نتایج روان‌شناختی نیازمند مجوز مستقل (بخش ۳.۲)"""
    admins = client.get("/api/v1/assessment-administrations", headers=operator_headers).json()["items"]
    if admins:
        r = client.get(f"/api/v1/assessment-administrations/{admins[0]['id']}/results", headers=operator_headers)
        assert r.status_code == 403
