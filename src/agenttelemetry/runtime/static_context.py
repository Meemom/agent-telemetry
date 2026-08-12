from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from agenttelemetry.runtime.entrypoint import parse_entrypoint


def build_static_context(entrypoint: str) -> dict[str, Any]:
    try:
        parsed = parse_entrypoint(entrypoint)
        module = ast.parse(parsed.file_path.read_text(encoding="utf-8"))
        return {
            "schema_version": "agenttelemetry.static.v1",
            "framework": "langgraph",
            "entrypoint": entrypoint,
            "entrypoint_file": str(parsed.file_path),
            "exported_symbol": parsed.symbol,
            "status": "ok",
            "best_effort": True,
            "nodes": _extract_nodes(module),
            "edges": _extract_edges(module),
            "tools": _extract_tools(module, parsed.file_path),
            "metadata": {
                "source": "ast",
                "limitations": [
                    "does_not_execute_user_code",
                    "dynamic_graph_construction_may_be_incomplete",
                ],
            },
        }
    except Exception as exc:
        return build_static_error(entrypoint, exc)


def build_static_error(entrypoint: str, exc: Exception) -> dict[str, Any]:
    return {
        "schema_version": "agenttelemetry.static.v1",
        "framework": "langgraph",
        "entrypoint": entrypoint,
        "status": "error",
        "best_effort": True,
        "nodes": [],
        "edges": [],
        "tools": [],
        "error": str(exc),
        "metadata": {
            "source": "ast",
            "limitations": [
                "does_not_execute_user_code",
                "dynamic_graph_construction_may_be_incomplete",
            ],
        },
    }


def _extract_nodes(module: ast.Module) -> list[dict[str, Any]]:
    nodes: dict[str, dict[str, Any]] = {}
    for call in _calls(module, "add_node"):
        if not call.args:
            continue
        node_name = _literal_string(call.args[0])
        if node_name is None:
            continue
        nodes[node_name] = {
            "id": node_name,
            "name": node_name,
            "type": "unknown",
            "metadata": {"source": "builder.add_node"},
        }

    for call in _calls(module, "set_entry_point"):
        if not call.args:
            continue
        node_name = _literal_string(call.args[0])
        if node_name is None:
            continue
        nodes.setdefault(
            node_name,
            {
                "id": node_name,
                "name": node_name,
                "type": "unknown",
                "metadata": {},
            },
        )
        nodes[node_name]["metadata"]["entry_point"] = True

    return sorted(nodes.values(), key=lambda node: node["id"])


def _extract_edges(module: ast.Module) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for call in _calls(module, "add_edge"):
        if len(call.args) < 2:
            continue
        source = _node_ref(call.args[0])
        target = _node_ref(call.args[1])
        if source and target:
            edges.append(
                {
                    "source": source,
                    "target": target,
                    "condition": None,
                    "metadata": {"source": "builder.add_edge"},
                }
            )

    for call in _calls(module, "add_conditional_edges"):
        if len(call.args) < 3:
            continue
        source = _node_ref(call.args[0])
        mapping = call.args[2]
        if source is None or not isinstance(mapping, ast.Dict):
            continue
        for key, value in zip(mapping.keys, mapping.values, strict=False):
            target = _node_ref(value)
            condition = _node_ref(key)
            if target:
                edges.append(
                    {
                        "source": source,
                        "target": target,
                        "condition": condition,
                        "metadata": {"source": "builder.add_conditional_edges"},
                    }
                )
    return edges


def _extract_tools(module: ast.Module, file_path: Path) -> list[dict[str, Any]]:
    imported_tools = {
        alias.asname or alias.name
        for item in module.body
        if isinstance(item, ast.ImportFrom) and item.module == "tools"
        for alias in item.names
    }
    tool_file = file_path.parent / "tools.py"
    defined_tools = _defined_functions(tool_file) if tool_file.exists() else set()
    tools = imported_tools | defined_tools
    return [
        {
            "id": tool,
            "name": tool,
            "category": _tool_category(tool),
            "description": None,
            "metadata": {
                "source": "tools.py" if tool in defined_tools else "import",
                "safe_fixture": True,
            },
        }
        for tool in sorted(tools)
    ]


def _defined_functions(path: Path) -> set[str]:
    try:
        module = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()
    return {node.name for node in module.body if isinstance(node, ast.FunctionDef)}


def _calls(module: ast.Module, method_name: str) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(module)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == method_name
    ]


def _literal_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _node_ref(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    return _literal_string(node)


def _tool_category(tool_name: str) -> str:
    if tool_name == "send_email":
        return "external_communication"
    return "unknown"
