# AgentTelemetry

AgentTelemetry is a security and observability toolkit for LangGraph agentic
systems. The first milestone provides the project skeleton, CLI, core Pydantic
schemas, a JSONL trace writer, and a basic test suite.

## Milestone 1

Implemented:

- Python package scaffold under `src/agenttelemetry`.
- Typer CLI with `version` and `init-trace` commands.
- Pydantic models for workflow graphs, runtime traces, findings, and test
  results.
- Runtime trace primitives:
  - `InMemoryTraceCollector`
  - `JsonlTraceWriter`
- Pytest test suite covering models, runtime writer, and CLI basics.

## Development

Install the package with development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

Create a sample JSONL trace:

```bash
agenttelemetry init-trace --workflow-name demo --output runs/trace.jsonl
```
