from typer.testing import CliRunner

from agenttelemetry.cli import app


def test_version_command() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "AgentTelemetry 0.1.0" in result.output


def test_init_trace_command(tmp_path) -> None:
    runner = CliRunner()
    output = tmp_path / "trace.jsonl"

    result = runner.invoke(
        app, ["init-trace", "--workflow-name", "demo", "--output", str(output)]
    )

    assert result.exit_code == 0
    assert output.exists()

