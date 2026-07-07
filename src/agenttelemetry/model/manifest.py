from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from agenttelemetry.model.trace import utc_now


class RunManifest(BaseModel):
    schema_version: str = "agenttelemetry.run.v1"
    cli_version: str = "0.1.0"
    run_id: str = Field(default_factory=lambda: f"run_{uuid4().hex}")
    entrypoint: str
    config_path: str | None = None
    config_sha256: str | None = None
    out_dir: str
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None
    redaction_mode: Literal["strict", "metadata", "off"] = "strict"
    payload_mode: Literal["none", "summary", "full"] = "none"
    allow_live_tools: bool = False
    timeout_seconds: float
    final_exit_code: int | None = None
