from pathlib import Path

from agenttelemetry.runtime.static_context import build_static_context

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = PROJECT_ROOT / "examples" / "langgraph_apps" / "customer_support"


def test_build_static_context_extracts_fixture_graph() -> None:
    context = build_static_context(f"{FIXTURE_DIR / 'app.py'}:graph")

    assert context["status"] == "ok"
    assert context["best_effort"] is True
    assert context["entrypoint"] == f"{FIXTURE_DIR / 'app.py'}:graph"
    assert context["exported_symbol"] == "graph"
    assert {node["name"] for node in context["nodes"]} == {
        "send_email",
        "triage",
    }
    assert {tool["name"] for tool in context["tools"]} == {"send_email"}
    assert any(edge["source"] == "triage" for edge in context["edges"])


def test_build_static_context_returns_error_shape_for_missing_entrypoint(
    tmp_path: Path,
) -> None:
    context = build_static_context(f"{tmp_path / 'missing.py'}:graph")

    assert context["status"] == "error"
    assert context["best_effort"] is True
    assert context["entrypoint"] == f"{tmp_path / 'missing.py'}:graph"
