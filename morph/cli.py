"""CLI entry point for morph."""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.syntax import Syntax

from . import __version__
from .converter import convert
from .detector import detect_format
from .utils import detect_encoding

console = Console(highlight=False)
console_err = Console(stderr=True, highlight=False)

FORMAT_CHOICES = ["json", "csv", "yaml"]


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
                "Example: cat data.json | morph convert -t csv"
            )
        enc, text = detect_encoding(None, raw)
        return text, None, enc


def _display_result(output: str, to_fmt: str) -> None:
    """Display converted output with optional syntax highlighting."""
    if to_fmt == "json":
        syntax = Syntax(output, "json", theme="monokai", word_wrap=True)
        console.print(syntax)
    elif to_fmt == "yaml":
        syntax = Syntax(output, "yaml", theme="monokai", word_wrap=True)
        console.print(syntax)
    else:
        # CSV: output raw text to stdout for pipe compatibility
        sys.stdout.write(output)


@click.group()
@click.version_option(version=__version__, prog_name="morph")
def main():
    """morph — A dead-simple data format converter CLI.

    Convert JSON, CSV, and YAML between each other.
    Pipe data in, get converted data out.
    """
    pass


@main.command()
@click.argument("input_file", required=False, default=None)
@click.option(
    "-f", "--from", "from_fmt",
    type=click.Choice(FORMAT_CHOICES),
    help="Input format. Auto-detected if not specified.",
)
@click.option(
    "-t", "--to", "to_fmt",
    type=click.Choice(FORMAT_CHOICES),
    required=True,
    help="Target output format.",
)
@click.option(
    "-o", "--output",
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
        text, file_path, encoding = _read_input(input_file)
    except Exception as e:
        console.print(f"[red]Error reading input:[/red] {e}")
        raise SystemExit(1)

    # 2. Detect / parse format
    if from_fmt:
        # Explicit format — parse directly
        try:
            from .detector import _parse_json, _parse_csv, _parse_yaml
            parsers = {"json": _parse_json, "csv": _parse_csv, "yaml": _parse_yaml}
            data = parsers[from_fmt](text)
        except Exception as e:
            console.print(f"[red]Error parsing {from_fmt.upper()}:[/red] {e}")
            raise SystemExit(1)
    else:
        # Auto-detect
        try:
            detected_fmt, data = detect_format(file_path, text)
            console_err.print(
                f"[dim]Detected input format: {detected_fmt.upper()}[/dim]"
            )
            from_fmt = detected_fmt
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            raise SystemExit(1)

    # Show some info about what we got
    _show_input_summary(data, from_fmt)

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
        _display_result(result, to_fmt)


def _show_input_summary(data, fmt: str) -> None:
    """Print a brief summary of the input data to stderr."""
    if fmt == "csv":
        rows = data if isinstance(data, list) else [data]
        cols = len(rows[0]) if rows else 0
        console_err.print(
            f"[dim]Input: CSV | {len(rows)} rows × {cols} columns[/dim]"
        )
    elif fmt == "json":
        if isinstance(data, list):
            console_err.print(
                f"[dim]Input: JSON array | {len(data)} items[/dim]"
            )
        elif isinstance(data, dict):
            console_err.print(
                f"[dim]Input: JSON object | {len(data)} keys[/dim]"
            )
        else:
            console_err.print(
                f"[dim]Input: JSON | scalar value[/dim]"
            )
    elif fmt == "yaml":
        if isinstance(data, list):
            console_err.print(
                f"[dim]Input: YAML | {len(data)} items[/dim]"
            )
        elif isinstance(data, dict):
            console_err.print(
                f"[dim]Input: YAML | {len(data)} keys[/dim]"
            )
        else:
            console_err.print(
                f"[dim]Input: YAML | scalar value[/dim]"
            )


if __name__ == "__main__":
    main()
