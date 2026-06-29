from agenttelemetry.model import (
    GraphEdge,
    GraphNode,
    RuntimeEvent,
    RuntimeEventType,
    TraceRun,
    WorkflowGraph,
)


def test_trace_run_creates_run_id() -> None:
    run = TraceRun.start("demo")

    assert run.run_id.startswith("run_")
    assert run.workflow_name == "demo"


def test_runtime_event_serializes_to_json_shape() -> None:
    event = RuntimeEvent(run_id="run_123", event_type=RuntimeEventType.RUN_START)
    payload = event.model_dump(mode="json")

    assert payload["event_type"] == "run_start"
    assert payload["run_id"] == "run_123"
    assert payload["event_id"].startswith("evt_")


def test_workflow_graph_defaults_to_langgraph() -> None:
    graph = WorkflowGraph(
        workflow_id="wf_123",
        name="demo",
        nodes=[GraphNode(id="start", name="START")],
        edges=[GraphEdge(source="START", target="END")],
    )

    assert graph.framework == "langgraph"
    assert graph.nodes[0].name == "START"
    assert graph.edges[0].target == "END"

