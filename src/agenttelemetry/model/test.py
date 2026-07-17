from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from agenttelemetry.model.finding import SecurityFinding


class AssertionConfig(BaseModel):
    type: Literal[
        "tool_called",
        "tool_not_called",
        "regex_matches",
        "regex_not_matches",
    ]
    tool: str | None = None
    target: Literal["output", "tool_args"] | None = None
    pattern: str | None = None

    @model_validator(mode="after")
    def validate_required_fields(self) -> "AssertionConfig":
        if self.type in {"tool_called", "tool_not_called"} and not self.tool:
            raise ValueError(f"{self.type} requires a tool field")
        if self.type in {"regex_matches", "regex_not_matches"}:
            if not self.target:
                raise ValueError(f"{self.type} requires a target field")
            if not self.pattern:
                raise ValueError(f"{self.type} requires a pattern field")
        return self


class ConfiguredTest(BaseModel):
    name: str
    input: dict[str, Any]
    assertions: list[AssertionConfig] = Field(min_length=1)


class TestSuiteConfig(BaseModel):
    tests: list[ConfiguredTest] = Field(min_length=1)


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
