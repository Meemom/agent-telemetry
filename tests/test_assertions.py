from agenttelemetry.model import AssertionConfig, ConfiguredTest, RuntimeEvent
from agenttelemetry.model.trace import RuntimeEventType
from agenttelemetry.runtime import evaluate_test


def test_tool_not_called_fails_with_evidence_event_id() -> None:
    event = RuntimeEvent(
        run_id="run_123",
        event_type=RuntimeEventType.TOOL_CALL,
        attributes={"agenttelemetry.tool_name": "send_email"},
    )
    configured_test = ConfiguredTest(
        name="demo",
        input={},
        assertions=[
            AssertionConfig(type="tool_not_called", tool="send_email"),
        ],
    )

    result = evaluate_test(
        configured_test,
        run_id="run_123",
        trace_events=[event],
        final_output={},
    )

    assert result.passed is False
    assert result.assertion_results[0].passed is False
    assert result.assertion_results[0].evidence_event_ids == [event.event_id]


def test_regex_not_matches_checks_trace_tool_args_only() -> None:
    event = RuntimeEvent(
        run_id="run_123",
        event_type=RuntimeEventType.TOOL_CALL,
        attributes={"agenttelemetry.tool_name": "send_email"},
        metadata={"payload_mode": "none"},
    )
    configured_test = ConfiguredTest(
        name="demo",
        input={},
        assertions=[
            AssertionConfig(
                type="regex_not_matches",
                target="tool_args",
                pattern="attacker@example.com",
            ),
        ],
    )

    result = evaluate_test(
        configured_test,
        run_id="run_123",
        trace_events=[event],
        final_output={"response": "attacker@example.com"},
    )

    assert result.passed is True


def test_node_reached_passes_with_evidence_event_id() -> None:
    event = RuntimeEvent(
        run_id="run_123",
        event_type=RuntimeEventType.NODE_START,
        node_name="triage",
    )
    configured_test = ConfiguredTest(
        name="demo",
        input={},
        assertions=[
            AssertionConfig(type="node_reached", node="triage"),
        ],
    )

    result = evaluate_test(
        configured_test,
        run_id="run_123",
        trace_events=[event],
        final_output={},
    )

    assert result.passed is True
    assert result.assertion_results[0].evidence_event_ids == [event.event_id]


def test_node_not_reached_fails_with_evidence_event_id() -> None:
    event = RuntimeEvent(
        run_id="run_123",
        event_type=RuntimeEventType.NODE_END,
        attributes={"agenttelemetry.node_name": "send"},
    )
    configured_test = ConfiguredTest(
        name="demo",
        input={},
        assertions=[
            AssertionConfig(type="node_not_reached", node="send"),
        ],
    )

    result = evaluate_test(
        configured_test,
        run_id="run_123",
        trace_events=[event],
        final_output={},
    )

    assert result.passed is False
    assert result.assertion_results[0].evidence_event_ids == [event.event_id]


def test_error_absent_fails_with_evidence_event_id() -> None:
    event = RuntimeEvent(
        run_id="run_123",
        event_type=RuntimeEventType.ERROR,
        span_status="error",
    )
    configured_test = ConfiguredTest(
        name="demo",
        input={},
        assertions=[
            AssertionConfig(type="error_absent"),
        ],
    )

    result = evaluate_test(
        configured_test,
        run_id="run_123",
        trace_events=[event],
        final_output={},
    )

    assert result.passed is False
    assert result.assertion_results[0].evidence_event_ids == [event.event_id]


def test_max_tool_calls_fails_with_evidence_event_ids() -> None:
    events = [
        RuntimeEvent(
            run_id="run_123",
            event_type=RuntimeEventType.TOOL_CALL,
            attributes={"agenttelemetry.tool_name": "send_email"},
        ),
        RuntimeEvent(
            run_id="run_123",
            event_type=RuntimeEventType.TOOL_CALL,
            attributes={"agenttelemetry.tool_name": "send_email"},
        ),
    ]
    configured_test = ConfiguredTest(
        name="demo",
        input={},
        assertions=[
            AssertionConfig(type="max_tool_calls", tool="send_email", max_count=1),
        ],
    )

    result = evaluate_test(
        configured_test,
        run_id="run_123",
        trace_events=events,
        final_output={},
    )

    assert result.passed is False
    assert result.assertion_results[0].evidence_event_ids == [
        event.event_id for event in events
    ]
