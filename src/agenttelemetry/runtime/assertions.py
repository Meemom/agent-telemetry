from __future__ import annotations

import json
import re
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
            trace_events=trace_events,
            final_output=final_output,
        )
        for assertion in configured_test.assertions
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
    trace_events: list[RuntimeEvent],
    final_output: dict[str, Any] | None,
) -> AssertionResult:
    if assertion.type == "tool_called":
        return _evaluate_tool_called(assertion, trace_events)
    if assertion.type == "tool_not_called":
        return _evaluate_tool_not_called(assertion, trace_events)
    if assertion.type == "regex_matches":
        return _evaluate_regex(assertion, trace_events, final_output, should_match=True)
    return _evaluate_regex(assertion, trace_events, final_output, should_match=False)


def _evaluate_tool_called(
    assertion: AssertionConfig, trace_events: list[RuntimeEvent]
) -> AssertionResult:
    matches = _tool_events(trace_events, assertion.tool or "")
    passed = bool(matches)
    return AssertionResult(
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
    assertion: AssertionConfig, trace_events: list[RuntimeEvent]
) -> AssertionResult:
    matches = _tool_events(trace_events, assertion.tool or "")
    passed = not matches
    return AssertionResult(
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
        assertion_type=assertion.type,
        passed=passed,
        message=f"Pattern {verb} target {assertion.target}; expected {expectation}.",
        evidence_event_ids=evidence_event_ids,
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
