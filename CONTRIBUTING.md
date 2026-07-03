# Contributing

## Local Setup

```bash
python -m pip install -e ".[dev]"
```

## Checks

Run the same checks used by CI:

```bash
ruff check .
ruff format --check .
pytest
agenttelemetry version
python -m build
```

Pull requests should pass all checks before review. Keep changes scoped to one
milestone or one small behavior at a time.
