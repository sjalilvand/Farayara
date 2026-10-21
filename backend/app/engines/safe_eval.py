"""ارزیاب امن عبارات — بدون eval (بخش ۱۱.۲ سند)

ممنوعیت: دسترسی به فایل، شبکه، سیستم‌عامل، صفت‌ها و فراخوانی آزاد.
مجاز: اعداد، رشته‌های کوتاه، متغیرها، عملگرهای ریاضی/منطقی/مقایسه‌ای و
توکن‌های مجاز {sum, avg, min, max, round, abs, len}.
"""
import ast
import operator

_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
}
_UNARY = {ast.Not: operator.not_, ast.USub: operator.neg, ast.UAdd: operator.pos}
_CMPOPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
}
_BOOL = {ast.And: all, ast.Or: any}

_ALLOWED_FUNCS = {"sum": sum, "avg": lambda xs: sum(xs) / len(xs) if xs else 0,
                  "min": min, "max": max, "round": round, "abs": abs, "len": len}

MAX_LEN = 500


class SafeEvalError(Exception):
    pass


def _to_number(v):
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str):
        try:
            return float(v) if "." in v else int(v)
        except ValueError:
            return 0.0
    return 0.0


def _eval_node(node, variables):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, variables)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, bool, str)) or node.value is None:
            return node.value
        raise SafeEvalError("مقدار ثابت مجاز نیست")
    if isinstance(node, ast.Name):
        if node.id in variables:
            return variables[node.id]
        # متغیر تعریف‌نشده = مقدار صفر (پاسخ ناقص)
        return 0
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        left = _to_number(_eval_node(node.left, variables))
        right = _to_number(_eval_node(node.right, variables))
        return _BINOPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval_node(node.operand, variables))
    if isinstance(node, ast.BoolOp) and type(node.op) in _BOOL:
        values = [bool(_eval_node(v, variables)) for v in node.values]
        return _BOOL[type(node.op)](values)
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, variables)
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval_node(comparator, variables)
            fn = _CMPOPS.get(type(op))
            if fn is None:
                raise SafeEvalError("عملگر مقایسه مجاز نیست")
            if isinstance(left, str) or isinstance(right, str):
                # مقایسه رشته‌ای مستقیم (بدون تبدیل عددی)
                if not fn(str(left), str(right)):
                    return False
            elif not fn(_to_number(left), _to_number(right)):
                return False
            left = right
        return True
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCS:
            raise SafeEvalError("تابع مجاز نیست")
        if node.keywords:
            raise SafeEvalError("آرگومان کلیدواژه‌ای مجاز نیست")
        args = [_eval_node(a, variables) for a in node.args]
        if node.func.id in ("sum", "avg", "min", "max", "len"):
            # پذیرش آرگومان لیستی یا چند مقدار
            if len(args) == 1 and isinstance(args[0], (list, tuple)):
                args = [list(args[0])]
        return _ALLOWED_FUNCS[node.func.id](*args)
    if isinstance(node, ast.List):
        return [_eval_node(e, variables) for e in node.elts]
    raise SafeEvalError(f"عبارت مجاز نیست: {type(node).__name__}")


def safe_eval(expression: str, variables: dict | None = None):
    """ارزیابی امن عبارت؛ در خطا SafeEvalError برمی‌گرداند"""
    if not expression or not str(expression).strip():
        return None
    expr = str(expression).strip()
    if len(expr) > MAX_LEN:
        raise SafeEvalError("عبارت بیش از حد طولانی است")
    # پاکسازی ${...} استاندارد BPMN
    if expr.startswith("${") and expr.endswith("}"):
        expr = expr[2:-1].strip()
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise SafeEvalError(f"ساختار عبارت نامعتبر است: {e}") from None
    return _eval_node(tree, dict(variables or {}))


def safe_eval_number(expression: str, variables: dict | None = None) -> float:
    """ارزیابی امن با خروجی عددی (برای نمره‌گذاری)"""
    result = safe_eval(expression, variables)
    if result is None:
        return 0.0
    if isinstance(result, (list, tuple)):
        return float(sum(_to_number(x) for x in result))
    return float(_to_number(result))
