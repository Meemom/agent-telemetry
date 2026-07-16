from __future__ import annotations

import json
import sys
from typing import Any

from agenttelemetry.runtime.entrypoint import (
    EntrypointError,
    load_entrypoint_object,
    parse_entrypoint,
)


def main() -> int:
    try:
        request = json.loads(sys.stdin.read())
        entrypoint = parse_entrypoint(request["entrypoint"])
        graph = load_entrypoint_object(entrypoint)
        if not hasattr(graph, "invoke"):
            raise EntrypointError("Entrypoint object must expose an invoke method.")

        output = graph.invoke(request.get("input", {}))
        response = {
            "output": output,
            "tool_attempts": _extract_tool_attempts(output),
        }
        print(json.dumps(response, default=str))
        return 0
    except (EntrypointError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - exercised by subprocess behavior.
        print(json.dumps({"error": f"Graph execution failed: {exc}"}), file=sys.stderr)
        return 1


def _extract_tool_attempts(output: Any) -> list[Any]:
    if not isinstance(output, dict):
        return []

    attempts: list[Any] = []
    for key, value in output.items():
        if key.endswith("_attempts") and isinstance(value, list):
            attempts.extend(value)
    return attempts


if __name__ == "__main__":
    raise SystemExit(main())
