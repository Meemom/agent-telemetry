from enum import StrEnum

from pydantic import BaseModel, Field


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SecurityFinding(BaseModel):
    id: str
    title: str
    severity: Severity
    confidence: Confidence = Confidence.MEDIUM
    description: str
    affected_nodes: list[str] = Field(default_factory=list)
    affected_tools: list[str] = Field(default_factory=list)
    static_evidence: list[str] = Field(default_factory=list)
    runtime_evidence: list[str] = Field(default_factory=list)
    remediation: str | None = None

