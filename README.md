# AgentTelemetry

AgentTelemetry is a local CLI toolkit for testing LangGraph agent workflows for
unsafe tool use. It runs a graph in an isolated subprocess, captures a minimal
runtime trace, evaluates deterministic assertions, and emits evidence-backed
security findings.

Current MVP loop:

```text
LangGraph app -> isolated run -> trace.jsonl -> tests.json -> findings.json -> report
```

## Features

- Explicit LangGraph entrypoint loading with `file.py:graph`.
- Subprocess execution with timeout handling.
- Live tool side effects disabled by default through
  `AGENTTELEMETRY_LIVE_TOOLS=0`.
- JSONL runtime trace with span-style `trace_id`, `span_id`, parent span, timing,
  attributes, and tool-call events.
- Payload capture modes: `none`, `summary`, `full`.
- Redaction modes: `strict`, `metadata`, `off`.
  - `strict` and `metadata` redact emails, SSN-like values, API-key-like
    tokens, and Luhn-valid credit-card-like numbers before trace writes.
- Deterministic assertions:
  - `tool_called`
  - `tool_not_called`
  - `regex_matches`
  - `regex_not_matches`
  - `node_reached`
  - `node_not_reached`
  - `error_absent`
  - `max_tool_calls`
- Built-in `send_email` risk mapping to create high-severity findings from
  failed runtime assertions.
- Best-effort static context for LangGraph fixtures via AST parsing.
- Stable artifacts: `manifest.json`, `output.json`, `trace.jsonl`,
  `tests.json`, `findings.json`, `report.json`, `report.html`.
- CI command with severity-threshold exit behavior.

## Tech Stack

- Python 3.11+
- Typer CLI
- Pydantic schemas
- PyYAML test config loading
- Rich terminal output
- LangGraph fixture support
- JSONL trace storage
- Pytest and pytest-cov
- Ruff linting and formatting
- Hatchling package build
- GitHub Actions CI

## Install

```bash
python -m pip install -e ".[dev]"
```

## Usage

Print the CLI version:

```bash
agenttelemetry version
```

Create a basic trace event:

```bash
agenttelemetry init-trace --workflow-name demo --output runs/trace.jsonl
```

Run a LangGraph app in the isolated runner:

```bash
agenttelemetry observe \
  examples/langgraph_apps/customer_support/app.py:graph \
  --input examples/langgraph_apps/customer_support/input.json \
  --out-dir runs/customer-support
```

Run deterministic adversarial tests:

```bash
agenttelemetry test \
  examples/langgraph_apps/customer_support/app.py:graph \
  --config examples/langgraph_apps/customer_support/tests.yaml \
  --out-dir runs/customer-support
```

Expected fixture result: exit code `1`, because the adversarial test triggers a
simulated `send_email` attempt and fails `tool_not_called(send_email)`.

Run the CI security loop and write reports:

```bash
agenttelemetry ci \
  examples/langgraph_apps/customer_support/app.py:graph \
  --config examples/langgraph_apps/customer_support/tests.yaml \
  --out-dir runs/customer-support \
  --severity-threshold high
```

## Artifacts

`agenttelemetry observe` writes:

```text
runs/customer-support/
  manifest.json
  output.json
  trace.jsonl
```

`agenttelemetry test` writes:

```text
runs/customer-support/
  manifest.json
  output.json
  trace.jsonl
  tests.json
  findings.json
```

`agenttelemetry ci` writes:

```text
runs/customer-support/
  manifest.json
  static.json
  output.json
  trace.jsonl
  tests.json
  findings.json
  report.json
  report.html
```

`static.json` is best-effort context. It records the entrypoint, exported
symbol, detected fixture nodes, edges, and local tools when they are visible
from source without executing user code.

## Fixture

The included fixture is:

```text
examples/langgraph_apps/customer_support/
```

It exports `app.py:graph` and uses a simulated `send_email` tool that records
attempted actions instead of sending email.

## Development

Run local checks:

```bash
ruff check .
ruff format --check .
pytest
agenttelemetry version
python -m build
```

Generated run artifacts are written under `runs/` and are not part of source
control.

## Documentation

Milestone implementation reports are stored in `docs/`.
