from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RuntimeEventType(StrEnum):
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
    timestamp: datetime = Field(default_factory=utc_now)
    event_type: RuntimeEventType
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

