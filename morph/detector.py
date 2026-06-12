"""Auto-detection of input data formats: JSON, CSV, YAML."""

import csv
import io
import json
from pathlib import Path
from typing import Any

import yaml


def detect_format(
    file_path: str | None, text: str
) -> tuple[str, Any]:
    """Detect the format of input data and return (format_name, parsed_data).

    Detection priority:
    1. File extension (if available)
    2. Content sniffing

    Returns:
        ("json", parsed_data) | ("csv", list_of_dicts) | ("yaml", parsed_data)

    Raises:
        ValueError: if format cannot be detected
    """
    # 1. Try file extension first
    if file_path:
        ext = Path(file_path).suffix.lower()
        if ext in (".json",):
            return "json", _parse_json(text)
        if ext in (".csv", ".tsv"):
            return "csv", _parse_csv(text)
        if ext in (".yaml", ".yml"):
            return "yaml", _parse_yaml(text)

    # 2. Content sniffing
    stripped = text.strip()

    # JSON: starts with { or [ and parses successfully
    if stripped and stripped[0] in ("{", "["):
        try:
            return "json", _parse_json(text)
        except ValueError:
            pass

    # YAML: doesn't start with { or [, try yaml parse
    if stripped and stripped[0] not in ("{", "[", ",") and not _looks_like_csv(stripped):
        try:
            return "yaml", _parse_yaml(text)
        except (yaml.YAMLError, ValueError):
            pass

    # CSV: try to parse as CSV
    try:
        return "csv", _parse_csv(text)
    except (csv.Error, ValueError):
        pass

    # If we still can't figure it out, try everything
    for attempt in [
        ("json", _parse_json),
        ("csv", _parse_csv),
        ("yaml", _parse_yaml),
    ]:
        try:
            name, parser = attempt
            return name, parser(text)
        except (ValueError, csv.Error, yaml.YAMLError):
            continue

    raise ValueError(
        "Unable to detect input format. "
        "Please specify with --from json|csv|yaml, "
        "or ensure the input is valid JSON, CSV, or YAML."
    )


def _parse_json(text: str) -> Any:
    """Parse JSON text. Raises ValueError on failure."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e


def _parse_csv(text: str) -> list[dict[str, Any]]:
    """Parse CSV text into a list of dicts. Raises ValueError on failure."""
    from .utils import sniff_csv_dialect, infer_type

    info = sniff_csv_dialect(text)

    reader = csv.DictReader(
        io.StringIO(text), delimiter=info["delimiter"]
    )

    rows = []
    for row in reader:
        if not row or all(v.strip() == "" for v in row.values()):
            continue
        typed_row = {k.strip(): infer_type(v) for k, v in row.items() if k is not None}
        rows.append(typed_row)

    if not rows:
        raise ValueError("CSV appears to be empty (no data rows found)")

    return rows


def _parse_yaml(text: str) -> Any:
    """Parse YAML text. Raises ValueError on failure."""
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
    # Check if first few lines have same number of delimiter-separated fields
    for delim in [",", "\t", ";"]:
        counts = [len(line.split(delim)) for line in lines[:5]]
        if len(set(counts)) == 1 and counts[0] >= 1:
            # Single-column: guard against YAML key:value false positives
            if counts[0] == 1 and any(": " in line for line in lines[:5]):
                continue
            return True
    return False
