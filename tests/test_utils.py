"""Tests for morph.utils — utility functions."""

from morph.utils import detect_encoding, sniff_csv_dialect, infer_type, write_csv_rows
import io


class TestDetectEncoding:
    def test_utf8(self):
        enc, text = detect_encoding(None, "hello".encode("utf-8"))
        assert enc in ("utf-8", "utf-8-sig")

    def test_utf8_bom(self):
        raw = b"\xef\xbb\xbfhello"
        enc, text = detect_encoding(None, raw)
        assert enc == "utf-8-sig"
        assert text == "hello"

    def test_latin1(self):
        raw = "café".encode("latin-1")
        enc, text = detect_encoding(None, raw)
        assert text == "café"

    def test_empty(self):
        enc, text = detect_encoding(None, b"")
        assert isinstance(text, str)


class TestSniffCSVDialect:
    def test_comma(self):
        info = sniff_csv_dialect("a,b,c\n1,2,3\n4,5,6")
        assert info["delimiter"] == ","

    def test_tab(self):
        info = sniff_csv_dialect("a\tb\tc\n1\t2\t3")
        assert info["delimiter"] == "\t"

    def test_semicolon(self):
        info = sniff_csv_dialect("a;b;c\n1;2;3")
        assert info["delimiter"] == ";"


class TestInferType:
    def test_integer(self):
        assert infer_type("123") == 123
        assert infer_type("-456") == -456

    def test_float(self):
        assert infer_type("1.5") == 1.5
        assert infer_type("-3.14") == -3.14

    def test_boolean(self):
        assert infer_type("true") is True
        assert infer_type("False") is False

    def test_null(self):
        assert infer_type("null") is None
        assert infer_type("") is None

    def test_string(self):
        assert infer_type("hello") == "hello"
        assert infer_type("NYC") == "NYC"


class TestWriteCSVRows:
    def test_basic(self):
        buf = io.StringIO()
        rows = [{"name": "Alice", "age": 30}]
        write_csv_rows(rows, buf)
        result = buf.getvalue()
        assert "name,age" in result
        assert "Alice,30" in result

    def test_complex_values_serialized(self):
        buf = io.StringIO()
        rows = [{"data": [1, 2, 3], "meta": {"key": "val"}}]
        write_csv_rows(rows, buf)
        result = buf.getvalue()
        assert "data,meta" in result
        # Should contain JSON strings
        assert "[1, 2, 3]" in result

    def test_empty_rows(self):
        buf = io.StringIO()
        write_csv_rows([], buf)
        assert buf.getvalue() == ""

    def test_custom_delimiter(self):
        buf = io.StringIO()
        rows = [{"a": "1", "b": "2"}]
        write_csv_rows(rows, buf, delimiter=";")
        result = buf.getvalue()
        assert "a;b" in result
