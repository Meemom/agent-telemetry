from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any


class EntrypointError(ValueError):
    """Raised when an entrypoint cannot be parsed or loaded."""


@dataclass(frozen=True)
class Entrypoint:
    file_path: Path
    symbol: str

    @property
    def raw(self) -> str:
        return f"{self.file_path}:{self.symbol}"


def parse_entrypoint(value: str) -> Entrypoint:
    file_part, separator, symbol = value.partition(":")
    if not separator:
        raise EntrypointError("Entrypoint must use the form file.py:symbol.")
    if not file_part.strip():
        raise EntrypointError("Entrypoint file path cannot be empty.")
    if not symbol.strip():
        raise EntrypointError("Entrypoint symbol cannot be empty.")

    file_path = Path(file_part).expanduser().resolve()
    if not file_path.exists():
        raise EntrypointError(f"Entrypoint file does not exist: {file_path}")
    if not file_path.is_file():
        raise EntrypointError(f"Entrypoint path is not a file: {file_path}")

    return Entrypoint(file_path=file_path, symbol=symbol.strip())


def load_entrypoint_object(entrypoint: Entrypoint) -> Any:
    module = _load_module(entrypoint.file_path)
    target: Any = module
    for part in entrypoint.symbol.split("."):
        if not part:
            raise EntrypointError("Entrypoint symbol contains an empty segment.")
        if not hasattr(target, part):
            raise EntrypointError(f"Entrypoint symbol not found: {entrypoint.symbol}")
        target = getattr(target, part)
    return target


def _load_module(file_path: Path) -> ModuleType:
    module_name = f"agenttelemetry_user_graph_{file_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise EntrypointError(f"Could not load entrypoint module: {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(file_path.parent))
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # pragma: no cover - surfaced through worker tests.
        raise EntrypointError(f"Entrypoint module failed to import: {exc}") from exc
    finally:
        sys.path.remove(str(file_path.parent))
    return module
