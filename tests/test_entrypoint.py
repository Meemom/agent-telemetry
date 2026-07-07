from pathlib import Path

import pytest

from agenttelemetry.runtime import (
    EntrypointError,
    load_entrypoint_object,
    parse_entrypoint,
)


def test_parse_entrypoint_accepts_file_and_symbol(tmp_path: Path) -> None:
    app_file = tmp_path / "app.py"
    app_file.write_text("graph = object()\n", encoding="utf-8")

    entrypoint = parse_entrypoint(f"{app_file}:graph")

    assert entrypoint.file_path == app_file.resolve()
    assert entrypoint.symbol == "graph"


def test_parse_entrypoint_rejects_missing_separator() -> None:
    with pytest.raises(EntrypointError, match="file.py:symbol"):
        parse_entrypoint("app.py")


def test_parse_entrypoint_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(EntrypointError, match="does not exist"):
        parse_entrypoint(f"{tmp_path / 'missing.py'}:graph")


def test_load_entrypoint_object_rejects_missing_symbol(tmp_path: Path) -> None:
    app_file = tmp_path / "app.py"
    app_file.write_text("other = object()\n", encoding="utf-8")
    entrypoint = parse_entrypoint(f"{app_file}:graph")

    with pytest.raises(EntrypointError, match="symbol not found"):
        load_entrypoint_object(entrypoint)
