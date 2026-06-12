"""Core conversion engine: JSON ↔ CSV ↔ YAML with flattening."""

import io
import json
from typing import Any

import yaml


def convert(
    data: Any,
    from_fmt: str,
    to_fmt: str,
    flatten: bool = True,
    pretty: bool = False,
    csv_delimiter: str = ",",
) -> str:
    """Convert data between formats.

    Args:
        data: Parsed input data.
        from_fmt: Source format ("json", "csv", "yaml").
        to_fmt: Target format ("json", "csv", "yaml").
        flatten: Flatten nested JSON/YAML when converting to CSV.
        pretty: Pretty-print JSON/YAML output.
        csv_delimiter: CSV delimiter character.

    Returns:
        Converted output as a string.
    """
    if from_fmt == to_fmt:
        return _serialize(data, to_fmt, pretty, csv_delimiter)

    # Route through the conversion paths
    if from_fmt == "json" and to_fmt == "csv":
        result = _json_to_csv(data, flatten)
        return _to_csv_string(result, csv_delimiter)

    elif from_fmt == "json" and to_fmt == "yaml":
        return _to_yaml_string(data)

    elif from_fmt == "csv" and to_fmt == "json":
        return _to_json_string(data, pretty)

    elif from_fmt == "csv" and to_fmt == "yaml":
        return _to_yaml_string(data)

    elif from_fmt == "yaml" and to_fmt == "json":
        return _to_json_string(data, pretty)

    elif from_fmt == "yaml" and to_fmt == "csv":
        result = _yaml_to_csv(data, flatten)
        return _to_csv_string(result, csv_delimiter)

    else:
        raise ValueError(f"Unsupported conversion: {from_fmt} → {to_fmt}")


# ---------------------------------------------------------------------------
# JSON → CSV
# ---------------------------------------------------------------------------

def _json_to_csv(data: Any, flatten: bool) -> list[dict[str, Any]]:
    """Convert parsed JSON data to a list of flat dicts (CSV-ready rows)."""
    rows = _normalize_to_rows(data)
    if flatten:
        rows = [flatten_dict(r) for r in rows]
    return rows


def _normalize_to_rows(data: Any) -> list[dict[str, Any]]:
    """Normalize parsed data into a list of dicts."""
    if isinstance(data, list):
        # Top-level array
        rows = []
        for item in data:
            if isinstance(item, dict):
                rows.append(item)
            else:
                rows.append({"value": item})
        return rows
    elif isinstance(data, dict):
        return [data]
    else:
        return [{"value": data}]


# ---------------------------------------------------------------------------
# YAML → CSV
# ---------------------------------------------------------------------------

def _yaml_to_csv(data: Any, flatten: bool) -> list[dict[str, Any]]:
    """YAML data is parsed identically to JSON by PyYAML, reuse the logic."""
    return _json_to_csv(data, flatten)


# ---------------------------------------------------------------------------
# Flattening
# ---------------------------------------------------------------------------

def flatten_dict(
    d: dict[str, Any],
    parent_key: str = "",
    sep: str = "_",
) -> dict[str, Any]:
    """Flatten a nested dict into a single-level dict.

    Examples:
        {"a": {"b": 1, "c": 2}}  →  {"a_b": 1, "a_c": 2}
        {"items": [1, 2, 3]}     →  {"items_0": 1, "items_1": 2, "items_2": 3}
        {"items": [{"x": 1}]}    →  {"items_0_x": 1}
    """
    items: dict[str, Any] = {}
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else str(k)

        if isinstance(v, dict):
            items.update(flatten_dict(v, new_key, sep))
        elif isinstance(v, list):
            if not v:
                items[new_key] = ""
            elif all(isinstance(i, dict) for i in v):
                # Array of objects: flatten each with index
                for idx, obj in enumerate(v):
                    items.update(flatten_dict(obj, f"{new_key}{sep}{idx}", sep))
            else:
                # Array of primitives: index each value
                for idx, val in enumerate(v):
                    if isinstance(val, (dict, list)):
                        items[f"{new_key}{sep}{idx}"] = json.dumps(
                            val, ensure_ascii=False
                        )
                    else:
                        items[f"{new_key}{sep}{idx}"] = val
        else:
            items[new_key] = v

    return items


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def _serialize(
    data: Any, fmt: str, pretty: bool, delimiter: str
) -> str:
    """Serialize data back to string in the given format."""
    if fmt == "json":
        return _to_json_string(data, pretty)
    elif fmt == "yaml":
        return _to_yaml_string(data)
    elif fmt == "csv":
        return _to_csv_string(data, delimiter)
    else:
        raise ValueError(f"Unknown format: {fmt}")


def _to_json_string(data: Any, pretty: bool) -> str:
    indent = 2 if pretty else None
    return json.dumps(data, indent=indent, ensure_ascii=False)


def _to_yaml_string(data: Any) -> str:
    return yaml.dump(
        data,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=4096,  # prevent automatic line-wrapping of long values
    )


def _to_csv_string(rows: list[dict[str, Any]], delimiter: str) -> str:
    """Convert list of dicts to CSV string."""
    from .utils import write_csv_rows

    buf = io.StringIO()
    write_csv_rows(rows, buf, delimiter)
    return buf.getvalue()
