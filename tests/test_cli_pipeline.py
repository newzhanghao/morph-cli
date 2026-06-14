"""Tests for morph.cli — pipeline commands (filter, select, head, etc.).

Pipeline commands suppress stderr status messages (quiet mode),
so CliRunner output is clean JSON/YAML.
"""

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


class TestFilter:
    """CLI tests for the filter command."""

    def test_filter_simple(self, runner):
        data = json.dumps([
            {"name": "Alice", "age": 25},
            {"name": "Bob", "age": 17},
            {"name": "Charlie", "age": 30},
        ])
        result = runner.invoke(
            main,
            ["filter", "age >= 18"],
            input=data,
        )
        assert result.exit_code == 0
        # Should output filtered JSON
        output = json.loads(result.output)
        assert len(output) == 2
        assert output[0]["name"] == "Alice"
        assert output[1]["name"] == "Charlie"

    def test_filter_file(self, runner, tmp_path):
        f = tmp_path / "data.json"
        data = [{"name": "Alice", "age": 25}, {"name": "Bob", "age": 17}]
        f.write_text(json.dumps(data))
        result = runner.invoke(main, ["filter", "age > 18", str(f)])
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        assert output[0]["name"] == "Alice"

    def test_filter_dot_notation(self, runner):
        data = json.dumps([
            {"user": {"name": "Alice", "address": {"city": "NYC"}}},
            {"user": {"name": "Bob", "address": {"city": "LA"}}},
        ])
        result = runner.invoke(
            main,
            ["filter", "user.address.city == 'NYC'"],
            input=data,
        )
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        assert output[0]["user"]["name"] == "Alice"

    def test_filter_no_match(self, runner):
        data = json.dumps([{"name": "Alice", "age": 25}])
        result = runner.invoke(
            main,
            ["filter", "age > 100"],
            input=data,
        )
        assert result.exit_code == 0
        assert "No records matched" in result.output

    def test_filter_yaml_input(self, runner, tmp_path):
        f = tmp_path / "data.yaml"
        data = [{"name": "Alice", "age": 25}, {"name": "Bob", "age": 17}]
        f.write_text(yaml.dump(data))
        result = runner.invoke(main, ["filter", "age >= 18", str(f)])
        assert result.exit_code == 0
        output = yaml.safe_load(result.output)
        assert len(output) == 1
        assert output[0]["name"] == "Alice"

    def test_filter_invalid_expression(self, runner):
        result = runner.invoke(
            main,
            ["filter", "age >>> 18"],
            input="[{}]",
        )
        assert result.exit_code != 0
        assert "Invalid" in result.output or "Error" in result.output

    def test_filter_no_input(self, runner):
        result = runner.invoke(main, ["filter", "age > 18"])
        assert result.exit_code != 0
        assert "No input" in result.output or "Error" in result.output


class TestSelect:
    """CLI tests for the select command."""

    def test_select_simple_fields(self, runner):
        data = json.dumps([
            {"name": "Alice", "email": "alice@example.com", "age": 25},
            {"name": "Bob", "email": "bob@example.com", "age": 30},
        ])
        result = runner.invoke(main, ["select", "name, email"], input=data)
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 2
        assert "name" in output[0]
        assert "email" in output[0]
        assert "age" not in output[0]

    def test_select_nested_fields(self, runner):
        data = json.dumps([
            {"user": {"name": "Alice", "address": {"city": "NYC"}}},
        ])
        result = runner.invoke(main, ["select", "user.name, user.address.city"], input=data)
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output[0]["user.name"] == "Alice"
        assert output[0]["user.address.city"] == "NYC"

    def test_select_missing_field(self, runner):
        data = json.dumps([{"name": "Alice"}])
        result = runner.invoke(main, ["select", "name, email"], input=data)
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output[0]["name"] == "Alice"
        assert output[0]["email"] is None

    def test_select_empty_fields(self, runner):
        result = runner.invoke(main, ["select", ""], input="[{}]")
        assert result.exit_code != 0


class TestHead:
    """CLI tests for the head command."""

    def test_head_default(self, runner):
        data = json.dumps([{"id": i} for i in range(100)])
        result = runner.invoke(main, ["head"], input=data)
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 10  # default N

    def test_head_n(self, runner):
        data = json.dumps([{"id": i} for i in range(100)])
        result = runner.invoke(main, ["head", "5"], input=data)
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 5

    def test_head_more_than_available(self, runner):
        data = json.dumps([{"id": i} for i in range(3)])
        result = runner.invoke(main, ["head", "10"], input=data)
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 3


class TestTail:
    """CLI tests for the tail command."""

    def test_tail_default(self, runner):
        data = json.dumps([{"id": i} for i in range(100)])
        result = runner.invoke(main, ["tail"], input=data)
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 10
        assert output[0]["id"] == 90

    def test_tail_n(self, runner):
        data = json.dumps([{"id": i} for i in range(100)])
        result = runner.invoke(main, ["tail", "3"], input=data)
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 3
        assert output[0]["id"] == 97

    def test_tail_file(self, runner, tmp_path):
        f = tmp_path / "data.json"
        data = [{"id": i} for i in range(10)]
        f.write_text(json.dumps(data))
        result = runner.invoke(main, ["tail", "3", str(f)])
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output[0]["id"] == 7
        assert output[-1]["id"] == 9


class TestSample:
    """CLI tests for the sample command."""

    def test_sample_basic(self, runner):
        data = json.dumps([{"id": i} for i in range(100)])
        result = runner.invoke(main, ["sample", "10"], input=data)
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 10

    def test_sample_all_when_n_larger(self, runner):
        data = json.dumps([{"id": i} for i in range(5)])
        result = runner.invoke(main, ["sample", "100"], input=data)
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 5  # can only sample as many as exist


class TestPipeline:
    """End-to-end pipeline tests combining multiple commands."""

    def test_filter_then_select(self, runner):
        data = json.dumps([
            {"name": "Alice", "email": "a@x.com", "age": 25},
            {"name": "Bob", "email": "b@x.com", "age": 17},
            {"name": "Charlie", "email": "c@x.com", "age": 30},
        ])
        # Simulate: morph filter "age >= 18" | morph select "name"
        r1 = runner.invoke(main, ["filter", "age >= 18"], input=data)
        assert r1.exit_code == 0
        r2 = runner.invoke(main, ["select", "name"], input=r1.output)
        assert r2.exit_code == 0
        output = json.loads(r2.output)
        assert len(output) == 2
        assert output[0]["name"] == "Alice"
        assert output[1]["name"] == "Charlie"
        # Should only have "name" key
        assert "email" not in output[0]

    def test_filter_then_convert_csv(self, runner):
        data = json.dumps([
            {"name": "Alice", "age": 25},
            {"name": "Bob", "age": 17},
        ])
        r1 = runner.invoke(main, ["filter", "age >= 18"], input=data)
        assert r1.exit_code == 0
        r2 = runner.invoke(main, ["convert", "-t", "csv"], input=r1.output)
        assert r2.exit_code == 0
        assert "Alice" in r2.output
        assert "Bob" not in r2.output

    def test_head_in_pipeline(self, runner):
        data = json.dumps([{"id": i} for i in range(100)])
        r1 = runner.invoke(main, ["filter", "id >= 50"], input=data)
        assert r1.exit_code == 0
        r2 = runner.invoke(main, ["head", "3"], input=r1.output)
        assert r2.exit_code == 0
        output = json.loads(r2.output)
        assert len(output) == 3
        assert output[0]["id"] == 50
