from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from agenttelemetry.model import RuntimeEvent, RuntimeEventType

PayloadMode = Literal["none", "summary", "full"]
RedactionMode = Literal["strict", "metadata", "off"]

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def build_minimal_trace(
    *,
    run_id: str,
    entrypoint: str,
    started_at: datetime,
    ended_at: datetime,
    duration_ms: float,
    tool_attempts: list[Any],
    allow_live_tools: bool,
    payload_mode: PayloadMode = "none",
    redaction_mode: RedactionMode = "strict",
) -> list[RuntimeEvent]:
    trace_id = uuid4().hex
    root_span_id = uuid4().hex[:16]
    root_attributes = {
        "agenttelemetry.run_id": run_id,
        "agenttelemetry.schema_version": "agenttelemetry.trace.v1",
        "agenttelemetry.framework": "langgraph",
        "agenttelemetry.entrypoint": entrypoint,
        "agenttelemetry.payload_mode": payload_mode,
        "agenttelemetry.redaction_mode": redaction_mode,
        "agenttelemetry.allow_live_tools": allow_live_tools,
    }

    events = [
        RuntimeEvent(
            run_id=run_id,
            trace_id=trace_id,
            span_id=root_span_id,
            event_type=RuntimeEventType.SPAN_START,
            span_name="langgraph.invoke",
            span_status="unset",
            started_at=started_at,
            attributes=root_attributes,
        )
    ]

    for attempt in tool_attempts:
        events.append(
            RuntimeEvent(
                run_id=run_id,
                trace_id=trace_id,
                span_id=uuid4().hex[:16],
                parent_span_id=root_span_id,
                event_type=RuntimeEventType.TOOL_CALL,
                span_name="tool.call",
                span_status="ok",
                started_at=ended_at,
                ended_at=ended_at,
                duration_ms=0.0,
                attributes={
                    **root_attributes,
                    "agenttelemetry.tool_name": _tool_name(attempt),
                },
                metadata=_tool_metadata(
                    attempt,
                    payload_mode=payload_mode,
                    redaction_mode=redaction_mode,
                ),
            )
        )

    events.append(
        RuntimeEvent(
            run_id=run_id,
            trace_id=trace_id,
            span_id=root_span_id,
            event_type=RuntimeEventType.SPAN_END,
            span_name="langgraph.invoke",
            span_status="ok",
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=duration_ms,
            attributes=root_attributes,
        )
    )
    return events


def _tool_name(attempt: Any) -> str:
    if isinstance(attempt, dict):
        value = attempt.get("attempted_tool") or attempt.get("tool_name")
        if isinstance(value, str) and value:
            return value
    return "unknown"


def _tool_metadata(
    attempt: Any,
    *,
    payload_mode: PayloadMode,
    redaction_mode: RedactionMode,
) -> dict[str, Any]:
    if not isinstance(attempt, dict):
        return {"payload_mode": payload_mode}

    metadata: dict[str, Any] = {
        "payload_mode": payload_mode,
        "simulated": str(attempt.get("sent", "")).lower() == "false",
    }
    if payload_mode == "summary":
        metadata["argument_keys"] = sorted(
            key for key in attempt if key not in {"attempted_tool", "tool_name"}
        )
    elif payload_mode == "full":
        metadata["tool_args"] = _redact(attempt, redaction_mode)
    return metadata


def _redact(value: Any, redaction_mode: RedactionMode) -> Any:
    if redaction_mode == "off":
        return value
    if isinstance(value, dict):
        return {key: _redact(child, redaction_mode) for key, child in value.items()}
    if isinstance(value, list):
        return [_redact(child, redaction_mode) for child in value]
    if isinstance(value, str):
        redacted = _EMAIL_RE.sub("[REDACTED_EMAIL]", value)
        if redaction_mode == "strict" and len(redacted) > 80:
            return f"{redacted[:77]}..."
        return redacted
    return value
