"""CLI entry point for morph — process data at the speed of thought."""
import random, sys
from pathlib import Path
from typing import Any, Optional

import click
from rich.console import Console
from rich.syntax import Syntax

from . import __version__
from .converter import convert
from .detector import detect_format, _parse_json, _parse_csv, _parse_yaml
from .filter_expr import evaluate, UnsafeExpression, EvalError
from .utils import detect_encoding, write_csv_rows

console = Console(highlight=False)
console_err = Console(stderr=True, highlight=False)
FORMAT_CHOICES = ["json", "csv", "yaml", "jsonl"]


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _read_input(file_path: Optional[str]) -> tuple[str, str | None, str]:
    """Read from file or stdin. Returns (text, path_or_None, encoding)."""
    if file_path and file_path != "-":
        p = Path(file_path)
        if not p.exists():
            raise click.BadParameter(f"File not found: {file_path}")
        raw = p.read_bytes()
        enc, text = detect_encoding(str(p), raw)
        return text, str(p), enc
    raw = sys.stdin.buffer.read()
    if not raw:
        raise click.UsageError(
            "No input provided. Pipe data to morph or specify a file.\n"
            "Example: cat data.json | morph filter 'age > 18'"
        )
    enc, text = detect_encoding(None, raw)
    return text, None, enc


def _parse_data(text: str, file_path: str | None, from_fmt: str | None, quiet: bool = False) -> tuple[str, Any]:
    """Detect/parse format. Returns (fmt, data)."""
    if from_fmt:
        parsers = {"json": _parse_json, "csv": _parse_csv, "yaml": _parse_yaml}
        try:
            return from_fmt, parsers[from_fmt](text)
        except Exception as e:
            console.print(f"[red]Error parsing {from_fmt.upper()}:[/red] {e}")
            raise SystemExit(1)
    try:
        fmt, data = detect_format(file_path, text)
        if not quiet:
            console_err.print(f"[dim]Detected format: {fmt.upper()}[/dim]")
        return fmt, data
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)


def _get_records(data: Any) -> list[dict]:
    """Normalize data to list of dicts."""
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return [data] if isinstance(data, dict) else []


def _load(input_file: Optional[str], from_fmt: Optional[str]) -> tuple[str, list[dict]]:
    """Read, parse, extract records. Returns (fmt, records)."""
    text, path, _ = _read_input(input_file)
    fmt, data = _parse_data(text, path, from_fmt, quiet=True)
    return fmt, _get_records(data)


def _output_result(result: Any, fmt: str, output_path: Optional[str]) -> None:
    """Serialize and write result to file or stdout."""
    text = _serialize(result, fmt)
    if output_path:
        Path(output_path).write_text(text, encoding="utf-8")
        console.print(f"[green]✓[/green] Written to [bold]{output_path}[/bold]")
    else:
        sys.stdout.write(text)


def _serialize(data: Any, fmt: str, pretty: bool = True) -> str:
    """Serialize data to string. Handles jsonl separately from converter."""
    if fmt == "jsonl":
        import json
        return "\n".join(json.dumps(item, ensure_ascii=False) for item in data) + "\n"
    from .converter import _serialize as _conv_serialize
    return _conv_serialize(data, fmt, pretty, ",")


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(version=__version__, prog_name="morph")
def main():
    """morph — Process data at the speed of thought."""


# ---------------------------------------------------------------------------
# convert
# ---------------------------------------------------------------------------

@main.command()
@click.argument("input_file", required=False, default=None)
@click.option("-f", "--from", "from_fmt", type=click.Choice(FORMAT_CHOICES),
              help="Input format. Auto-detected if not specified.")
@click.option("-t", "--to", "to_fmt", type=click.Choice(FORMAT_CHOICES), required=True,
              help="Target output format.")
@click.option("-o", "--output", type=click.Path(writable=True),
              help="Write output to file instead of stdout.")
@click.option("--pretty/--no-pretty", default=True,
              help="Pretty-print JSON/YAML output (default: on).")
@click.option("--flatten/--no-flatten", default=True,
              help="Flatten nested objects for CSV output (default: on).")
@click.option("--delimiter", default=",", help="CSV delimiter (default: comma).")
def convert_cmd(input_file, from_fmt, to_fmt, output, pretty, flatten, delimiter):
    """Convert data between JSON, CSV, and YAML formats."""
    text, file_path, _ = _read_input(input_file)
    detected_fmt, data = _parse_data(text, file_path, from_fmt)
    if not from_fmt:
        from_fmt = detected_fmt

    try:
        result = convert(data, from_fmt=from_fmt, to_fmt=to_fmt,
                         flatten=flatten, pretty=pretty, csv_delimiter=delimiter)
    except Exception as e:
        console.print(f"[red]Error converting:[/red] {e}")
        raise SystemExit(1)

    if output:
        Path(output).write_text(result, encoding="utf-8")
        console.print(f"[green]✓[/green] Written to [bold]{output}[/bold]")
    elif to_fmt == "csv":
        sys.stdout.write(result)
    else:
        console.print(Syntax(result, to_fmt, theme="monokai", word_wrap=True))


# ---------------------------------------------------------------------------
# Pipeline commands (filter, select, head, tail, sample)
# ---------------------------------------------------------------------------

@main.command()
@click.argument("expression")
@click.argument("input_file", required=False, default=None)
@click.option("-f", "--from", "from_fmt", type=click.Choice(FORMAT_CHOICES),
              help="Input format. Auto-detected.")
@click.option("-o", "--output", type=click.Path(writable=True),
              help="Write output to file.")
def filter_cmd(expression, input_file, from_fmt, output):
    """Filter records using an expression with familiar operators.

    \b
    Operators: ==, !=, <, <=, >, >=, and, or, not, in, not in, . (dot-notation)
    Example: morph filter "age > 18 and status == 'active'"
    """
    import ast
    try:
        ast.parse(expression.strip(), mode="eval")
    except SyntaxError as e:
        console.print(f"[red]Invalid filter expression:[/red] {e}")
        raise SystemExit(1)

    fmt, records = _load(input_file, from_fmt)
    if not records:
        console.print("[yellow]Warning:[/yellow] No records found in input")
        return

    filtered, skipped = [], 0
    for rec in records:
        try:
            if evaluate(expression, rec):
                filtered.append(rec)
        except (UnsafeExpression, EvalError):
            skipped += 1

    if skipped:
        console_err.print(f"[dim]Skipped {skipped} records with evaluation errors[/dim]")
    if not filtered:
        console_err.print("[yellow]No records matched the filter expression[/yellow]")
        return
    _output_result(filtered, fmt, output)


@main.command()
@click.argument("fields")
@click.argument("input_file", required=False, default=None)
@click.option("-f", "--from", "from_fmt", type=click.Choice(FORMAT_CHOICES),
              help="Input format. Auto-detected.")
@click.option("-o", "--output", type=click.Path(writable=True),
              help="Write output to file.")
def select_cmd(fields, input_file, from_fmt, output):
    """Extract specific fields using dot-notation.

    \b
    Example: morph select "name, email, user.address.city" data.json
    """
    field_list = [f.strip() for f in fields.split(",") if f.strip()]
    if not field_list:
        console.print("[red]Error:[/red] No fields specified")
        raise SystemExit(1)

    fmt, records = _load(input_file, from_fmt)
    if not records:
        console.print("[yellow]Warning:[/yellow] No records found in input")
        return

    selected = []
    for rec in records:
        new = {}
        for field in field_list:
            parts = field.split(".")
            val: Any = rec
            for part in parts:
                if isinstance(val, dict) and part in val:
                    val = val[part]
                else:
                    val = None
                    break
            new[field] = val
        selected.append(new)
    _output_result(selected, fmt, output)


@main.command()
@click.argument("n", type=int, default=10)
@click.argument("input_file", required=False, default=None)
@click.option("-f", "--from", "from_fmt", type=click.Choice(FORMAT_CHOICES),
              help="Input format. Auto-detected.")
@click.option("-o", "--output", type=click.Path(writable=True),
              help="Write output to file.")
def head_cmd(n, input_file, from_fmt, output):
    """Show the first N records. Default: 10."""
    fmt, records = _load(input_file, from_fmt)
    if records:
        _output_result(records[:n], fmt, output)


@main.command()
@click.argument("n", type=int, default=10)
@click.argument("input_file", required=False, default=None)
@click.option("-f", "--from", "from_fmt", type=click.Choice(FORMAT_CHOICES),
              help="Input format. Auto-detected.")
@click.option("-o", "--output", type=click.Path(writable=True),
              help="Write output to file.")
def tail_cmd(n, input_file, from_fmt, output):
    """Show the last N records. Default: 10."""
    fmt, records = _load(input_file, from_fmt)
    if records:
        _output_result(records[-n:], fmt, output)


@main.command()
@click.argument("n", type=int, default=100)
@click.argument("input_file", required=False, default=None)
@click.option("-f", "--from", "from_fmt", type=click.Choice(FORMAT_CHOICES),
              help="Input format. Auto-detected.")
@click.option("-o", "--output", type=click.Path(writable=True),
              help="Write output to file.")
def sample_cmd(n, input_file, from_fmt, output):
    """Randomly sample N records from the input."""
    fmt, records = _load(input_file, from_fmt)
    if records:
        n = min(n, len(records))
        _output_result(random.sample(records, n), fmt, output)


if __name__ == "__main__":
    main()
