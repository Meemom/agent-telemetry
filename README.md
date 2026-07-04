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

Milestone 3 implemented:

- Safe `customer_support` LangGraph fixture under
  `examples/langgraph_apps/customer_support`.
- Simulated `send_email` tool that records attempted actions and always returns
  `sent=false`.
- Adversarial test config for the first vertical slice:
  `tool_not_called(send_email)`.
- Integration tests proving the fixture can trigger and avoid the email path.

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

Run the customer support fixture directly:

```bash
python examples/langgraph_apps/customer_support/app.py
```

Run the fixture integration test:

```bash
pytest tests/integration/test_customer_support_fixture.py
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
