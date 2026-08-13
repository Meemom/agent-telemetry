from __future__ import annotations

import json
import re
from hashlib import sha256
from typing import Any

from agenttelemetry.model import (
    AssertionConfig,
    AssertionResult,
    ConfiguredTest,
    RuntimeEvent,
    RuntimeEventType,
    TestResult,
)


def evaluate_test(
    configured_test: ConfiguredTest,
    *,
    run_id: str,
    trace_events: list[RuntimeEvent],
    final_output: dict[str, Any] | None,
) -> TestResult:
    assertion_results = [
        evaluate_assertion(
            assertion,
            assertion_id=_assertion_id(configured_test.name, index, assertion),
            trace_events=trace_events,
            final_output=final_output,
        )
        for index, assertion in enumerate(configured_test.assertions)
    ]
    return TestResult(
        run_id=run_id,
        test_name=configured_test.name,
        passed=all(result.passed for result in assertion_results),
        assertion_results=assertion_results,
    )


def evaluate_assertion(
    assertion: AssertionConfig,
    *,
    assertion_id: str | None = None,
    trace_events: list[RuntimeEvent],
    final_output: dict[str, Any] | None,
) -> AssertionResult:
    assertion_id = assertion_id or _assertion_id("adhoc", 0, assertion)
    if assertion.type == "tool_called":
        return _evaluate_tool_called(assertion, assertion_id, trace_events)
    if assertion.type == "tool_not_called":
        return _evaluate_tool_not_called(assertion, assertion_id, trace_events)
    if assertion.type == "regex_matches":
        return _evaluate_regex(
            assertion,
            assertion_id,
            trace_events,
            final_output,
            should_match=True,
        )
    if assertion.type == "regex_not_matches":
        return _evaluate_regex(
            assertion,
            assertion_id,
            trace_events,
            final_output,
            should_match=False,
        )
    if assertion.type == "node_reached":
        return _evaluate_node_reached(assertion, assertion_id, trace_events)
    if assertion.type == "node_not_reached":
        return _evaluate_node_not_reached(assertion, assertion_id, trace_events)
    if assertion.type == "error_absent":
        return _evaluate_error_absent(assertion, assertion_id, trace_events)
    return _evaluate_max_tool_calls(assertion, assertion_id, trace_events)


def _evaluate_tool_called(
    assertion: AssertionConfig, assertion_id: str, trace_events: list[RuntimeEvent]
) -> AssertionResult:
    matches = _tool_events(trace_events, assertion.tool or "")
    passed = bool(matches)
    return AssertionResult(
        assertion_id=assertion_id,
        assertion_type=assertion.type,
        passed=passed,
        message=(
            f"Observed tool call: {assertion.tool}"
            if passed
            else f"Expected tool call was not observed: {assertion.tool}"
        ),
        evidence_event_ids=[event.event_id for event in matches],
    )


def _evaluate_tool_not_called(
    assertion: AssertionConfig, assertion_id: str, trace_events: list[RuntimeEvent]
) -> AssertionResult:
    matches = _tool_events(trace_events, assertion.tool or "")
    passed = not matches
    return AssertionResult(
        assertion_id=assertion_id,
        assertion_type=assertion.type,
        passed=passed,
        message=(
            f"Tool was not observed: {assertion.tool}"
            if passed
            else f"Unexpected tool call observed: {assertion.tool}"
        ),
        evidence_event_ids=[event.event_id for event in matches],
    )


def _evaluate_regex(
    assertion: AssertionConfig,
    assertion_id: str,
    trace_events: list[RuntimeEvent],
    final_output: dict[str, Any] | None,
    *,
    should_match: bool,
) -> AssertionResult:
    pattern = assertion.pattern or ""
    evidence_event_ids: list[str] = []
    haystacks = _regex_haystacks(
        assertion.target or "output",
        trace_events,
        final_output,
    )
    matched = False
    for event_id, text in haystacks:
        if re.search(pattern, text):
            matched = True
            if event_id:
                evidence_event_ids.append(event_id)

    passed = matched if should_match else not matched
    verb = "matched" if matched else "did not match"
    expectation = "match" if should_match else "not match"
    return AssertionResult(
        assertion_id=assertion_id,
        assertion_type=assertion.type,
        passed=passed,
        message=f"Pattern {verb} target {assertion.target}; expected {expectation}.",
        evidence_event_ids=evidence_event_ids,
    )


def _evaluate_node_reached(
    assertion: AssertionConfig, assertion_id: str, trace_events: list[RuntimeEvent]
) -> AssertionResult:
    matches = _node_events(trace_events, assertion.node or "")
    passed = bool(matches)
    return AssertionResult(
        assertion_id=assertion_id,
        assertion_type=assertion.type,
        passed=passed,
        message=(
            f"Observed node execution: {assertion.node}"
            if passed
            else f"Expected node execution was not observed: {assertion.node}"
        ),
        evidence_event_ids=[event.event_id for event in matches],
    )


def _evaluate_node_not_reached(
    assertion: AssertionConfig, assertion_id: str, trace_events: list[RuntimeEvent]
) -> AssertionResult:
    matches = _node_events(trace_events, assertion.node or "")
    passed = not matches
    return AssertionResult(
        assertion_id=assertion_id,
        assertion_type=assertion.type,
        passed=passed,
        message=(
            f"Node was not observed: {assertion.node}"
            if passed
            else f"Unexpected node execution observed: {assertion.node}"
        ),
        evidence_event_ids=[event.event_id for event in matches],
    )


def _evaluate_error_absent(
    assertion: AssertionConfig, assertion_id: str, trace_events: list[RuntimeEvent]
) -> AssertionResult:
    matches = _error_events(trace_events)
    passed = not matches
    return AssertionResult(
        assertion_id=assertion_id,
        assertion_type=assertion.type,
        passed=passed,
        message=(
            "No runtime errors were observed."
            if passed
            else f"Observed {len(matches)} runtime error event(s)."
        ),
        evidence_event_ids=[event.event_id for event in matches],
    )


def _evaluate_max_tool_calls(
    assertion: AssertionConfig, assertion_id: str, trace_events: list[RuntimeEvent]
) -> AssertionResult:
    matches = (
        _tool_events(trace_events, assertion.tool)
        if assertion.tool
        else _all_tool_events(trace_events)
    )
    max_count = assertion.max_count or 0
    count = len(matches)
    passed = count <= max_count
    scope = assertion.tool or "all tools"
    message = (
        f"Observed {count} tool call(s) for {scope}; maximum allowed is {max_count}."
    )
    return AssertionResult(
        assertion_id=assertion_id,
        assertion_type=assertion.type,
        passed=passed,
        message=message,
        evidence_event_ids=[event.event_id for event in matches],
    )


def _tool_events(
    trace_events: list[RuntimeEvent], tool_name: str
) -> list[RuntimeEvent]:
    return [
        event
        for event in trace_events
        if event.event_type == RuntimeEventType.TOOL_CALL
        and event.attributes.get("agenttelemetry.tool_name") == tool_name
    ]


def _all_tool_events(trace_events: list[RuntimeEvent]) -> list[RuntimeEvent]:
    return [
        event
        for event in trace_events
        if event.event_type == RuntimeEventType.TOOL_CALL
    ]


def _node_events(
    trace_events: list[RuntimeEvent], node_name: str
) -> list[RuntimeEvent]:
    return [
        event
        for event in trace_events
        if event.event_type in {RuntimeEventType.NODE_START, RuntimeEventType.NODE_END}
        and _event_node_name(event) == node_name
    ]


def _event_node_name(event: RuntimeEvent) -> str | None:
    if event.node_name:
        return event.node_name
    value = event.attributes.get("agenttelemetry.node_name")
    if isinstance(value, str):
        return value
    return None


def _error_events(trace_events: list[RuntimeEvent]) -> list[RuntimeEvent]:
    return [
        event
        for event in trace_events
        if event.event_type == RuntimeEventType.ERROR or event.span_status == "error"
    ]


def _regex_haystacks(
    target: str,
    trace_events: list[RuntimeEvent],
    final_output: dict[str, Any] | None,
) -> list[tuple[str | None, str]]:
    if target == "tool_args":
        return [
            (event.event_id, json.dumps(event.metadata.get("tool_args", {})))
            for event in trace_events
            if event.event_type == RuntimeEventType.TOOL_CALL
        ]
    return [(None, json.dumps(final_output or {}, sort_keys=True))]


def _assertion_id(test_name: str, index: int, assertion: AssertionConfig) -> str:
    parts = [
        test_name,
        str(index),
        assertion.type,
        assertion.tool or "",
        assertion.target or "",
        assertion.pattern or "",
    ]
    if assertion.type in {"node_reached", "node_not_reached"}:
        parts.append(assertion.node or "")
    if assertion.type == "max_tool_calls":
        parts.append(
            str(assertion.max_count) if assertion.max_count is not None else ""
        )
    raw = ":".join(parts)
    return f"assert_{sha256(raw.encode()).hexdigest()[:12]}"
