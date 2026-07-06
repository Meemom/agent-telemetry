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

Run the Milestone 3 fixture test directly:

```bash
pytest tests/integration/test_customer_support_fixture.py
```

Pull requests should pass all checks before review. Keep changes scoped to one
milestone or one small behavior at a time.
