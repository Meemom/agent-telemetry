from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class RuntimeEventType(StrEnum):
    SPAN_START = "span_start"
    SPAN_END = "span_end"
    RUN_START = "run_start"
    RUN_END = "run_end"
    NODE_START = "node_start"
    NODE_END = "node_end"
    TOOL_CALL = "tool_call"
    MODEL_CALL = "model_call"
    ROUTE_DECISION = "route_decision"
    ERROR = "error"


class RuntimeEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex}")
    run_id: str
    trace_id: str = Field(default_factory=lambda: uuid4().hex)
    span_id: str = Field(default_factory=lambda: uuid4().hex[:16])
    parent_span_id: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)
    event_type: RuntimeEventType
    span_name: str = "runtime"
    span_kind: Literal["internal", "client", "server", "producer", "consumer"] = (
        "internal"
    )
    span_status: Literal["unset", "ok", "error"] = "unset"
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_ms: float | None = None
    attributes: dict[str, str | int | float | bool] = Field(default_factory=dict)
    workflow_name: str | None = None
    node_name: str | None = None
    input: Any | None = None
    output: Any | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceRun(BaseModel):
    run_id: str = Field(default_factory=lambda: f"run_{uuid4().hex}")
    workflow_name: str
    started_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def start(
        cls, workflow_name: str, metadata: dict[str, Any] | None = None
    ) -> "TraceRun":
        return cls(workflow_name=workflow_name, metadata=metadata or {})
