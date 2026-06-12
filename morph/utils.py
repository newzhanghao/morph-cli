"""Utility functions for encoding detection, type inference, etc."""

import csv
import io
import re
from typing import Any


# Common encodings to try, ordered by likelihood
_ENCODINGS = ["utf-8", "utf-8-sig", "latin-1", "gbk", "cp1252", "iso-8859-1"]


def detect_encoding(file_path: str | None, raw: bytes) -> tuple[str, str]:
    """Detect encoding and decode raw bytes to string.

    Returns (encoding, text).
    """
    # Check BOM first
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig", raw.decode("utf-8-sig")

    for enc in _ENCODINGS:
        try:
            text = raw.decode(enc)
            # Quick sanity: check for replacement characters
            if "�" not in text:
                return enc, text
        except (UnicodeDecodeError, UnicodeError):
            continue

    # Last resort: utf-8 with errors
    return "utf-8", raw.decode("utf-8", errors="replace")


def sniff_csv_dialect(text: str) -> dict[str, Any]:
    """Detect CSV dialect from sample text.

    Returns a dict with delimiter, quotechar, etc.
    """
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(text[:8192])
        delimiter = dialect.delimiter
    except (csv.Error, Exception):
        # Fallback: count delimiters
        lines = text.strip().split("\n")[:20]
        counts = {",": 0, "\t": 0, ";": 0, "|": 0}
        for line in lines:
            for delim in counts:
                counts[delim] += line.count(delim)
        delimiter = max(counts, key=counts.get) if max(counts.values()) > 0 else ","

    try:
        has_header = csv.Sniffer().has_header(text[:8192])
    except (csv.Error, Exception):
        has_header = True  # assume first row is header

    return {"delimiter": delimiter, "has_header": has_header}


def infer_type(value: str) -> Any:
    """Infer the best Python type for a string value from CSV."""
    if value == "":
        return None

    # Boolean
    lower = value.lower().strip()
    if lower in ("true", "yes", "on"):
        return True
    if lower in ("false", "no", "off"):
        return False

    # Null
    if lower in ("null", "none", "nil", "na", "n/a", ""):
        return None

    # Integer
    if re.match(r"^-?\d+$", value):
        try:
            return int(value)
        except ValueError:
            pass

    # Float
    if re.match(r"^-?\d+\.?\d*([eE][+-]?\d+)?$", value):
        try:
            return float(value)
        except ValueError:
            pass

    return value


def write_csv_rows(rows: list[dict], output: io.TextIOBase, delimiter: str = ",") -> None:
    """Write list of dicts as CSV to a text stream."""
    if not rows:
        return

    # Collect all keys, preserving order from first row + adding new keys from later rows
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for k in row:
            if k not in seen:
                keys.append(k)
                seen.add(k)

    writer = csv.DictWriter(
        output,
        fieldnames=keys,
        delimiter=delimiter,
        quoting=csv.QUOTE_MINIMAL,
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    for row in rows:
        # Convert complex values to JSON strings
        safe_row = {}
        for k in keys:
            v = row.get(k, "")
            if isinstance(v, (dict, list, tuple, bool)) or v is None:
                safe_row[k] = _serialize_cell(v)
            else:
                safe_row[k] = v
        writer.writerow(safe_row)


def _serialize_cell(value: Any) -> str:
    """Serialize a cell value for CSV output."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (dict, list, tuple)):
        import json

        return json.dumps(value, ensure_ascii=False)
    return str(value)
