"""Tests for morph.detector — auto format detection."""

import pytest
from morph.detector import detect_format, _looks_like_csv


class TestDetectFormat:
    """Format detection tests."""

    def test_detect_json_object(self):
        fmt, data = detect_format(None, '{"a": 1, "b": 2}')
        assert fmt == "json"
        assert data == {"a": 1, "b": 2}

    def test_detect_json_array(self):
        fmt, data = detect_format(None, '[1, 2, 3]')
        assert fmt == "json"
        assert data == [1, 2, 3]

    def test_detect_json_by_extension(self):
        fmt, data = detect_format("data.json", '{"x": 1}')
        assert fmt == "json"

    def test_detect_csv(self):
        text = "name,age,city\nAlice,30,NYC\nBob,25,SF"
        fmt, data = detect_format(None, text)
        assert fmt == "csv"
        assert len(data) == 2
        assert data[0]["name"] == "Alice"

    def test_detect_csv_by_extension(self):
        fmt, data = detect_format("data.csv", "name,age\nAlice,30\n")
        assert fmt == "csv"

    def test_detect_yaml(self):
        text = "server:\n  host: localhost\n  port: 8080\n"
        fmt, data = detect_format(None, text)
        assert fmt == "yaml"
        assert data["server"]["host"] == "localhost"

    def test_detect_yaml_by_extension(self):
        fmt, data = detect_format("config.yaml", "key: value\n")
        assert fmt == "yaml"

    def test_detect_yml_extension(self):
        fmt, data = detect_format("config.yml", "key: value\n")
        assert fmt == "yaml"

    def test_bare_string_falls_back_to_yaml(self):
        # A bare string without JSON brackets or CSV structure
        # should be parsed as YAML (which handles scalars)
        fmt, data = detect_format(None, "barestringwithoutstructure")
        # YAML can parse bare strings as scalar values
        assert fmt == "yaml"
        assert data == "barestringwithoutstructure"


class TestLooksLikeCSV:
    """CSV heuristic tests."""

    def test_comma_delimited(self):
        assert _looks_like_csv("a,b,c\n1,2,3\n4,5,6") is True

    def test_tab_delimited(self):
        assert _looks_like_csv("a\tb\tc\n1\t2\t3") is True

    def test_not_csv_single_line(self):
        assert _looks_like_csv("hello world") is False

    def test_yaml_not_mistaken_for_csv(self):
        assert _looks_like_csv("key: value\nother: thing") is False
