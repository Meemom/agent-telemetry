from pydantic import BaseModel, Field

from agenttelemetry.model.finding import SecurityFinding


class AssertionResult(BaseModel):
    assertion_type: str
    passed: bool
    message: str
    evidence_event_ids: list[str] = Field(default_factory=list)


class TestResult(BaseModel):
    run_id: str
    test_name: str
    passed: bool
    assertion_results: list[AssertionResult] = Field(default_factory=list)
    findings: list[SecurityFinding] = Field(default_factory=list)

