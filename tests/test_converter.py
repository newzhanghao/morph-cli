"""Tests for morph.converter — format conversion engine."""

import json

import pytest
import yaml

from morph.converter import convert, flatten_dict


class TestFlattenDict:
    """Nested dict flattening tests."""

    def test_simple_nesting(self):
        d = {"a": {"b": 1, "c": 2}}
        result = flatten_dict(d)
        assert result == {"a_b": 1, "a_c": 2}

    def test_deep_nesting(self):
        d = {"x": {"y": {"z": 1}}}
        result = flatten_dict(d)
        assert result == {"x_y_z": 1}

    def test_array_of_primitives(self):
        d = {"scores": [85, 92]}
        result = flatten_dict(d)
        assert result == {"scores_0": 85, "scores_1": 92}

    def test_array_of_objects(self):
        d = {"items": [{"name": "A", "val": 1}, {"name": "B", "val": 2}]}
        result = flatten_dict(d)
        assert result == {
            "items_0_name": "A",
            "items_0_val": 1,
            "items_1_name": "B",
            "items_1_val": 2,
        }

    def test_empty_array(self):
        d = {"items": []}
        result = flatten_dict(d)
        assert result == {"items": ""}

    def test_mixed_values(self):
        d = {"name": "Alice", "meta": {"age": 30}, "tags": ["dev", "python"]}
        result = flatten_dict(d)
        assert result == {
            "name": "Alice",
            "meta_age": 30,
            "tags_0": "dev",
            "tags_1": "python",
        }

    def test_custom_separator(self):
        d = {"a": {"b": 1}}
        result = flatten_dict(d, sep=".")
        assert result == {"a.b": 1}


class TestConvert:
    """Format conversion tests."""

    # --- JSON → CSV ---

    def test_json_to_csv_flat(self):
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        result = convert(data, "json", "csv")
        lines = result.strip().split("\n")
        assert lines[0] == "name,age"
        assert "Alice,30" in lines
        assert "Bob,25" in lines

    def test_json_to_csv_flatten_nested(self):
        data = {"user": {"name": "Alice", "address": {"city": "NYC"}}}
        result = convert(data, "json", "csv", flatten=True)
        assert "user_name" in result
        assert "user_address_city" in result
        assert "NYC" in result

    def test_json_to_csv_no_flatten(self):
        data = {"user": {"name": "Alice"}}
        result = convert(data, "json", "csv", flatten=False)
        # Without flatten, nested dict becomes a JSON string
        assert "user" in result

    def test_json_to_csv_custom_delimiter(self):
        data = [{"a": 1, "b": 2}]
        result = convert(data, "json", "csv", csv_delimiter=";")
        assert "a;b" in result

    # --- JSON → YAML ---

    def test_json_to_yaml(self):
        data = {"name": "Alice", "age": 30}
        result = convert(data, "json", "yaml")
        assert "name: Alice" in result
        assert "age: 30" in result

    def test_json_array_to_yaml(self):
        data = [{"name": "Alice"}, {"name": "Bob"}]
        result = convert(data, "json", "yaml")
        parsed = yaml.safe_load(result)
        assert len(parsed) == 2

    # --- CSV → JSON ---

    def test_csv_to_json(self):
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        result = convert(data, "csv", "json")
        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed[0]["name"] == "Alice"
        assert parsed[0]["age"] == 30  # type inference

    def test_csv_to_json_pretty(self):
        data = [{"a": 1}]
        result = convert(data, "csv", "json", pretty=True)
        assert "\n  " in result  # indented

    # --- CSV → YAML ---

    def test_csv_to_yaml(self):
        data = [
            {"name": "Alice", "score": 95},
            {"name": "Bob", "score": 87},
        ]
        result = convert(data, "csv", "yaml")
        assert "- name: Alice" in result
        assert "score: 95" in result

    # --- YAML → JSON ---

    def test_yaml_to_json(self):
        data = {"server": {"host": "localhost", "port": 8080}}
        result = convert(data, "yaml", "json")
        parsed = json.loads(result)
        assert parsed["server"]["host"] == "localhost"

    # --- YAML → CSV ---

    def test_yaml_to_csv(self):
        data = [{"name": "Alice", "age": 30}]
        result = convert(data, "yaml", "csv")
        assert "name,age" in result
        assert "Alice,30" in result

    # --- Same format (no-op) ---

    def test_same_format_noop(self):
        data = [{"a": 1}]
        result = convert(data, "json", "json")
        parsed = json.loads(result)
        assert parsed == data

    # --- Error handling ---

    def test_unsupported_conversion(self):
        with pytest.raises(ValueError, match="Unsupported"):
            convert({}, "unknown_fmt", "csv")
