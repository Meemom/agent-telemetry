# Contributing

## Local Setup

```bash
python -m pip install -e ".[dev]"
```

## Checks

Run the same core checks used by CI:

```bash
pytest
agenttelemetry version
```

Milestone 1 keeps CI intentionally small. Linting, formatting checks, coverage,
and package build validation are planned for the CI/CD baseline milestone.

