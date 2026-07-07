from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from time import monotonic
from typing import Any

from agenttelemetry.runtime.entrypoint import Entrypoint

TIMEOUT_EXIT_CODE = 124


@dataclass(frozen=True)
class IsolatedRunResult:
    exit_code: int
    output: dict[str, Any] | None = None
    error: str | None = None
    timed_out: bool = False
    duration_ms: float = 0.0
    forwarded_env: dict[str, str] = field(default_factory=dict)


def run_isolated_entrypoint(
    entrypoint: Entrypoint,
    input_payload: dict[str, Any],
    timeout_seconds: float,
    allow_live_tools: bool = False,
    env: dict[str, str] | None = None,
) -> IsolatedRunResult:
    request = {"entrypoint": entrypoint.raw, "input": input_payload}
    child_env = _build_child_env(env or {}, allow_live_tools)
    started = monotonic()

    try:
        completed = subprocess.run(
            [sys.executable, "-m", "agenttelemetry.runtime.worker"],
            input=json.dumps(request),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
            env=child_env,
        )
    except subprocess.TimeoutExpired:
        return IsolatedRunResult(
            exit_code=TIMEOUT_EXIT_CODE,
            error=f"Entrypoint timed out after {timeout_seconds} seconds.",
            timed_out=True,
            duration_ms=_elapsed_ms(started),
            forwarded_env=_visible_forwarded_env(child_env),
        )

    output = _parse_stdout(completed.stdout)
    error = completed.stderr.strip() or None
    if completed.returncode == 0:
        error = None
    return IsolatedRunResult(
        exit_code=completed.returncode,
        output=output,
        error=error,
        duration_ms=_elapsed_ms(started),
        forwarded_env=_visible_forwarded_env(child_env),
    )


def _build_child_env(
    forwarded_env: dict[str, str], allow_live_tools: bool
) -> dict[str, str]:
    child_env = {
        "AGENTTELEMETRY_LIVE_TOOLS": "1" if allow_live_tools else "0",
    }
    package_src = str(Path(__file__).resolve().parents[2])
    for key in ("PATH", "PYTHONPATH"):
        value = os.environ.get(key)
        if value:
            child_env[key] = value
    child_env["PYTHONPATH"] = (
        f"{package_src}{os.pathsep}{child_env['PYTHONPATH']}"
        if "PYTHONPATH" in child_env
        else package_src
    )
    child_env.update(forwarded_env)
    return child_env


def _visible_forwarded_env(child_env: dict[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in child_env.items()
        if key not in {"PATH", "PYTHONPATH"}
    }


def _parse_stdout(stdout: str) -> dict[str, Any] | None:
    if not stdout.strip():
        return None
    return json.loads(stdout)


def _elapsed_ms(started: float) -> float:
    return round((monotonic() - started) * 1000, 3)
