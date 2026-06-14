"""CLI entry point for morph — process data at the speed of thought."""

import random
import sys
from pathlib import Path
from typing import Any, Optional

import click
from rich.console import Console
from rich.syntax import Syntax

from . import __version__
from .converter import convert
from .detector import detect_format
from .filter_expr import evaluate, UnsafeExpression, EvalError
from .utils import detect_encoding

console = Console(highlight=False)
console_err = Console(stderr=True, highlight=False)

FORMAT_CHOICES = ["json", "csv", "yaml", "jsonl"]


# ---------------------------------------------------------------------------
# Shared I/O helpers — used by all commands
# ---------------------------------------------------------------------------


def _read_input(file_path: Optional[str]) -> tuple[str, str | None, str]:
    """Read input from a file path, stdin, or pipe.

    Returns (text, file_path_to_use, encoding).
    """
    if file_path and file_path != "-":
        path = Path(file_path)
        if not path.exists():
            raise click.BadParameter(f"File not found: {file_path}")
        raw = path.read_bytes()
        enc, text = detect_encoding(str(path), raw)
        return text, str(path), enc
    else:
        # Read from stdin (handle pipe or redirect)
        raw = sys.stdin.buffer.read()
        if not raw:
            raise click.UsageError(
                "No input provided. Pipe data to morph or specify a file.\n"
                "Example: cat data.json | morph filter 'age > 18'"
            )
        enc, text = detect_encoding(None, raw)
        return text, None, enc


def _parse_data(text: str, file_path: str | None, from_fmt: str | None, quiet: bool = False) -> tuple[str, Any]:
    """Detect/parse input format and return (format_name, parsed_data)."""
    if from_fmt:
        from .detector import _parse_json, _parse_csv, _parse_yaml

        parsers = {"json": _parse_json, "csv": _parse_csv, "yaml": _parse_yaml}
        try:
            data = parsers[from_fmt](text)
        except Exception as e:
            console.print(f"[red]Error parsing {from_fmt.upper()}:[/red] {e}")
            raise SystemExit(1)
        return from_fmt, data
    else:
        try:
            detected_fmt, data = detect_format(file_path, text)
            if not quiet:
                console_err.print(f"[dim]Detected format: {detected_fmt.upper()}[/dim]")
            return detected_fmt, data
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            raise SystemExit(1)


def _get_records(data: Any) -> list[dict]:
    """Normalize parsed data to a list of dicts for pipeline processing."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    elif isinstance(data, dict):
        return [data]
    else:
        return []


def _serialize(data: Any, fmt: str, pretty: bool = True) -> str:
    """Serialize data back to a string in the given format."""
    import json

    if fmt == "json":
        indent = 2 if pretty else None
        return json.dumps(data, indent=indent, ensure_ascii=False)
    elif fmt == "jsonl":
        return "\n".join(json.dumps(item, ensure_ascii=False) for item in data) + "\n"
    elif fmt == "yaml":
        import yaml

        return yaml.dump(
            data,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=4096,
        )
    else:
        # CSV — use converter's internal serializer
        from .utils import write_csv_rows

        import io

        buf = io.StringIO()
        rows = data if isinstance(data, list) else [data]
        write_csv_rows(rows, buf, ",")
        return buf.getvalue()


def _output_result(result: Any, fmt: str, output_path: Optional[str]) -> None:
    """Write result to file or display in terminal.

    Pipe commands (filter, select, head, etc.) always write clean text
    to stdout for pipe compatibility. Only the 'convert' command uses
    Rich syntax highlighting (it has its own output logic).
    """
    text = _serialize(result, fmt)

    if output_path:
        Path(output_path).write_text(text, encoding="utf-8")
        console.print(f"[green]✓[/green] Written to [bold]{output_path}[/bold]")
    else:
        sys.stdout.write(text)


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(version=__version__, prog_name="morph")
def main():
    """morph — Process data at the speed of thought.

    Filter, select, sample, and convert JSON / CSV / YAML data.
    Pipe-friendly. Memory-efficient. Zero learning curve.
    """
    pass


# ---------------------------------------------------------------------------
# convert — format conversion (original command)
# ---------------------------------------------------------------------------


@main.command()
@click.argument("input_file", required=False, default=None)
@click.option(
    "-f",
    "--from",
    "from_fmt",
    type=click.Choice(FORMAT_CHOICES),
    help="Input format. Auto-detected if not specified.",
)
@click.option(
    "-t",
    "--to",
    "to_fmt",
    type=click.Choice(FORMAT_CHOICES),
    required=True,
    help="Target output format.",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(writable=True),
    help="Write output to file instead of stdout.",
)
@click.option(
    "--pretty/--no-pretty",
    default=True,
    help="Pretty-print JSON/YAML output (default: on).",
)
@click.option(
    "--flatten/--no-flatten",
    default=True,
    help="Flatten nested objects for CSV output (default: on).",
)
@click.option(
    "--delimiter",
    default=",",
    help="CSV delimiter (default: comma).",
)
def convert_cmd(
    input_file: Optional[str],
    from_fmt: Optional[str],
    to_fmt: str,
    output: Optional[str],
    pretty: bool,
    flatten: bool,
    delimiter: str,
):
    """Convert data between JSON, CSV, and YAML formats.

    Examples:

    \b
        # JSON → CSV (auto-detect input format)
        morph convert data.json -t csv

    \b
        # YAML → JSON (explicit input format)
        morph convert config.yaml -f yaml -t json

    \b
        # Pipe from curl, output to file
        curl https://api.example.com/data | morph convert -t csv -o data.csv

    \b
        # Keep nested JSON as JSON strings in CSV (no flatten)
        morph convert deep.json -t csv --no-flatten
    """
    # 1. Read input
    try:
        text, file_path, _encoding = _read_input(input_file)
    except Exception as e:
        console.print(f"[red]Error reading input:[/red] {e}")
        raise SystemExit(1)

    # 2. Detect / parse
    try:
        detected_fmt, data = _parse_data(text, file_path, from_fmt)
    except SystemExit:
        raise SystemExit(1)

    if not from_fmt:
        from_fmt = detected_fmt

    # 3. Convert
    try:
        result = convert(
            data,
            from_fmt=from_fmt,
            to_fmt=to_fmt,
            flatten=flatten,
            pretty=pretty,
            csv_delimiter=delimiter,
        )
    except Exception as e:
        console.print(f"[red]Error converting:[/red] {e}")
        raise SystemExit(1)

    # 4. Output
    if output:
        Path(output).write_text(result, encoding="utf-8")
        console.print(f"[green]✓[/green] Written to [bold]{output}[/bold]")
    else:
        if to_fmt == "csv":
            sys.stdout.write(result)
        else:
            syntax = Syntax(result, to_fmt, theme="monokai", word_wrap=True)
            console.print(syntax)


# ---------------------------------------------------------------------------
# filter — stream-safe record filtering
# ---------------------------------------------------------------------------


@main.command()
@click.argument("expression")
@click.argument("input_file", required=False, default=None)
@click.option(
    "-f",
    "--from",
    "from_fmt",
    type=click.Choice(FORMAT_CHOICES),
    help="Input format. Auto-detected if not specified.",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(writable=True),
    help="Write output to file instead of stdout.",
)
def filter_cmd(
    expression: str,
    input_file: Optional[str],
    from_fmt: Optional[str],
    output: Optional[str],
):
    """Filter records using an expression with familiar operators.

    \b
    Supported operators:
        ==, !=, <, <=, >, >=   — Comparisons
        and, or, not            — Boolean logic
        in, not in              — Membership checks
        . (dot)                 — Nested field access: user.age
        +, -, *, /              — Arithmetic

    \b
    Examples:
        # Simple comparison
        morph filter "age > 18" data.json

        # Boolean logic with nested fields
        morph filter "user.age >= 21 and status == 'active'" users.json

        # Membership check
        morph filter "'admin' in roles" data.json

        # Pipe from stdin
        cat data.json | morph filter "price * qty > 100" | morph convert -t csv
    """
    # Validate expression syntax first (fail fast)
    try:
        import ast
        ast.parse(expression.strip(), mode="eval")
    except SyntaxError as e:
        console.print(f"[red]Invalid filter expression:[/red] {e}")
        raise SystemExit(1)

    # Read and parse input (quiet mode for pipe compatibility)
    try:
        text, file_path, _ = _read_input(input_file)
        detected_fmt, data = _parse_data(text, file_path, from_fmt, quiet=True)
    except SystemExit:
        raise SystemExit(1)

    # Convert to records and filter
    records = _get_records(data)
    if not records:
        console.print("[yellow]Warning:[/yellow] No records found in input")
        return

    filtered = []
    skipped = 0
    for record in records:
        try:
            if evaluate(expression, record):
                filtered.append(record)
        except (UnsafeExpression, EvalError) as e:
            skipped += 1

    if skipped:
        console_err.print(f"[dim]Skipped {skipped} records with evaluation errors[/dim]")

    if not filtered:
        console_err.print("[yellow]No records matched the filter expression[/yellow]")
        return

    # Output in the detected format
    _output_result(filtered, detected_fmt, output)


# ---------------------------------------------------------------------------
# select — field extraction
# ---------------------------------------------------------------------------


@main.command()
@click.argument("fields")
@click.argument("input_file", required=False, default=None)
@click.option(
    "-f",
    "--from",
    "from_fmt",
    type=click.Choice(FORMAT_CHOICES),
    help="Input format. Auto-detected if not specified.",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(writable=True),
    help="Write output to file instead of stdout.",
)
def select_cmd(
    fields: str,
    input_file: Optional[str],
    from_fmt: Optional[str],
    output: Optional[str],
):
    """Extract specific fields from records using dot-notation.

    \b
    Examples:
        # Select top-level fields
        morph select "name, email" data.json

        # Nested fields with dot-notation
        morph select "id, user.name, user.address.city" data.yaml

        # In a pipeline
        morph filter "age > 18" data.json | morph select "name, email"
    """
    field_list = [f.strip() for f in fields.split(",") if f.strip()]
    if not field_list:
        console.print("[red]Error:[/red] No fields specified")
        raise SystemExit(1)

    try:
        text, file_path, _ = _read_input(input_file)
        detected_fmt, data = _parse_data(text, file_path, from_fmt, quiet=True)
    except SystemExit:
        raise SystemExit(1)

    records = _get_records(data)
    if not records:
        console.print("[yellow]Warning:[/yellow] No records found in input")
        return

    selected = []
    for record in records:
        new_record = {}
        for field in field_list:
            # Resolve dot-notation: "user.name" → record['user']['name']
            parts = field.split(".")
            value = record
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    value = None
                    break
            # Use the last part of the dot-path as the key (flat mode)
            # Or use the full path as key
            new_record[field] = value
        selected.append(new_record)

    _output_result(selected, detected_fmt, output)


# ---------------------------------------------------------------------------
# head — preview first N records
# ---------------------------------------------------------------------------


@main.command()
@click.argument("n", type=int, default=10)
@click.argument("input_file", required=False, default=None)
@click.option(
    "-f",
    "--from",
    "from_fmt",
    type=click.Choice(FORMAT_CHOICES),
    help="Input format. Auto-detected if not specified.",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(writable=True),
    help="Write output to file instead of stdout.",
)
def head_cmd(
    n: int,
    input_file: Optional[str],
    from_fmt: Optional[str],
    output: Optional[str],
):
    """Show the first N records.

    \b
    Examples:
        morph head 10 data.json
        morph head 5 data.csv
        curl api | morph filter "active" | morph head 20
    """
    try:
        text, file_path, _ = _read_input(input_file)
        detected_fmt, data = _parse_data(text, file_path, from_fmt, quiet=True)
    except SystemExit:
        raise SystemExit(1)

    records = _get_records(data)
    if not records:
        return

    _output_result(records[:n], detected_fmt, output)


# ---------------------------------------------------------------------------
# tail — last N records
# ---------------------------------------------------------------------------


@main.command()
@click.argument("n", type=int, default=10)
@click.argument("input_file", required=False, default=None)
@click.option(
    "-f",
    "--from",
    "from_fmt",
    type=click.Choice(FORMAT_CHOICES),
    help="Input format. Auto-detected if not specified.",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(writable=True),
    help="Write output to file instead of stdout.",
)
def tail_cmd(
    n: int,
    input_file: Optional[str],
    from_fmt: Optional[str],
    output: Optional[str],
):
    """Show the last N records.

    \b
    Examples:
        morph tail 10 data.json
        morph tail 5 data.yaml
    """
    try:
        text, file_path, _ = _read_input(input_file)
        detected_fmt, data = _parse_data(text, file_path, from_fmt, quiet=True)
    except SystemExit:
        raise SystemExit(1)

    records = _get_records(data)
    if not records:
        return

    _output_result(records[-n:], detected_fmt, output)


# ---------------------------------------------------------------------------
# sample — random sampling
# ---------------------------------------------------------------------------


@main.command()
@click.argument("n", type=int, default=100)
@click.argument("input_file", required=False, default=None)
@click.option(
    "-f",
    "--from",
    "from_fmt",
    type=click.Choice(FORMAT_CHOICES),
    help="Input format. Auto-detected if not specified.",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(writable=True),
    help="Write output to file instead of stdout.",
)
def sample_cmd(
    n: int,
    input_file: Optional[str],
    from_fmt: Optional[str],
    output: Optional[str],
):
    """Randomly sample N records from the input.

    \b
    Examples:
        # Sample 1000 records from a large file
        morph sample 1000 huge.json > sample.json

        # In a pipeline
        curl api | morph filter "active" | morph sample 50
    """
    try:
        text, file_path, _ = _read_input(input_file)
        detected_fmt, data = _parse_data(text, file_path, from_fmt, quiet=True)
    except SystemExit:
        raise SystemExit(1)

    records = _get_records(data)
    if not records:
        return

    n = min(n, len(records))
    sampled = random.sample(records, n)
    _output_result(sampled, detected_fmt, output)


if __name__ == "__main__":
    main()
