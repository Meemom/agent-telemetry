# AgentTelemetry

AgentTelemetry is a security and observability toolkit for LangGraph agentic
systems. The first milestone provides the project skeleton, CLI, core Pydantic
schemas, a JSONL trace writer, and a basic test suite.

## Milestones

Milestone 1 implemented:

- Python package scaffold under `src/agenttelemetry`.
- Typer CLI with `version` and `init-trace` commands.
- Pydantic models for workflow graphs, runtime traces, findings, and test
  results.
- Runtime trace primitives:
  - `InMemoryTraceCollector`
  - `JsonlTraceWriter`
- Pytest test suite covering models, runtime writer, and CLI basics.

Milestone 2 implemented:

- Ruff linting and format checks.
- Pytest coverage reporting.
- Package build validation.
- GitHub Actions CI baseline for pushes and pull requests.

## Development

Install the package with development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run the full local check suite:

```bash
ruff check .
ruff format --check .
pytest
agenttelemetry version
python -m build
```

Create a sample JSONL trace:

```bash
agenttelemetry init-trace --workflow-name demo --output runs/trace.jsonl
```

## CI

GitHub Actions runs the Milestone 2 verification suite on pushes and pull
requests:

- install the package with development dependencies
- run `ruff check .`
- run `ruff format --check .`
- run `pytest` with coverage
- run `agenttelemetry version`
- run `python -m build`
