"""Safe expression evaluator — AST-based, no eval(), no function calls."""
import ast, operator
from typing import Any

_COMPARE_OPS = {
    ast.Eq: operator.eq, ast.NotEq: operator.ne,
    ast.Lt: operator.lt, ast.LtE: operator.le,
    ast.Gt: operator.gt, ast.GtE: operator.ge,
    ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b,
    ast.Is: operator.is_, ast.IsNot: operator.is_not,
}
_BINARY_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {
    ast.UAdd: operator.pos, ast.USub: operator.neg,
    ast.Not: operator.not_,
}


class UnsafeExpression(ValueError):
    """Expression uses syntax not in the whitelist."""
    pass

class EvalError(ValueError):
    """Expression parsing or evaluation failure."""
    pass


def _resolve_value(node: ast.AST, data: dict) -> Any:
    """Recursively evaluate an AST node against a data dict."""
    # Literals
    if isinstance(node, ast.Constant):
        return node.value

    # Name lookup
    if isinstance(node, ast.Name):
        return data.get(node.id)

    # Dot-notation: user.age
    if isinstance(node, ast.Attribute):
        v = _resolve_value(node.value, data)
        return v.get(node.attr) if isinstance(v, dict) else None

    # Subscript: user['age'], items[0]
    if isinstance(node, ast.Subscript):
        v = _resolve_value(node.value, data)
        k = _resolve_value(node.slice, data)
        if isinstance(v, (dict, list, tuple)):
            try:
                return v[k]
            except (KeyError, IndexError, TypeError):
                return None
        return None

    # Slice: items[1:3]
    if isinstance(node, ast.Slice):
        return slice(
            _resolve_value(node.lower, data) if node.lower else None,
            _resolve_value(node.upper, data) if node.upper else None,
            _resolve_value(node.step, data) if node.step else None,
        )

    # Unary: -x, not x
    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise UnsafeExpression(f"Unsupported unary operator: {type(node.op).__name__}")
        return op(_resolve_value(node.operand, data))

    # Comparison: a == b, a > b, a in b, etc.
    if isinstance(node, ast.Compare):
        left = _resolve_value(node.left, data)
        for op_node, comparator in zip(node.ops, node.comparators):
            right = _resolve_value(comparator, data)
            op = _COMPARE_OPS.get(type(op_node))
            if op is None:
                raise UnsafeExpression(f"Unsupported comparison operator: {type(op_node).__name__}")
            try:
                if not op(left, right):
                    return False
            except TypeError:
                return False
            left = right
        return True

    # Boolean: and / or (short-circuit)
    if isinstance(node, ast.BoolOp):
        vals = (_resolve_value(v, data) for v in node.values)
        if isinstance(node.op, ast.Or):
            return any(vals)  # short-circuits via generator
        if isinstance(node.op, ast.And):
            return all(vals)  # short-circuits via generator
        raise UnsafeExpression(f"Unsupported boolean operator: {type(node.op).__name__}")

    # Binary: +, -, *, /, etc.
    if isinstance(node, ast.BinOp):
        op = _BINARY_OPS.get(type(node.op))
        if op is None:
            raise UnsafeExpression(f"Unsupported binary operator: {type(node.op).__name__}")
        return op(_resolve_value(node.left, data), _resolve_value(node.right, data))

    # Lists and tuples
    if isinstance(node, ast.List):
        return [_resolve_value(el, data) for el in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_resolve_value(el, data) for el in node.elts)

    # Expression wrapper
    if isinstance(node, ast.Expression):
        return _resolve_value(node.body, data)

    # Blocked constructs — caught here instead of a separate AST walk
    if isinstance(node, ast.Call):
        raise UnsafeExpression(
            f"Function calls are not allowed in filter expressions "
            f"(found: {ast.dump(node)})"
        )
    if isinstance(node, (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
        raise UnsafeExpression(
            f"{type(node).__name__} expressions are not allowed in filter expressions"
        )

    raise UnsafeExpression(
        f"Unsupported syntax: {type(node).__name__} (in expression: {ast.dump(node)})"
    )


def evaluate(expression: str, data: dict) -> bool:
    """Evaluate a filter expression against a data record."""
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError as e:
        raise EvalError(f"Invalid expression: {e}") from e

    try:
        return bool(_resolve_value(tree, data))
    except UnsafeExpression:
        raise
    except Exception as e:
        raise EvalError(f"Error evaluating expression: {e}") from e


def filter_records(records: list[dict], expression: str) -> list[dict]:
    """Filter a list of records using an expression. Skips errored records."""
    if not records:
        return []
    result = []
    for record in records:
        try:
            if evaluate(expression, record):
                result.append(record)
        except (EvalError, UnsafeExpression, Exception):
            continue
    return result
