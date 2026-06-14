"""Tests for morph/filter_expr.py — safe expression evaluator."""

import pytest
from morph.filter_expr import evaluate, filter_records, EvalError, UnsafeExpression


class TestEvaluate:
    """Tests for the evaluate() function."""

    def test_simple_comparison_gt(self):
        assert evaluate("age > 18", {"age": 20}) is True
        assert evaluate("age > 18", {"age": 15}) is False
        assert evaluate("age > 18", {"age": 18}) is False

    def test_simple_comparison_gte(self):
        assert evaluate("age >= 18", {"age": 18}) is True
        assert evaluate("age >= 18", {"age": 17}) is False

    def test_simple_comparison_eq(self):
        assert evaluate("status == 'active'", {"status": "active"}) is True
        assert evaluate("status == 'active'", {"status": "inactive"}) is False

    def test_simple_comparison_neq(self):
        assert evaluate("status != 'active'", {"status": "inactive"}) is True

    def test_comparison_lt(self):
        assert evaluate("count < 10", {"count": 5}) is True
        assert evaluate("count < 10", {"count": 10}) is False

    def test_comparison_lte(self):
        assert evaluate("count <= 10", {"count": 10}) is True

    def test_boolean_and(self):
        assert evaluate("age > 18 and status == 'active'", {"age": 25, "status": "active"}) is True
        assert evaluate("age > 18 and status == 'active'", {"age": 25, "status": "inactive"}) is False
        assert evaluate("age > 18 and status == 'active'", {"age": 15, "status": "active"}) is False

    def test_boolean_or(self):
        assert evaluate("age > 18 or status == 'admin'", {"age": 15, "status": "admin"}) is True
        assert evaluate("age > 18 or status == 'admin'", {"age": 15, "status": "user"}) is False

    def test_not_operator(self):
        assert evaluate("not active", {"active": False}) is True
        assert evaluate("not active", {"active": True}) is False

    def test_membership_in(self):
        assert evaluate("'admin' in roles", {"roles": ["user", "admin"]}) is True
        assert evaluate("'admin' in roles", {"roles": ["user"]}) is False

    def test_membership_not_in(self):
        assert evaluate("'admin' not in roles", {"roles": ["user"]}) is True

    def test_dot_notation(self):
        data = {"user": {"name": "Alice", "address": {"city": "NYC"}}}
        assert evaluate("user.name == 'Alice'", data) is True
        assert evaluate("user.address.city == 'NYC'", data) is True
        assert evaluate("user.address.city == 'LA'", data) is False

    def test_missing_fields_return_false(self):
        assert evaluate("age > 18", {"name": "Alice"}) is False

    def test_nested_missing_fields(self):
        assert evaluate("user.age > 18", {"user": {"name": "Alice"}}) is False

    def test_arithmetic_comparison(self):
        data = {"price": 10, "qty": 5}
        assert evaluate("price * qty >= 50", data) is True
        assert evaluate("price * qty < 50", data) is False

    def test_comparison_with_string(self):
        assert evaluate("name == 'Alice'", {"name": "Alice"}) is True

    def test_comparison_with_number(self):
        assert evaluate("count == 0", {"count": 0}) is True
        assert evaluate("count == 0", {"count": 1}) is False

    def test_null_values(self):
        assert evaluate("name == None", {"name": None}) is True
        assert evaluate("name == None", {"name": "Alice"}) is False

    def test_list_literal(self):
        data = {"type": "a"}
        assert evaluate("type in ['a', 'b']", data) is True
        assert evaluate("type in ['c', 'd']", data) is False

    def test_chained_comparison(self):
        assert evaluate("1 < age < 100", {"age": 50}) is True
        assert evaluate("1 < age < 100", {"age": 0}) is False
        assert evaluate("1 < age < 100", {"age": 100}) is False

    def test_subscript_access(self):
        data = {"items": [1, 2, 3]}
        assert evaluate("items[0] == 1", data) is True
        data2 = {"meta": {"tags": ["a", "b"]}}
        assert evaluate("meta['tags'][0] == 'a'", data2) is True


class TestUnsafeExpressions:
    """Tests that unsafe expressions are properly rejected."""

    def test_function_call_blocked(self):
        with pytest.raises(UnsafeExpression):
            evaluate("len(items) > 0", {"items": [1, 2, 3]})

    def test_import_blocked(self):
        with pytest.raises(UnsafeExpression):
            evaluate("__import__('os')", {})

    def test_lambda_blocked(self):
        with pytest.raises(UnsafeExpression):
            evaluate("(lambda x: x)(1)", {})

    def test_comprehension_blocked(self):
        with pytest.raises(UnsafeExpression):
            evaluate("[x for x in items]", {"items": [1, 2, 3]})


class TestEvalErrors:
    """Tests for expression parsing errors."""

    def test_invalid_syntax(self):
        with pytest.raises(EvalError):
            evaluate("age >>> 18", {"age": 20})

    def test_empty_expression(self):
        with pytest.raises(EvalError):
            evaluate("", {"age": 20})

    def test_garbage_expression(self):
        with pytest.raises(EvalError):
            evaluate("!@#$%", {"age": 20})


class TestFilterRecords:
    """Tests for the filter_records() function."""

    def test_basic_filter(self):
        records = [
            {"name": "Alice", "age": 25},
            {"name": "Bob", "age": 17},
            {"name": "Charlie", "age": 30},
        ]
        result = filter_records(records, "age >= 18")
        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        assert result[1]["name"] == "Charlie"

    def test_empty_records(self):
        assert filter_records([], "age > 18") == []

    def test_all_match(self):
        records = [{"age": 20}, {"age": 30}]
        assert len(filter_records(records, "age > 10")) == 2

    def test_none_match(self):
        records = [{"age": 5}, {"age": 10}]
        assert filter_records(records, "age > 18") == []

    def test_skips_bad_records_gracefully(self):
        records = [
            {"age": 25},
            {"name": "Bob"},  # missing 'age' field → returns False
            {"age": 30},
        ]
        # Bob is excluded because missing 'age' means age > 18 is False
        result = filter_records(records, "age > 18")
        assert len(result) == 2
        assert result[0]["age"] == 25
        assert result[1]["age"] == 30
