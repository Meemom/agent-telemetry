from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from agenttelemetry.model import RunManifest, RuntimeEvent, SecurityFinding, Severity
from agenttelemetry.model.test import TestResult

SEVERITY_RANK: dict[Severity, int] = {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


def build_static_placeholder(entrypoint: str) -> dict[str, Any]:
    return {
        "schema_version": "agenttelemetry.static.v1",
        "framework": "langgraph",
        "entrypoint": entrypoint,
        "status": "not_implemented",
        "nodes": [],
        "edges": [],
        "tools": [],
    }


def trace_summary(trace_events: list[RuntimeEvent]) -> dict[str, Any]:
    event_counts: dict[str, int] = {}
    trace_ids = set()
    tool_names: list[str] = []
    duration_ms = 0.0

    for event in trace_events:
        event_counts[event.event_type.value] = (
            event_counts.get(event.event_type.value, 0) + 1
        )
        trace_ids.add(event.trace_id)
        if event.duration_ms is not None:
            duration_ms += event.duration_ms
        tool_name = event.attributes.get("agenttelemetry.tool_name")
        if isinstance(tool_name, str) and tool_name not in tool_names:
            tool_names.append(tool_name)

    return {
        "event_count": len(trace_events),
        "trace_count": len(trace_ids),
        "event_counts": event_counts,
        "tool_calls_total": event_counts.get("tool_call", 0),
        "tool_names": tool_names,
        "duration_ms": round(duration_ms, 3),
    }


def findings_summary(findings: list[SecurityFinding]) -> dict[str, Any]:
    by_severity: dict[str, int] = {}
    for finding in findings:
        by_severity[finding.severity.value] = (
            by_severity.get(finding.severity.value, 0) + 1
        )
    return {
        "count": len(findings),
        "by_severity": by_severity,
        "highest_severity": highest_severity(findings).value if findings else None,
    }


def build_report_json(
    *,
    manifest: RunManifest,
    static_graph: dict[str, Any],
    trace_events: list[RuntimeEvent],
    test_results: list[TestResult],
    findings: list[SecurityFinding],
) -> dict[str, Any]:
    return {
        "schema_version": "agenttelemetry.report.v1",
        "manifest": manifest.model_dump(mode="json"),
        "static": static_graph,
        "tests": {
            "passed": all(result.passed for result in test_results),
            "results": [result.model_dump(mode="json") for result in test_results],
        },
        "trace_summary": trace_summary(trace_events),
        "findings_summary": findings_summary(findings),
        "findings": [finding.model_dump(mode="json") for finding in findings],
    }


def build_report_html(report: dict[str, Any]) -> str:
    manifest = report["manifest"]
    findings = report["findings"]
    static_graph = report["static"]
    tests = report["tests"]["results"]
    trace = report["trace_summary"]
    findings_rows = "\n".join(_finding_row(finding) for finding in findings) or (
        '<tr><td colspan="5">No findings</td></tr>'
    )
    test_rows = "\n".join(_test_row(result) for result in tests) or (
        '<tr><td colspan="3">No test results</td></tr>'
    )
    run_id = escape(manifest["run_id"])
    entrypoint = escape(manifest["entrypoint"])
    final_exit_code = manifest["final_exit_code"]
    tools = escape(", ".join(trace["tool_names"]))
    static_status = escape(str(static_graph.get("status", "unknown")))
    static_entrypoint = escape(str(static_graph.get("entrypoint", "")))
    static_nodes = escape(
        ", ".join(node.get("name", "") for node in static_graph.get("nodes", []))
    )
    static_tools = escape(
        ", ".join(tool.get("name", "") for tool in static_graph.get("tools", []))
    )

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>AgentTelemetry Report</title>
    <style>
      body {{
        margin: 0;
        background: #f7fafc;
        color: #17212b;
        font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }}
      main {{
        max-width: 1040px;
        margin: 0 auto;
        padding: 40px 24px 64px;
      }}
      h1 {{ margin: 0; font-size: 2.2rem; }}
      h2 {{ margin-top: 32px; font-size: 1.3rem; }}
      table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 12px;
        background: #fff;
      }}
      th, td {{
        border-bottom: 1px solid #d8e1e8;
        padding: 9px 8px;
        text-align: left;
        vertical-align: top;
      }}
      th {{
        color: #5f6f7a;
        font-size: .78rem;
        text-transform: uppercase;
        letter-spacing: .04em;
      }}
      code {{
        background: #eaf1f6;
        border: 1px solid #d4e0e8;
        border-radius: 5px;
        padding: 1px 5px;
      }}
      .grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 12px;
        margin-top: 20px;
      }}
      .card {{
        background: #fff;
        border: 1px solid #d8e1e8;
        border-radius: 8px;
        padding: 14px;
      }}
      .label {{
        color: #5f6f7a;
        display: block;
        font-size: .76rem;
        font-weight: 800;
        text-transform: uppercase;
      }}
      .value {{
        display: block;
        margin-top: 4px;
        font-size: 1.05rem;
        font-weight: 800;
      }}
      .bad {{ color: #b42318; font-weight: 800; }}
      .good {{ color: #0f766e; font-weight: 800; }}
    </style>
  </head>
  <body>
    <main>
      <h1>AgentTelemetry Report</h1>
      <section class="grid">
        <div class="card">
          <span class="label">Run ID</span>
          <span class="value">{run_id}</span>
        </div>
        <div class="card">
          <span class="label">Entrypoint</span>
          <span class="value"><code>{entrypoint}</code></span>
        </div>
        <div class="card">
          <span class="label">Exit Code</span>
          <span class="value">{final_exit_code}</span>
        </div>
        <div class="card">
          <span class="label">Findings</span>
          <span class="value">{len(findings)}</span>
        </div>
      </section>
      <h2>Trace Summary</h2>
      <table>
        <tr><th>Events</th><th>Tool Calls</th><th>Tools</th><th>Duration ms</th></tr>
        <tr>
          <td>{trace["event_count"]}</td>
          <td>{trace["tool_calls_total"]}</td>
          <td>{tools}</td>
          <td>{trace["duration_ms"]}</td>
        </tr>
      </table>
      <h2>Static Context</h2>
      <table>
        <tr><th>Status</th><th>Best Effort</th><th>Entrypoint</th></tr>
        <tr>
          <td>{static_status}</td>
          <td>{static_graph.get("best_effort", True)}</td>
          <td><code>{static_entrypoint}</code></td>
        </tr>
        <tr><th>Nodes</th><th colspan="2">Tools</th></tr>
        <tr>
          <td>{static_nodes}</td>
          <td colspan="2">{static_tools}</td>
        </tr>
      </table>
      <h2>Tests</h2>
      <table>
        <tr><th>Test</th><th>Status</th><th>Assertions</th></tr>
        {test_rows}
      </table>
      <h2>Findings</h2>
      <table>
        <tr><th>ID</th><th>Severity</th><th>Confidence</th><th>Tool</th><th>Remediation</th></tr>
        {findings_rows}
      </table>
    </main>
  </body>
</html>
"""


def finding_meets_threshold(finding: SecurityFinding, threshold: Severity) -> bool:
    return SEVERITY_RANK[finding.severity] >= SEVERITY_RANK[threshold]


def highest_severity(findings: list[SecurityFinding]) -> Severity | None:
    if not findings:
        return None
    return max(findings, key=lambda finding: SEVERITY_RANK[finding.severity]).severity


def write_report_artifacts(out_dir: Path, report: dict[str, Any]) -> None:
    import json

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "report.html").write_text(
        build_report_html(report),
        encoding="utf-8",
    )


def _finding_row(finding: dict[str, Any]) -> str:
    tools = ", ".join(finding.get("affected_tools", []))
    return (
        "<tr>"
        f"<td><code>{escape(finding['id'])}</code></td>"
        f'<td class="bad">{escape(finding["severity"])}</td>'
        f"<td>{escape(finding['confidence'])}</td>"
        f"<td>{escape(tools)}</td>"
        f"<td>{escape(finding.get('remediation') or '')}</td>"
        "</tr>"
    )


def _test_row(result: dict[str, Any]) -> str:
    status_class = "good" if result["passed"] else "bad"
    status = "passed" if result["passed"] else "failed"
    assertion_text = ", ".join(
        f"{assertion['assertion_type']}={assertion['passed']}"
        for assertion in result["assertion_results"]
    )
    return (
        "<tr>"
        f"<td>{escape(result['test_name'])}</td>"
        f'<td class="{status_class}">{status}</td>'
        f"<td>{escape(assertion_text)}</td>"
        "</tr>"
    )
