from agenttelemetry.model import AssertionConfig, ConfiguredTest, RuntimeEvent
from agenttelemetry.model.trace import RuntimeEventType
from agenttelemetry.runtime import create_findings, evaluate_test


def test_create_findings_from_failed_send_email_assertion() -> None:
    event = RuntimeEvent(
        run_id="run_123",
        event_type=RuntimeEventType.TOOL_CALL,
        attributes={"agenttelemetry.tool_name": "send_email"},
    )
    configured_test = ConfiguredTest(
        name="prompt_injection_no_email",
        input={},
        assertions=[
            AssertionConfig(type="tool_not_called", tool="send_email"),
        ],
    )
    test_result = evaluate_test(
        configured_test,
        run_id="run_123",
        trace_events=[event],
        final_output={},
    )

    findings = create_findings(test_result, [event])

    assert len(findings) == 1
    finding = findings[0]
    assert finding.severity == "high"
    assert finding.confidence == "high"
    assert finding.assertion_id == test_result.assertion_results[0].assertion_id
    assert finding.runtime_evidence == [event.event_id]
    assert finding.affected_tools == ["send_email"]
    assert finding.tool_category == "external_communication"
    assert finding.attempted_side_effect == "email_send_attempt"
    assert finding.remediation is not None


def test_create_findings_ignores_passing_assertions() -> None:
    configured_test = ConfiguredTest(
        name="safe_path",
        input={},
        assertions=[
            AssertionConfig(type="tool_not_called", tool="send_email"),
        ],
    )
    test_result = evaluate_test(
        configured_test,
        run_id="run_123",
        trace_events=[],
        final_output={},
    )

    assert create_findings(test_result, []) == []
