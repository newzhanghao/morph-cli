"""Tests for morph.cli — command-line interface."""

import json

import pytest
import yaml
from click.testing import CliRunner

from morph.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def fixtures_dir():
    from pathlib import Path
    return Path(__file__).parent / "fixtures"


class TestCLI:
    """End-to-end CLI tests."""

    # --- Basic conversions ---

    def test_json_to_csv_file(self, runner, fixtures_dir):
        f = fixtures_dir / "sample.json"
        result = runner.invoke(main, ["convert", str(f), "-t", "csv"])
        assert result.exit_code == 0
        assert "name,email,score" in result.output
        assert "Alice" in result.output

    def test_csv_to_json_file(self, runner, fixtures_dir):
        f = fixtures_dir / "sample.csv"
        result = runner.invoke(main, ["convert", str(f), "-t", "json"])
        assert result.exit_code == 0
        # In CliRunner, stdout and stderr are mixed in result.output.
        # Find the JSON array by looking for the first "["
        # or just verify the output contains the expected keys.
        assert "Alice" in result.output
        assert "Bob" in result.output

    def test_yaml_to_json_file(self, runner, fixtures_dir):
        f = fixtures_dir / "sample.yaml"
        result = runner.invoke(main, ["convert", str(f), "-t", "json"])
        assert result.exit_code == 0

    # --- Piped / stdin input ---

    def test_stdin_json(self, runner):
        result = runner.invoke(
            main,
            ["convert", "-t", "csv"],
            input='{"name":"Alice","age":30}',
        )
        assert result.exit_code == 0
        assert "name,age" in result.output
        assert "Alice,30" in result.output

    def test_stdin_csv(self, runner):
        result = runner.invoke(
            main,
            ["convert", "-t", "json"],
            input="a,b\n1,2\n3,4",
        )
        assert result.exit_code == 0

    # --- Explicit format ---

    def test_explicit_format_flag(self, runner):
        result = runner.invoke(
            main,
            ["convert", "-f", "json", "-t", "csv"],
            input='{"x": 1}',
        )
        assert result.exit_code == 0

    # --- Output to file ---

    def test_output_to_file(self, runner, fixtures_dir, tmp_path):
        f = fixtures_dir / "sample.json"
        out = tmp_path / "out.csv"
        result = runner.invoke(
            main, ["convert", str(f), "-t", "csv", "-o", str(out)]
        )
        assert result.exit_code == 0
        assert out.exists()
        content = out.read_text()
        assert "name" in content

    # --- Pretty / no-pretty ---

    def test_pretty_json(self, runner):
        result = runner.invoke(
            main,
            ["convert", "-t", "json", "--pretty"],
            input="a,b\n1,2",
        )
        assert result.exit_code == 0
        # Pretty output should have indentation
        assert "  " in result.output or "\n  " in result.output

    # --- Flatten / no-flatten ---

    def test_no_flatten(self, runner):
        result = runner.invoke(
            main,
            ["convert", "-t", "csv", "--no-flatten"],
            input='{"user":{"name":"Alice"}}',
        )
        assert result.exit_code == 0
        # Without flatten, "user" should appear as a column (containing JSON string)
        assert "user" in result.output

    def test_flatten_default(self, runner):
        result = runner.invoke(
            main,
            ["convert", "-t", "csv"],
            input='{"user":{"name":"Alice"}}',
        )
        assert result.exit_code == 0
        assert "user_name" in result.output

    # --- Version and help ---

    def test_version(self, runner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_convert_help(self, runner):
        result = runner.invoke(main, ["convert", "--help"])
        assert result.exit_code == 0
        assert "--to" in result.output
        assert "--from" in result.output

    # --- Error cases ---

    def test_file_not_found(self, runner):
        result = runner.invoke(main, ["convert", "/nonexistent/file.json", "-t", "csv"])
        assert result.exit_code != 0

    def test_missing_to_flag(self, runner):
        result = runner.invoke(main, ["convert"])
        assert result.exit_code != 0

    def test_invalid_format(self, runner):
        result = runner.invoke(
            main,
            ["convert", "-t", "xml"],
            input="{}",
        )
        assert result.exit_code != 0

    def test_no_input(self, runner):
        result = runner.invoke(main, ["convert", "-t", "json"])
        assert result.exit_code != 0

    # --- Edge cases ---

    def test_nested_json_flatten_to_csv(self, runner, fixtures_dir):
        f = fixtures_dir / "nested.json"
        result = runner.invoke(main, ["convert", str(f), "-t", "csv"])
        assert result.exit_code == 0
        # Should have flattened columns
        assert "user_name" in result.output
        assert "user_address_city" in result.output
        assert "user_scores_0" in result.output

    def test_empty_csv_graceful(self, runner):
        result = runner.invoke(
            main,
            ["convert", "-f", "csv", "-t", "json"],
            input="col1,col2\n",  # header only, no data
        )
        # Should fail gracefully — no data rows
        assert result.exit_code != 0

    def test_delimiter_option(self, runner):
        result = runner.invoke(
            main,
            ["convert", "-t", "csv", "--delimiter", ";"],
            input='[{"a":1,"b":2}]',
        )
        assert result.exit_code == 0
        assert "a;b" in result.output
