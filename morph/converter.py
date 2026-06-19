"""Format conversion: JSON ↔ CSV ↔ YAML."""
import io, json
from typing import Any

import yaml
from .utils import write_csv_rows


def convert(
    data: Any, from_fmt: str, to_fmt: str, *,
    flatten: bool = True, pretty: bool = False, csv_delimiter: str = ",",
) -> str:
    """Convert parsed data between formats."""
    if from_fmt == to_fmt:
        return _serialize(data, to_fmt, pretty, csv_delimiter)

    if from_fmt == "json":
        if to_fmt == "csv":
            rows = _normalize_to_rows(data)
            out = [flatten_dict(r) for r in rows] if flatten else rows
            return _to_csv_string(out, csv_delimiter)
        return _to_yaml_string(data) if to_fmt == "yaml" else _to_json_string(data, pretty)

    if from_fmt in ("csv", "yaml"):
        if to_fmt == "json":
            return _to_json_string(data, pretty)
        if to_fmt == "yaml":
            return _to_yaml_string(data)
        if to_fmt == "csv":
            rows = _normalize_to_rows(data)
            out = [flatten_dict(r) for r in rows] if flatten else rows
            return _to_csv_string(out, csv_delimiter)

    raise ValueError(f"Unsupported conversion: {from_fmt} → {to_fmt}")


def _normalize_to_rows(data: Any) -> list[dict[str, Any]]:
    """Normalize data into a list of dicts."""
    if isinstance(data, list):
        return [r if isinstance(r, dict) else {"value": r} for r in data]
    return [data] if isinstance(data, dict) else [{"value": data}]


def flatten_dict(
    d: dict[str, Any], parent_key: str = "", sep: str = "_",
) -> dict[str, Any]:
    """Flatten nested dict to a single level."""
    items: dict[str, Any] = {}
    for k, v in d.items():
        nk = f"{parent_key}{sep}{k}" if parent_key else str(k)
        if isinstance(v, dict):
            items.update(flatten_dict(v, nk, sep))
        elif isinstance(v, list):
            if not v:
                items[nk] = ""
            elif all(isinstance(i, dict) for i in v):
                for idx, obj in enumerate(v):
                    items.update(flatten_dict(obj, f"{nk}{sep}{idx}", sep))
            else:
                for idx, val in enumerate(v):
                    items[f"{nk}{sep}{idx}"] = (
                        json.dumps(val, ensure_ascii=False)
                        if isinstance(val, (dict, list))
                        else val
                    )
        else:
            items[nk] = v
    return items


def _serialize(data: Any, fmt: str, pretty: bool, delimiter: str) -> str:
    if fmt == "json":
        return _to_json_string(data, pretty)
    if fmt == "yaml":
        return _to_yaml_string(data)
    if fmt == "csv":
        return _to_csv_string(data, delimiter)
    raise ValueError(f"Unknown format: {fmt}")


def _to_json_string(data: Any, pretty: bool = False) -> str:
    return json.dumps(data, indent=2 if pretty else None, ensure_ascii=False)


def _to_yaml_string(data: Any) -> str:
    return yaml.dump(data, allow_unicode=True, sort_keys=False,
                     default_flow_style=False, width=4096)


def _to_csv_string(rows: list[dict[str, Any]], delimiter: str = ",") -> str:
    buf = io.StringIO()
    write_csv_rows(rows, buf, delimiter)
    return buf.getvalue()
