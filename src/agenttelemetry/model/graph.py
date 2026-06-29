from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

from agenttelemetry.model.finding import SecurityFinding


class NodeType(StrEnum):
    AGENT = "agent"
    TOOL = "tool"
    MODEL = "model"
    MCP_SERVER = "mcp_server"
    BASIC = "basic"
    UNKNOWN = "unknown"


class GraphNode(BaseModel):
    id: str
    name: str
    type: NodeType = NodeType.UNKNOWN
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    condition: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(BaseModel):
    id: str
    name: str
    category: str = "unknown"
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowGraph(BaseModel):
    workflow_id: str
    name: str
    framework: Literal["langgraph"] = "langgraph"
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    tools: list[ToolDefinition] = Field(default_factory=list)
    findings: list[SecurityFinding] = Field(default_factory=list)

