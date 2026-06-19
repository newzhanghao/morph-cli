"""Auto-detect input format: JSON, CSV, YAML."""
import csv, io, json
from pathlib import Path
from typing import Any

import yaml
from .utils import sniff_csv_dialect, infer_type


def detect_format(file_path: str | None, text: str) -> tuple[str, Any]:
    """Detect format and return (format_name, parsed_data).

    Priority: file extension → content sniffing → try-all fallback.
    """
    # 1. File extension
    if file_path:
        ext = Path(file_path).suffix.lower()
        if ext in (".json",):
            return "json", _parse_json(text)
        if ext in (".csv", ".tsv"):
            return "csv", _parse_csv(text)
        if ext in (".yaml", ".yml"):
            return "yaml", _parse_yaml(text)

    # 2. Content sniffing — try in order of specificity
    s = text.strip()

    if s and s[0] in ("{", "["):
        try:
            return "json", _parse_json(text)
        except ValueError:
            pass

    if s and s[0] not in ("{", "[", ",") and not _looks_like_csv(s):
        try:
            return "yaml", _parse_yaml(text)
        except (yaml.YAMLError, ValueError):
            pass

    try:
        return "csv", _parse_csv(text)
    except (csv.Error, ValueError):
        pass

    # 3. Last resort: try all parsers in order
    for name, parser in (("json", _parse_json), ("csv", _parse_csv), ("yaml", _parse_yaml)):
        try:
            return name, parser(text)
        except (ValueError, csv.Error, yaml.YAMLError):
            continue

    raise ValueError(
        "Unable to detect input format. "
        "Please specify with --from json|csv|yaml, "
        "or ensure the input is valid JSON, CSV, or YAML."
    )


def _parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e


def _parse_csv(text: str) -> list[dict[str, Any]]:
    info = sniff_csv_dialect(text)
    reader = csv.DictReader(io.StringIO(text), delimiter=info["delimiter"])
    rows = []
    for row in reader:
        if not row or all(v.strip() == "" for v in row.values()):
            continue
        rows.append({k.strip(): infer_type(v) for k, v in row.items() if k is not None})
    if not rows:
        raise ValueError("CSV appears to be empty (no data rows found)")
    return rows


def _parse_yaml(text: str) -> Any:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}") from e
    if data is None:
        raise ValueError("YAML appears to be empty")
    return data


def _looks_like_csv(text: str) -> bool:
    """Quick heuristic: does this text look like CSV?"""
    lines = [l for l in text.strip().split("\n") if l.strip()]
    if len(lines) < 2:
        return False
    for delim in (",", "\t", ";"):
        counts = [len(line.split(delim)) for line in lines[:5]]
        if len(set(counts)) == 1 and counts[0] >= 1:
            if counts[0] == 1 and any(": " in line for line in lines[:5]):
                continue
            return True
    return False
