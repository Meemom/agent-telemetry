import json
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from agenttelemetry.model import RunManifest, RuntimeEvent, RuntimeEventType, TraceRun
from agenttelemetry.model.trace import utc_now
from agenttelemetry.runtime import (
    EntrypointError,
    JsonlTraceWriter,
    parse_entrypoint,
    run_isolated_entrypoint,
)
from agenttelemetry.runtime.trace_capture import (
    PayloadMode,
    RedactionMode,
    build_minimal_trace,
)

app = typer.Typer(
    name="agenttelemetry",
    help="Security and observability toolkit for LangGraph agentic systems.",
    no_args_is_help=True,
)
console = Console()


@app.callback()
def main() -> None:
    """AgentTelemetry command line interface."""


@app.command()
def version() -> None:
    """Print the AgentTelemetry version."""
    console.print("AgentTelemetry 0.1.0")


@app.command()
def init_trace(
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Path to the JSONL file that should receive the trace event.",
        ),
    ] = Path("agenttelemetry-runs/trace.jsonl"),
    workflow_name: Annotated[
        str,
        typer.Option("--workflow-name", help="Workflow name to include in the trace."),
    ] = "example",
) -> None:
    """Create a minimal JSONL trace file.

    This command is intentionally small. It proves the Milestone 1 runtime writer,
    schema, and CLI are wired together before real LangGraph instrumentation exists.
    """
    run = TraceRun.start(workflow_name=workflow_name)
    event = RuntimeEvent(
        run_id=run.run_id,
        event_type=RuntimeEventType.RUN_START,
        workflow_name=workflow_name,
        metadata={"source": "agenttelemetry init-trace"},
    )

    writer = JsonlTraceWriter(output)
    writer.write(event)

    table = Table(title="Trace Initialized")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("run_id", run.run_id)
    table.add_row("workflow_name", workflow_name)
    table.add_row("output", str(output))
    console.print(table)


@app.command()
def observe(
    entrypoint: Annotated[
        str,
        typer.Argument(help="LangGraph entrypoint in the form file.py:graph."),
    ],
    input_file: Annotated[
        Path,
        typer.Option(
            "--input",
            help="JSON file containing the graph input payload.",
        ),
    ],
    out_dir: Annotated[
        Path,
        typer.Option(
            "--out-dir",
            help="Directory that should receive run artifacts.",
        ),
    ] = Path("runs/test-run"),
    timeout_seconds: Annotated[
        float,
        typer.Option(
            "--timeout-seconds",
            min=0.1,
            help="Maximum seconds allowed for subprocess execution.",
        ),
    ] = 30.0,
    allow_live_tools: Annotated[
        bool,
        typer.Option(
            "--allow-live-tools",
            help="Allow real tool side effects in the child process.",
        ),
    ] = False,
    payload_mode: Annotated[
        PayloadMode,
        typer.Option(
            "--payload-mode",
            help="Trace payload capture mode.",
        ),
    ] = "none",
    redaction_mode: Annotated[
        RedactionMode,
        typer.Option(
            "--redaction-mode",
            help="Trace redaction mode.",
        ),
    ] = "strict",
) -> None:
    """Run a LangGraph entrypoint in an isolated subprocess."""
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = RunManifest(
        entrypoint=entrypoint,
        out_dir=str(out_dir),
        allow_live_tools=allow_live_tools,
        timeout_seconds=timeout_seconds,
        payload_mode=payload_mode,
        redaction_mode=redaction_mode,
    )

    try:
        parsed_entrypoint = parse_entrypoint(entrypoint)
        input_payload = _read_json_file(input_file)
    except (EntrypointError, ValueError) as exc:
        manifest.final_exit_code = 2
        manifest.finished_at = utc_now()
        _write_manifest(out_dir, manifest)
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc

    result = run_isolated_entrypoint(
        parsed_entrypoint,
        input_payload=input_payload,
        timeout_seconds=timeout_seconds,
        allow_live_tools=allow_live_tools,
    )

    manifest.final_exit_code = result.exit_code
    manifest.finished_at = utc_now()
    _write_manifest(out_dir, manifest)

    if result.output is not None:
        _write_json(out_dir / "output.json", result.output)
    _write_trace(
        out_dir / "trace.jsonl",
        run_id=manifest.run_id,
        entrypoint=entrypoint,
        started_at=manifest.started_at,
        ended_at=manifest.finished_at,
        duration_ms=result.duration_ms,
        tool_attempts=_tool_attempts(result.output),
        allow_live_tools=allow_live_tools,
        payload_mode=payload_mode,
        redaction_mode=redaction_mode,
    )

    table = Table(title="Isolated Run")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("entrypoint", entrypoint)
    table.add_row("out_dir", str(out_dir))
    table.add_row("allow_live_tools", str(allow_live_tools).lower())
    table.add_row("exit_code", str(result.exit_code))
    table.add_row("duration_ms", str(result.duration_ms))
    console.print(table)

    if result.error:
        console.print(f"[red]{result.error}[/red]")
    raise typer.Exit(result.exit_code)


def _read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"Input file does not exist: {path}")
    value = path.read_text(encoding="utf-8")

    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise ValueError("Input JSON must be an object.")
    return payload


def _write_manifest(out_dir: Path, manifest: RunManifest) -> None:
    _write_json(out_dir / "manifest.json", manifest.model_dump(mode="json"))


def _write_trace(
    path: Path,
    *,
    run_id: str,
    entrypoint: str,
    started_at,
    ended_at,
    duration_ms: float,
    tool_attempts: list[Any],
    allow_live_tools: bool,
    payload_mode: PayloadMode,
    redaction_mode: RedactionMode,
) -> None:
    writer = JsonlTraceWriter(path)
    events = build_minimal_trace(
        run_id=run_id,
        entrypoint=entrypoint,
        started_at=started_at,
        ended_at=ended_at,
        duration_ms=duration_ms,
        tool_attempts=tool_attempts,
        allow_live_tools=allow_live_tools,
        payload_mode=payload_mode,
        redaction_mode=redaction_mode,
    )
    writer.write_many(events)


def _tool_attempts(output: dict[str, Any] | None) -> list[Any]:
    if output is None:
        return []
    attempts = output.get("tool_attempts", [])
    if not isinstance(attempts, list):
        return []
    return attempts


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
