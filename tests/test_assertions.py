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
