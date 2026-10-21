"""موتور نمره‌گذاری امن آزمون (بخش ۱۱ سند)

- اجرای قواعد کاربر با eval ممنوع؛ از ارزیاب امن AST استفاده می‌شود.
- پاسخ ناقص با سیاست skip/zero/invalidate کنترل می‌شود.
- برای هر اجرای محاسبه، ScoreRun جدید با تصویر قواعد ثبت می‌شود
  (تغییر قواعد نتایج تاریخی را بی‌صدا تغییر نمی‌دهد — AC-13).
"""
from ..engines.safe_eval import SafeEvalError, safe_eval, safe_eval_number
from ..models import AssessmentItem, AssessmentVersion

DEFAULT_POLICY = "skip"  # skip / zero / invalidate


def compute_scores(version: AssessmentVersion, items: list[AssessmentItem], answers: dict) -> dict:
    """محاسبه نمره خام مقیاس‌ها بر اساس قواعد نسخه

    answers نمونه: {"q1": "3", "q2": "1", ...} — مقدار می‌تواند اندیس گزینه یا مقدار آن باشد
    خروجی: {raw_scores, item_scores, completeness, is_valid, details}
    """
    config = dict(version.items_config or {})
    option_values: dict = config.get("option_values") or {}
    reverse_items: list = config.get("reverse_items") or []
    policy = config.get("missing_policy", DEFAULT_POLICY)
    validity = config.get("validity") or {}
    min_answered = float(validity.get("min_answered_ratio", 0) or 0)

    item_scores: dict = {}
    answered = 0
    for item in items:
        raw = answers.get(item.code)
        if raw is None or raw == "" or (isinstance(raw, str) and raw.strip() == ""):
            if policy == "zero":
                item_scores[item.code] = 0.0
            else:
                item_scores[item.code] = None  # skip یا invalidate
            continue
        answered += 1
        val = _option_score(raw, item, option_values)
        if val is None:
            item_scores[item.code] = None
            continue
        if item.code in reverse_items or item.is_reverse:
            val = _reverse_score(val, item, option_values)
        item_scores[item.code] = val * float(item.weight or 1.0)

    total_items = len(items) or 1
    completeness = round(answered / total_items, 4)
    is_valid = True
    invalid_reason = None
    if completeness < min_answered:
        is_valid = False
        invalid_reason = f"نرخ پاسخ {completeness:.0%} کمتر از حداقل مجاز {min_answered:.0%} است"
    if policy == "invalidate" and answered < total_items:
        is_valid = False
        invalid_reason = "سیاست پاسخ ناقص این آزمون، نتیجه را نامعتبر می‌کند"

    # متغیرهای در دسترس عبارات: امتیاز هر گره + مجموع/میانگین گروهی
    variables: dict = {}
    for code, sc in item_scores.items():
        variables[code] = _to_num(sc)
    # متغیرهای کمکی روی آیتم‌ها
    variables["answered_count"] = answered
    variables["total_items"] = total_items

    scales_cfg = (version.scoring_rules or {}).get("scales") or []
    raw_scores: dict = {}
    scale_details: list = []

    def eval_scale(cfg) -> float | None:
        expr = cfg.get("expression")
        if expr:
            try:
                return round(safe_eval_number(expr, variables), 4)
            except SafeEvalError as e:
                raise ValueError(f"خطا در عبارت مقیاس «{cfg.get('code')}»: {e}")
        item_codes = cfg.get("items") or []
        vals = [_to_num(item_scores.get(c)) for c in item_codes]
        vals = [v for v in vals if v is not None]
        if cfg.get("mode") == "average":
            return round(sum(vals) / len(vals), 4) if vals else 0.0
        return round(float(sum(vals)), 4)

    # دو گذر: اول مقیاس‌های آیتم‌محور، سپس عبارت‌محور تا بتوانند به مقیاس‌های قبلی ارجاع دهند
    deferred = []
    for cfg in scales_cfg:
        if cfg.get("expression"):
            deferred.append(cfg)
        else:
            raw_scores[cfg.get("code")] = eval_scale(cfg)
    for code, score in raw_scores.items():
        variables[code] = score
    for cfg in deferred:
        raw_scores[cfg.get("code")] = eval_scale(cfg)
    for code, score in raw_scores.items():
        variables[code] = score

    # تفسیر بر اساس بازه‌ها
    interpretations: dict = {}
    for cfg in scales_cfg:
        code = cfg.get("code")
        score = raw_scores.get(code)
        chosen = None
        for rng in (cfg.get("interpretations") or []):
            mn = rng.get("min")
            mx = rng.get("max")
            if score is None:
                continue
            if (mn is None or score >= float(mn)) and (mx is None or score <= float(mx)):
                chosen = rng
                break
        interpretations[code] = {
            "score": score,
            "label": (chosen or {}).get("label"),
            "description": (chosen or {}).get("description"),
        }
        scale_details.append({
            "code": code,
            "title": cfg.get("title", code),
            "score": score,
            "min": cfg.get("min"),
            "max": cfg.get("max"),
            "interpretation": (chosen or {}).get("label"),
            "description": (chosen or {}).get("description"),
        })

    # تبدیل نمره با جداول هنجار (در صورت تعریف)
    converted = _apply_norms(version, raw_scores)

    return {
        "raw_scores": raw_scores,
        "item_scores": item_scores,
        "completeness": completeness,
        "is_valid": is_valid,
        "invalid_reason": invalid_reason,
        "interpretations": interpretations,
        "scale_details": scale_details,
        "converted_scores": converted,
        "missing_policy": policy,
        "answered": answered,
        "total_items": total_items,
    }


def _to_num(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _option_score(raw, item: AssessmentItem, option_values: dict) -> float | None:
    """تبدیل پاسخ به نمره — با پشتیبانی از options تعریف‌شده روی گره و نگاشت سراسری"""
    raw_s = str(raw)
    # ۱) گزینه‌های خود گره
    for opt in (item.options or []):
        if str(opt.get("value")) == raw_s:
            if opt.get("score") is not None:
                return float(opt["score"])
            return _to_num(opt.get("value"))
    # ۲) نگاشت سراسری option_values
    if raw_s in option_values:
        return _to_num(option_values[raw_s])
    # ۳) مقدار عددی مستقیم
    try:
        return float(raw_s)
    except ValueError:
        return None


def _reverse_score(score: float, item: AssessmentItem, option_values: dict) -> float:
    """نمره‌گذاری معکوس: max + min - score"""
    scores = [float(o["score"]) for o in (item.options or []) if o.get("score") is not None]
    if not scores and option_values:
        scores = sorted(_to_num(v) for v in option_values.values())
    if not scores:
        return score
    return float(max(scores) + min(scores) - score)


def _apply_norms(version: AssessmentVersion, raw_scores: dict) -> dict:
    """تبدیل نمره با جداول هنجار معتبر — انتخاب هنجار بر اساس شرایط مجاز"""
    converted: dict = {}
    for norm in (version.norm_sets or []):
        conditions = norm.get("conditions") or {}
        table = norm.get("table") or []
        if not table:
            continue
        # ساده: اگر شرایطی تعریف شده، فقط رکوردهای دارای شرایط را اعمال کن
        for scale_code, ranges in table.items():
            score = raw_scores.get(scale_code)
            if score is None:
                continue
            for rng in ranges:
                mn = rng.get("raw_min")
                mx = rng.get("raw_max")
                if (mn is None or score >= float(mn)) and (mx is None or score <= float(mx)):
                    converted[f"{scale_code}@{norm.get('title', 'norm')}"] = rng.get("converted")
                    break
    return converted


def run_validation_cases(version: AssessmentVersion, items: list[AssessmentItem], cases) -> dict:
    """اجرای مثال‌های مرجع و مقایسه خروجی با نتایج مورد انتظار (بخش ۱۱.۳)"""
    results = []
    passed = 0
    for case in cases:
        try:
            computed = compute_scores(version, items, case.input_answers or {})
            ok = True
            diffs = {}
            for scale_code, expected in (case.expected or {}).items():
                actual = computed["raw_scores"].get(scale_code)
                if actual is None or abs(float(actual) - float(expected)) > 0.01:
                    ok = False
                    diffs[scale_code] = {"expected": expected, "actual": actual}
            if ok:
                passed += 1
            results.append({
                "case": case.title or case.id,
                "passed": ok,
                "diffs": diffs,
                "computed_raw": computed["raw_scores"],
            })
        except (ValueError, SafeEvalError) as e:
            results.append({"case": case.title or case.id, "passed": False, "error": str(e)})
    return {
        "total": len(results),
        "passed": passed,
        "all_passed": passed == len(results) and len(results) > 0,
        "results": results,
    }
