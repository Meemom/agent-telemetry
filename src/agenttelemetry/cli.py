import json
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Any

import typer
import yaml
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from agenttelemetry.model import (
    RunManifest,
    RuntimeEvent,
    RuntimeEventType,
    SecurityFinding,
    Severity,
    TestResult,
    TestSuiteConfig,
    TraceRun,
)
from agenttelemetry.model.trace import utc_now
from agenttelemetry.runtime import (
    EntrypointError,
    JsonlTraceWriter,
    build_report_json,
    build_static_context,
    build_static_error,
    create_findings,
    evaluate_test,
    finding_meets_threshold,
    parse_entrypoint,
    run_isolated_entrypoint,
    write_report_artifacts,
)
from agenttelemetry.runtime.isolated import IsolatedRunResult
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

    result, trace_events = _run_and_write_artifacts(
        entrypoint=entrypoint,
        parsed_entrypoint=parsed_entrypoint,
        input_payload=input_payload,
        out_dir=out_dir,
        manifest=manifest,
        timeout_seconds=timeout_seconds,
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


@app.command()
def test(
    entrypoint: Annotated[
        str,
        typer.Argument(help="LangGraph entrypoint in the form file.py:graph."),
    ],
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            help="YAML file containing deterministic adversarial tests.",
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
    """Run configured deterministic assertions against an isolated graph."""
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = RunManifest(
        entrypoint=entrypoint,
        config_path=str(config),
        config_sha256=_file_sha256(config) if config.exists() else None,
        out_dir=str(out_dir),
        allow_live_tools=allow_live_tools,
        timeout_seconds=timeout_seconds,
        payload_mode=payload_mode,
        redaction_mode=redaction_mode,
    )

    try:
        parsed_entrypoint = parse_entrypoint(entrypoint)
        suite = _load_test_suite(config)
    except (EntrypointError, ValueError, ValidationError) as exc:
        manifest.final_exit_code = 2
        manifest.finished_at = utc_now()
        _write_manifest(out_dir, manifest)
        _write_json(
            out_dir / "tests.json",
            {
                "schema_version": "agenttelemetry.tests.v1",
                "run_id": manifest.run_id,
                "passed": False,
                "error": str(exc),
                "results": [],
            },
        )
        _write_findings_json(out_dir, manifest.run_id, [])
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc

    configured_test = suite.tests[0]
    result, trace_events = _run_and_write_artifacts(
        entrypoint=entrypoint,
        parsed_entrypoint=parsed_entrypoint,
        input_payload=configured_test.input,
        out_dir=out_dir,
        manifest=manifest,
        timeout_seconds=timeout_seconds,
        allow_live_tools=allow_live_tools,
        payload_mode=payload_mode,
        redaction_mode=redaction_mode,
    )

    if result.exit_code != 0:
        _write_tests_json(out_dir, manifest.run_id, [])
        _write_findings_json(out_dir, manifest.run_id, [])
        raise typer.Exit(result.exit_code)

    test_result = evaluate_test(
        configured_test,
        run_id=manifest.run_id,
        trace_events=trace_events,
        final_output=result.output.get("output") if result.output else None,
    )
    findings = create_findings(test_result, trace_events)
    test_result.findings = findings
    final_exit_code = 0 if test_result.passed else 1
    manifest.final_exit_code = final_exit_code
    manifest.finished_at = utc_now()
    _write_manifest(out_dir, manifest)
    _write_tests_json(out_dir, manifest.run_id, [test_result])
    _write_findings_json(out_dir, manifest.run_id, findings)

    table = Table(title="Deterministic Test Run")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("test_name", configured_test.name)
    table.add_row("passed", str(test_result.passed).lower())
    table.add_row("exit_code", str(final_exit_code))
    console.print(table)
    raise typer.Exit(final_exit_code)


@app.command()
def ci(
    entrypoint: Annotated[
        str,
        typer.Argument(help="LangGraph entrypoint in the form file.py:graph."),
    ],
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            help="YAML file containing deterministic adversarial tests.",
        ),
    ],
    out_dir: Annotated[
        Path,
        typer.Option(
            "--out-dir",
            help="Directory that should receive CI artifacts.",
        ),
    ] = Path("runs/test-run"),
    severity_threshold: Annotated[
        Severity,
        typer.Option(
            "--severity-threshold",
            help="Minimum finding severity that should fail CI.",
        ),
    ] = Severity.HIGH,
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
    """Run the core CI security loop and write stable report artifacts."""
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = RunManifest(
        entrypoint=entrypoint,
        config_path=str(config),
        config_sha256=_file_sha256(config) if config.exists() else None,
        out_dir=str(out_dir),
        allow_live_tools=allow_live_tools,
        timeout_seconds=timeout_seconds,
        payload_mode=payload_mode,
        redaction_mode=redaction_mode,
    )
    try:
        static_graph = build_static_context(entrypoint)
    except Exception as exc:
        static_graph = build_static_error(entrypoint, exc)
    _write_json(out_dir / "static.json", static_graph)

    try:
        parsed_entrypoint = parse_entrypoint(entrypoint)
        suite = _load_test_suite(config)
    except (EntrypointError, ValueError, ValidationError) as exc:
        _write_empty_ci_artifacts(
            out_dir=out_dir,
            manifest=manifest,
            static_graph=static_graph,
            error=str(exc),
        )
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc

    configured_test = suite.tests[0]
    result, trace_events = _run_and_write_artifacts(
        entrypoint=entrypoint,
        parsed_entrypoint=parsed_entrypoint,
        input_payload=configured_test.input,
        out_dir=out_dir,
        manifest=manifest,
        timeout_seconds=timeout_seconds,
        allow_live_tools=allow_live_tools,
        payload_mode=payload_mode,
        redaction_mode=redaction_mode,
    )

    if result.exit_code != 0:
        manifest.final_exit_code = 2
        manifest.finished_at = utc_now()
        _write_manifest(out_dir, manifest)
        _write_tests_json(out_dir, manifest.run_id, [])
        _write_findings_json(out_dir, manifest.run_id, [])
        _write_ci_report(
            out_dir=out_dir,
            manifest=manifest,
            static_graph=static_graph,
            trace_events=trace_events,
            test_results=[],
            findings=[],
        )
        raise typer.Exit(2)

    test_result = evaluate_test(
        configured_test,
        run_id=manifest.run_id,
        trace_events=trace_events,
        final_output=result.output.get("output") if result.output else None,
    )
    findings = create_findings(test_result, trace_events)
    test_result.findings = findings
    failed_threshold = any(
        finding_meets_threshold(finding, severity_threshold) for finding in findings
    )
    final_exit_code = 1 if failed_threshold else 0
    manifest.final_exit_code = final_exit_code
    manifest.finished_at = utc_now()
    _write_manifest(out_dir, manifest)
    _write_tests_json(out_dir, manifest.run_id, [test_result])
    _write_findings_json(out_dir, manifest.run_id, findings)
    _write_ci_report(
        out_dir=out_dir,
        manifest=manifest,
        static_graph=static_graph,
        trace_events=trace_events,
        test_results=[test_result],
        findings=findings,
    )

    table = Table(title="CI Security Run")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("test_name", configured_test.name)
    table.add_row("severity_threshold", severity_threshold.value)
    table.add_row("findings", str(len(findings)))
    table.add_row("exit_code", str(final_exit_code))
    console.print(table)
    raise typer.Exit(final_exit_code)


def _read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"Input file does not exist: {path}")
    value = path.read_text(encoding="utf-8")

    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise ValueError("Input JSON must be an object.")
    return payload


def _load_test_suite(path: Path) -> TestSuiteConfig:
    if not path.exists():
        raise ValueError(f"Config file does not exist: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Test config must be a YAML object.")
    return TestSuiteConfig.model_validate(data)


def _file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_manifest(out_dir: Path, manifest: RunManifest) -> None:
    _write_json(out_dir / "manifest.json", manifest.model_dump(mode="json"))


def _run_and_write_artifacts(
    *,
    entrypoint: str,
    parsed_entrypoint,
    input_payload: dict[str, Any],
    out_dir: Path,
    manifest: RunManifest,
    timeout_seconds: float,
    allow_live_tools: bool,
    payload_mode: PayloadMode,
    redaction_mode: RedactionMode,
) -> tuple[IsolatedRunResult, list[RuntimeEvent]]:
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
    trace_events = _write_trace(
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
    return result, trace_events


def _write_trace(
    path: Path,
    *,
    run_id: str,
    entrypoint: str,
    started_at: datetime,
    ended_at: datetime,
    duration_ms: float,
    tool_attempts: list[Any],
    allow_live_tools: bool,
    payload_mode: PayloadMode,
    redaction_mode: RedactionMode,
) -> list[RuntimeEvent]:
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
    return events


def _write_tests_json(out_dir: Path, run_id: str, results: list[TestResult]) -> None:
    _write_json(
        out_dir / "tests.json",
        {
            "schema_version": "agenttelemetry.tests.v1",
            "run_id": run_id,
            "passed": all(result.passed for result in results),
            "results": [result.model_dump(mode="json") for result in results],
        },
    )


def _write_findings_json(
    out_dir: Path, run_id: str, findings: list[SecurityFinding]
) -> None:
    _write_json(
        out_dir / "findings.json",
        {
            "schema_version": "agenttelemetry.findings.v1",
            "run_id": run_id,
            "findings": [finding.model_dump(mode="json") for finding in findings],
        },
    )


def _write_empty_ci_artifacts(
    *,
    out_dir: Path,
    manifest: RunManifest,
    static_graph: dict[str, Any],
    error: str,
) -> None:
    manifest.final_exit_code = 2
    manifest.finished_at = utc_now()
    _write_manifest(out_dir, manifest)
    _write_json(out_dir / "output.json", {"error": error})
    (out_dir / "trace.jsonl").write_text("", encoding="utf-8")
    _write_json(
        out_dir / "tests.json",
        {
            "schema_version": "agenttelemetry.tests.v1",
            "run_id": manifest.run_id,
            "passed": False,
            "error": error,
            "results": [],
        },
    )
    _write_findings_json(out_dir, manifest.run_id, [])
    _write_ci_report(
        out_dir=out_dir,
        manifest=manifest,
        static_graph=static_graph,
        trace_events=[],
        test_results=[],
        findings=[],
    )


def _write_ci_report(
    *,
    out_dir: Path,
    manifest: RunManifest,
    static_graph: dict[str, Any],
    trace_events: list[RuntimeEvent],
    test_results: list[TestResult],
    findings: list[SecurityFinding],
) -> None:
    report = build_report_json(
        manifest=manifest,
        static_graph=static_graph,
        trace_events=trace_events,
        test_results=test_results,
        findings=findings,
    )
    write_report_artifacts(out_dir, report)


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
