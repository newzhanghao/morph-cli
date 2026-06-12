# morph — A dead-simple data format converter CLI

[![PyPI version](https://img.shields.io/pypi/v/morph-cli.svg)](https://pypi.org/project/morph-cli/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

**One command. Three formats. Zero learning curve.**

`morph` converts JSON, CSV, and YAML between each other. Pipe data in, get converted data out. No jq syntax. No online tools. No privacy concerns.

---

## Why morph?

| Feature | jq | csvkit | yq | **morph** |
|---------|-----|--------|----|-----------|
| JSON → CSV nested flattening | ❌ Manual expression | — | — | ✅ **Auto** |
| Auto format detection | ❌ | ❌ | ❌ | ✅ |
| YAML ↔ JSON | ❌ | ❌ | ✅ | ✅ |
| Pipe-friendly | ❌ | ✅ | ✅ | ✅ |
| Terminal syntax highlighting | ❌ | ❌ | ❌ | ✅ |
| Zero learning cost | ❌ Need jq syntax | ❌ | ❌ | ✅ |

---

## Quick Start

```bash
# Install
pip install morph-cli

# JSON → CSV (with auto nested flattening)
morph convert data.json -t csv

# CSV → JSON (with smart type inference)
morph convert data.csv -t json

# YAML → JSON
morph convert config.yaml -t json

# Pipe from curl
curl https://api.example.com/data | morph convert -t csv -o output.csv
```

---

## Installation

```bash
pip install morph-cli
```

Requires Python 3.9+.

---

## Usage

```
morph convert [INPUT] -t json|csv|yaml [OPTIONS]
```

### Options

| Option | Description |
|--------|-------------|
| `INPUT` | File path (optional, defaults to stdin) |
| `-t, --to` | Target format: `json`, `csv`, or `yaml` **(required)** |
| `-f, --from` | Input format. Auto-detected if omitted |
| `-o, --output` | Write output to file instead of stdout |
| `--pretty / --no-pretty` | Pretty-print JSON/YAML output (default: on) |
| `--flatten / --no-flatten` | Flatten nested objects for CSV output (default: on) |
| `--delimiter` | CSV delimiter character (default: comma) |

### Examples

```bash
# JSON → CSV: nested objects automatically flattened
$ echo '{"user":{"name":"Alice","address":{"city":"NYC"}}}' | morph convert -t csv
user_name,user_address_city
Alice,NYC

# YAML → JSON: auto-detect input format
$ morph convert config.yaml -t json

# CSV → YAML: with type inference (numbers stay numbers)
$ morph convert data.csv -t yaml

# Output to file
$ morph convert data.json -t csv -o output.csv

# Keep nested JSON as raw string in CSV
$ morph convert deep.json -t csv --no-flatten

# Custom CSV delimiter
$ morph convert data.json -t csv --delimiter ";"
```

### Nested JSON → CSV Flattening

```bash
$ cat nested.json
{"user": {"name": "Alice", "address": {"city": "NYC"}, "scores": [85, 92]}}

$ morph convert nested.json -t csv
user_name,user_address_city,user_scores_0,user_scores_1
Alice,NYC,85,92
```

- Nested objects: `user.address.city` → `user_address_city`
- Arrays of primitives: `[85, 92]` → `scores_0`, `scores_1`
- Arrays of objects: each flattened with index (e.g. `items_0_name`)

---

## Supported Formats

| From \ To | JSON | CSV | YAML |
|-----------|------|-----|------|
| **JSON** | — | ✅ | ✅ |
| **CSV** | ✅ | — | ✅ |
| **YAML** | ✅ | ✅ | — |

---

## Roadmap

- [ ] `morph merge` — Multi-file merge with column alignment
- [ ] `morph preview` — Rich table preview in terminal
- [ ] `morph filter` — Simple row filtering & column selection
- [ ] XML / TOML support

---

## FAQ

**Q: Does morph send my data to a server?**
A: No. All processing is local. No network calls. No telemetry.

**Q: Can I use it in CI/CD pipelines?**
A: Yes. `pip install morph-cli` and pipe away.

**Q: What about large files?**
A: For moderate files (<100MB), morph works fine. Streaming support for larger files is on the roadmap.

---

## License

MIT
