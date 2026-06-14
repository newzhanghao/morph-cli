"""Safe expression evaluator for morph filter commands.

Uses Python's ast module to parse and evaluate filter expressions
without ever calling eval(). Function calls are blocked at the AST level.
Only whitelisted operators and syntax are allowed.

Examples:
    >>> evaluate("age > 18", {"age": 20})
    True
    >>> evaluate("status == 'active'", {"status": "inactive"})
    False
    >>> evaluate("user.age >= 21", {"user": {"age": 25}})
    True
    >>> evaluate("'admin' in roles", {"roles": ["user", "admin"]})
    True
"""

import ast
import operator
from typing import Any


# ---------------------------------------------------------------------------
# Whitelisted operators — map AST node types to Python operators
# ---------------------------------------------------------------------------

_COMPARE_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
    ast.Is: operator.is_,
    ast.IsNot: operator.is_not,
}

_BOOL_OPS = {
    ast.And: lambda a, b: a and b,
    ast.Or: lambda a, b: a or b,
}

_BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
    ast.Not: operator.not_,
}


class UnsafeExpression(ValueError):
    """Raised when an expression contains operations not in the whitelist."""
    pass


class EvalError(ValueError):
    """Raised when expression evaluation fails against the data."""
    pass


def _resolve_value(node: ast.AST, data: dict) -> Any:
    """Recursively evaluate an AST node against a data dict.

    This is the core of the safe evaluator. Only handles node types
    that are explicitly whitelisted — anything else raises UnsafeExpression.
    """
    # --- Literals ---
    if isinstance(node, ast.Constant):
        return node.value

    # --- Name lookup (top-level key) ---
    if isinstance(node, ast.Name):
        return data.get(node.id)

    # --- Dot-notation: user.age → data['user']['age'] ---
    if isinstance(node, ast.Attribute):
        value = _resolve_value(node.value, data)
        if isinstance(value, dict):
            return value.get(node.attr)
        # For non-dict values (e.g. strings have .endswith etc.), return None
        # We don't allow attribute access on non-dicts since that's an attack surface
        return None

    # --- Subscript: user['age'], items[0] ---
    if isinstance(node, ast.Subscript):
        value = _resolve_value(node.value, data)
        key = _resolve_value(node.slice, data)
        if isinstance(value, (dict, list, tuple)):
            try:
                return value[key]
            except (KeyError, IndexError, TypeError):
                return None
        return None

    # --- Slice: items[1:3] ---
    if isinstance(node, ast.Slice):
        lower = _resolve_value(node.lower, data) if node.lower else None
        upper = _resolve_value(node.upper, data) if node.upper else None
        step = _resolve_value(node.step, data) if node.step else None
        return slice(lower, upper, step)

    # --- Unary operators: -x, not x ---
    if isinstance(node, ast.UnaryOp):
        operand = _resolve_value(node.operand, data)
        op_func = _UNARY_OPS.get(type(node.op))
        if op_func is None:
            raise UnsafeExpression(
                f"Unsupported unary operator: {type(node.op).__name__}"
            )
        return op_func(operand)

    # --- Comparison: a == b, a > b, a in b, etc. ---
    if isinstance(node, ast.Compare):
        left = _resolve_value(node.left, data)
        for op_node, comparator in zip(node.ops, node.comparators):
            right = _resolve_value(comparator, data)
            op_func = _COMPARE_OPS.get(type(op_node))
            if op_func is None:
                raise UnsafeExpression(
                    f"Unsupported comparison operator: {type(op_node).__name__}"
                )
            # Handle missing fields gracefully — None can't compare with int/str
            try:
                if not op_func(left, right):
                    return False
            except TypeError:
                # e.g. None > 18 → return False
                return False
            left = right
        return True

    # --- Boolean operators: and / or ---
    if isinstance(node, ast.BoolOp):
        # Short-circuit: evaluate one at a time
        values = (_resolve_value(v, data) for v in node.values)
        op_type = type(node.op)
        if op_type == ast.Or:
            for v in values:
                if v:
                    return True
            return False
        elif op_type == ast.And:
            for v in values:
                if not v:
                    return False
            return True
        else:
            raise UnsafeExpression(
                f"Unsupported boolean operator: {op_type.__name__}"
            )

    # --- Binary operators: +, -, *, /, etc. ---
    if isinstance(node, ast.BinOp):
        left = _resolve_value(node.left, data)
        right = _resolve_value(node.right, data)
        op_func = _BINARY_OPS.get(type(node.op))
        if op_func is None:
            raise UnsafeExpression(
                f"Unsupported binary operator: {type(node.op).__name__}"
            )
        return op_func(left, right)

    # --- Lists and tuples ---
    if isinstance(node, ast.List):
        return [_resolve_value(el, data) for el in node.elts]

    if isinstance(node, ast.Tuple):
        return tuple(_resolve_value(el, data) for el in node.elts)

    # --- Expression wrapper ---
    if isinstance(node, ast.Expression):
        return _resolve_value(node.body, data)

    # If we got here, it's an unsupported node type
    raise UnsafeExpression(
        f"Unsupported syntax: {type(node).__name__} "
        f"(in expression: {ast.dump(node)})"
    )


def evaluate(expression: str, data: dict) -> bool:
    """Evaluate a filter expression against a single data record.

    Args:
        expression: Filter expression (e.g. "age > 18", "status == 'active'").
        data: Single record as a dict.

    Returns:
        True if the record matches the filter.

    Raises:
        UnsafeExpression: If the expression uses unsupported syntax.
        EvalError: If the expression is syntactically invalid.
    """
    # Parse the expression into an AST
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError as e:
        raise EvalError(f"Invalid expression: {e}") from e

    # Security check: walk the entire AST and reject any function calls
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            raise UnsafeExpression(
                "Function calls are not allowed in filter expressions "
                f"(found: {ast.dump(node)})"
            )
        # Also block comprehensions and lambda (they're basically function calls)
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            raise UnsafeExpression(
                f"Comprehensions are not allowed in filter expressions "
                f"(found: {type(node).__name__})"
            )
        if isinstance(node, ast.Lambda):
            raise UnsafeExpression(
                "Lambda expressions are not allowed in filter expressions"
            )

    # Evaluate
    try:
        result = _resolve_value(tree, data)
    except UnsafeExpression:
        raise
    except Exception as e:
        raise EvalError(f"Error evaluating expression: {e}") from e

    return bool(result)


def filter_records(records: list[dict], expression: str) -> list[dict]:
    """Filter a list of records using an expression.

    Args:
        records: List of data records (dicts).
        expression: Filter expression string.

    Returns:
        Filtered list of records.

    Raises:
        UnsafeExpression: If the expression uses unsupported syntax.
        EvalError: If the expression is invalid.
    """
    if not records:
        return []
    result = []
    for record in records:
        try:
            if evaluate(expression, record):
                result.append(record)
        except (EvalError, UnsafeExpression, Exception):
            # If evaluation fails for this record, skip it
            continue
    return result
