import json

from agenttelemetry.model import RuntimeEvent, RuntimeEventType
from agenttelemetry.runtime import InMemoryTraceCollector, JsonlTraceWriter


def test_in_memory_collector_records_events() -> None:
    collector = InMemoryTraceCollector()
    event = RuntimeEvent(run_id="run_123", event_type=RuntimeEventType.RUN_START)

    collector.record(event)

    assert collector.events == [event]


def test_jsonl_writer_writes_event(tmp_path) -> None:
    trace_path = tmp_path / "trace.jsonl"
    writer = JsonlTraceWriter(trace_path)
    event = RuntimeEvent(run_id="run_123", event_type=RuntimeEventType.RUN_START)

    writer.write(event)

    lines = trace_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["run_id"] == "run_123"
    assert payload["event_type"] == "run_start"

