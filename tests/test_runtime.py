import json
from datetime import UTC, datetime

from agenttelemetry.model import RuntimeEvent, RuntimeEventType
from agenttelemetry.runtime import (
    InMemoryTraceCollector,
    JsonlTraceWriter,
    build_minimal_trace,
)


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


def test_full_payload_trace_redacts_sensitive_values_before_jsonl_write(
    tmp_path,
) -> None:
    trace_path = tmp_path / "trace.jsonl"
    writer = JsonlTraceWriter(trace_path)
    events = build_minimal_trace(
        run_id="run_123",
        entrypoint="examples.app:graph",
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        ended_at=datetime(2026, 1, 1, tzinfo=UTC),
        duration_ms=0.0,
        tool_attempts=[
            {
                "attempted_tool": "send_email",
                "recipient": "attacker@example.com",
                "body": (
                    "SSN 123-45-6789 card 4111-1111-1111-1111 "
                    "key sk-testabcdefghijklmnop"
                ),
                "sent": False,
            }
        ],
        allow_live_tools=False,
        payload_mode="full",
        redaction_mode="strict",
    )

    for event in events:
        writer.write(event)

    contents = trace_path.read_text(encoding="utf-8")
    assert "attacker@example.com" not in contents
    assert "123-45-6789" not in contents
    assert "4111-1111-1111-1111" not in contents
    assert "sk-testabcdefghijklmnop" not in contents
    assert "[REDACTED_EMAIL]" in contents
    assert "[REDACTED_SSN]" in contents
    assert "[REDACTED_CREDIT_CARD]" in contents
    assert "[REDACTED_API_KEY]" in contents
