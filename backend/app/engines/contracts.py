"""رندر قرارداد از الگو (بخش ۱۲ سند)

- جایگذاری متغیرها با الگوی {{key}} و پشتیبانی از کلید نقطه‌ای
- بندهای شرطی ساده: {%if key%}...{%else%}...{%endif%}
- پاکسازی HTML خروجی با bleach (بخش ۱۹ — حفاظت در برابر XSS)
"""
import re

import bleach

ALLOWED_TAGS = [
    "p", "br", "b", "strong", "i", "em", "u", "s", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "table", "thead", "tbody", "tr", "td", "th",
    "blockquote", "span", "div", "hr", "sup", "sub", "a",
]
ALLOWED_ATTRS = {"a": ["href", "title", "target"], "td": ["colspan", "rowspan"], "th": ["colspan", "rowspan"]}

_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.\u0600-\u06FF]+)\s*\}\}")
_IF_RE = re.compile(r"\{%\s*if\s+([a-zA-Z0-9_.\u0600-\u06FF]+)\s*(?:==\s*['\"]([^'\"]*)['\"])?\s*%\}")


def sanitize_html(html: str) -> str:
    """پاکسازی HTML — حذف اسکریپت، استایل تزریقی و رویدادها"""
    return bleach.clean(html or "", tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)


def _lookup(data: dict, key: str):
    """جست‌وجوی کلید — ابتدا کلید تخت، سپس مسیر نقطه‌ای تو در تو"""
    if key in data:
        return data[key]
    cur = data
    for part in key.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _truthy(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() not in ("", "0", "no", "false", "False", "خیر", "نه")
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return bool(value)


def render_template(body_html: str, data: dict | None = None) -> tuple[str, list[str]]:
    """رندر الگو با داده — خروجی: (html رندرشده، فهرست متغیرهای پرنشده)"""
    data = dict(data or {})
    html = body_html or ""
    missing: list[str] = []

    # بندهای شرطی ساده (بدون تو در تو)
    def _if_sub(match):
        key = match.group(1)
        expected = match.group(2)
        value = _lookup(data, key)
        if expected is not None:
            cond = str(value) == expected if value is not None else False
        else:
            cond = _truthy(value)
        return _IF_PLACEHOLDER_PREFIX if cond else _IF_PLACEHOLDER_ELSE

    _IF_PLACEHOLDER_PREFIX = "\x01IFTRUE\x01"
    _IF_PLACEHOLDER_ELSE = "\x01IFFALSE\x01"
    html = _IF_RE.sub(_if_sub, html)
    # بلوک‌های {%if%}...{%endif%} — ساده و بدون تو در تو
    parts = re.split(r"\x01IF(TRUE|FALSE)\x01(.*?)\{%\s*endif\s*%\}", html, flags=re.S)
    out_parts = []
    i = 0
    # الگوی split: [قبل، TRUE/FALSE، محتوا، قبل، ...] → پردازش سه‌تایی
    while i < len(parts):
        if i == 0 or i % 4 == 0:
            out_parts.append(parts[i])
            i += 1
            continue
        branch = parts[i]
        content = parts[i + 1] if i + 1 < len(parts) else ""
        if branch == "TRUE":
            out_parts.append(content)
        # FALSE → محتوا حذف می‌شود (پشتیبانی {%else%} ساده)
        elif "{%else%}" in content or "{% else %}" in content:
            seg = re.split(r"\{%\s*else\s*%\}", content, flags=re.S)
            out_parts.append(seg[1] if len(seg) > 1 else "")
        i += 2
    html = "".join(out_parts)

    # جایگذاری متغیرها
    def _var_sub(match):
        key = match.group(1)
        value = _lookup(data, key)
        if value is None or value == "":
            missing.append(key)
            return f"<span class=\"fr-var-missing\">[— {key} —]</span>"
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        return str(value)

    html = _VAR_RE.sub(_var_sub, html)
    missing = sorted(set(missing))
    return html, missing


def find_variables(body_html: str) -> list[str]:
    """استخراج متغیرهای استفاده‌شده در متن الگو"""
    vars_found = sorted(set(m.group(1) for m in _VAR_RE.finditer(body_html or "")))
    for m in _IF_RE.finditer(body_html or ""):
        vars_found.append(m.group(1))
    return sorted(set(vars_found))
