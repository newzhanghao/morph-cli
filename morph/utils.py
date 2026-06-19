"""Utility functions: encoding detection, CSV dialect sniffing, type inference."""
import csv, io, json, re
from typing import Any

_ENCODINGS = ["utf-8", "utf-8-sig", "latin-1", "gbk", "cp1252", "iso-8859-1"]


def detect_encoding(file_path: str | None, raw: bytes) -> tuple[str, str]:
    """Detect encoding and decode bytes to string."""
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig", raw.decode("utf-8-sig")
    for enc in _ENCODINGS:
        try:
            text = raw.decode(enc)
            if "�" not in text:
                return enc, text
        except UnicodeError:
            continue
    return "utf-8", raw.decode("utf-8", errors="replace")


def sniff_csv_dialect(text: str) -> dict[str, Any]:
    """Detect CSV delimiter and header presence."""
    try:
        dialect = csv.Sniffer().sniff(text[:8192])
        delimiter = dialect.delimiter
    except (csv.Error, Exception):
        lines = text.strip().split("\n")[:20]
        delim_counts = {d: sum(l.count(d) for l in lines) for d in (",", "\t", ";", "|")}
        delimiter = max(delim_counts, key=delim_counts.get) if max(delim_counts.values()) else ","
    try:
        has_header = csv.Sniffer().has_header(text[:8192])
    except (csv.Error, Exception):
        has_header = True
    return {"delimiter": delimiter, "has_header": has_header}


def infer_type(value: str) -> Any:
    """Infer Python type from a CSV string value."""
    if value == "":
        return None
    lower = value.lower().strip()
    if lower in ("true", "yes", "on"):
        return True
    if lower in ("false", "no", "off"):
        return False
    if lower in ("null", "none", "nil", "na", "n/a"):
        return None
    if re.match(r"^-?\d+$", value):
        try:
            return int(value)
        except ValueError:
            pass
    if re.match(r"^-?\d+\.?\d*([eE][+-]?\d+)?$", value):
        try:
            return float(value)
        except ValueError:
            pass
    return value


def write_csv_rows(rows: list[dict], output: io.TextIOBase, delimiter: str = ",") -> None:
    """Write list of dicts as CSV to a stream."""
    if not rows:
        return
    # Collect all keys preserving insertion order
    keys = list(dict.fromkeys(k for row in rows for k in row))
    writer = csv.DictWriter(output, fieldnames=keys, delimiter=delimiter,
                            quoting=csv.QUOTE_MINIMAL, extrasaction="ignore",
                            lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: _serialize_cell(row.get(k, "")) for k in keys})


def _serialize_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)
