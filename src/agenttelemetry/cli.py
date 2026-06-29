from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from agenttelemetry.model import RuntimeEvent, RuntimeEventType, TraceRun
from agenttelemetry.runtime import JsonlTraceWriter

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

