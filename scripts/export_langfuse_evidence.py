from __future__ import annotations

import html
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langfuse import get_client


REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = REPO_ROOT / "submission" / "evidence"
PROMPT_NAME = "day13-chat"
FIELDS = "core,basic,metadata,model,usage,prompt,metrics,trace_context,io"


def safe(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, indent=2)


def observation_rows(client: Any) -> list[dict[str, Any]]:
    response = client.api.observations.get_many(
        limit=1000,
        fields=FIELDS,
        from_start_time=datetime.now(timezone.utc) - timedelta(days=2),
        to_start_time=datetime.now(timezone.utc) + timedelta(minutes=1),
        expand_metadata="correlation_id,feature,model,prompt_name,prompt_label,prompt_version,ttft_ms,prompt_source,prompt_fetch_error",
    )
    return [row.model_dump() for row in response.data]


def roots(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if row.get("type") == "AGENT" and row.get("is_root_observation") is True
    ]


def generation_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("type") == "GENERATION"]


def trace_card(row: dict[str, Any]) -> str:
    metadata = row.get("metadata") or {}
    return (
        "<tr>"
        f"<td><code>{safe(row.get('trace_id'))}</code></td>"
        f"<td>{safe(metadata.get('correlation_id'))}</td>"
        f"<td>{safe(row.get('session_id'))}</td>"
        f"<td>{safe(metadata.get('feature'))}</td>"
        f"<td>{safe(row.get('version') or metadata.get('prompt_version'))}</td>"
        f"<td>{safe(row.get('latency'))} s</td>"
        "</tr>"
    )


def page(title: str, subtitle: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe(title)}</title>
  <style>
    :root {{ color-scheme: light; --bg:#f5f7fb; --panel:#fff; --ink:#172235; --muted:#5d687b; --line:#d8dfeb; --accent:#126e98; --warn:#9a5700; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; padding:28px; background:var(--bg); color:var(--ink); font-family:Arial, sans-serif; letter-spacing:0; }}
    main {{ max-width:1400px; margin:0 auto; }}
    h1 {{ margin:0 0 8px; font-size:28px; }}
    h2 {{ margin:26px 0 10px; font-size:20px; }}
    .subtitle {{ color:var(--muted); line-height:1.5; }}
    .panel {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:20px; margin-top:18px; }}
    table {{ width:100%; border-collapse:collapse; font-size:14px; }}
    th, td {{ border-top:1px solid var(--line); padding:10px 8px; text-align:left; vertical-align:top; }}
    th {{ color:var(--muted); }}
    code, pre {{ font-family:Consolas, monospace; }}
    pre {{ background:#f0f3f8; padding:14px; overflow:auto; white-space:pre-wrap; }}
    .grid {{ display:grid; grid-template-columns:repeat(3, minmax(220px, 1fr)); gap:14px; }}
    .metric {{ border:1px solid var(--line); border-radius:8px; padding:14px; }}
    .label {{ color:var(--muted); font-size:13px; }}
    .value {{ color:var(--accent); font-size:25px; font-weight:700; margin-top:5px; }}
    .warn {{ color:var(--warn); }}
    @media (max-width:900px) {{ body {{ padding:14px; }} .grid {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body><main><h1>{safe(title)}</h1><div class="subtitle">{safe(subtitle)}</div>{body}</main></body>
</html>"""


def write_trace_list(rows: list[dict[str, Any]]) -> None:
    selected = sorted(roots(rows), key=lambda row: str(row.get("start_time")), reverse=True)[:20]
    body = (
        '<div class="panel"><div class="grid">'
        f'<div class="metric"><div class="label">Root traces found</div><div class="value">{len(roots(rows))}</div></div>'
        f'<div class="metric"><div class="label">Project</div><div class="value">day13-k4-l3a-2A202602383</div></div>'
        f'<div class="metric"><div class="label">Root observation</div><div class="value">lab-agent-run</div></div>'
        "</div></div>"
        '<div class="panel"><h2>Recent trace IDs</h2><table><thead><tr><th>Trace ID</th><th>Correlation ID</th><th>Session</th><th>Feature</th><th>Prompt version</th><th>Latency</th></tr></thead><tbody>'
        + "".join(trace_card(row) for row in selected)
        + "</tbody></table></div>"
    )
    (EVIDENCE_DIR / "06-trace-list.html").write_text(
        page(
            "Langfuse trace list evidence",
            "Read-only export from Langfuse v2 observations API. Raw user input and public-key metadata are omitted.",
            body,
        ),
        encoding="utf-8",
    )


def write_waterfall(rows: list[dict[str, Any]], trace_id: str) -> None:
    selected = [row for row in rows if row.get("trace_id") == trace_id]
    selected.sort(key=lambda row: str(row.get("start_time")))
    body_rows = []
    for row in selected:
        duration = float(row.get("latency") or 0)
        body_rows.append(
            "<tr>"
            f"<td>{safe(row.get('type'))}</td><td>{safe(row.get('name'))}</td>"
            f"<td>{safe(row.get('parent_observation_id'))}</td><td>{duration:.3f} s</td>"
            f"<td>{safe((row.get('metadata') or {}).get('correlation_id'))}</td>"
            "</tr>"
        )
    body = (
        f'<div class="panel"><div class="grid"><div class="metric"><div class="label">Trace ID</div><div class="value"><code>{safe(trace_id)}</code></div></div>'
        f'<div class="metric"><div class="label">Expected slow span</div><div class="value warn">retrieve-context</div></div>'
        f'<div class="metric"><div class="label">Correlation ID</div><div class="value">{safe(next(((r.get("metadata") or {}).get("correlation_id") for r in selected), ""))}</div></div></div></div>'
        '<div class="panel"><h2>Observation tree</h2><table><thead><tr><th>Type</th><th>Name</th><th>Parent observation</th><th>Duration</th><th>Correlation ID</th></tr></thead><tbody>'
        + "".join(body_rows)
        + "</tbody></table></div>"
    )
    (EVIDENCE_DIR / "07-trace-waterfall.html").write_text(
        page(
            "Langfuse trace waterfall evidence",
            "Real challenge trace from the personal Langfuse project.",
            body,
        ),
        encoding="utf-8",
    )


def write_metadata(rows: list[dict[str, Any]], trace_id: str) -> None:
    generation = next(
        row
        for row in rows
        if row.get("trace_id") == trace_id and row.get("type") == "GENERATION"
    )
    metadata = generation.get("metadata") or {}
    usage = generation.get("usage_details") or {}
    costs = generation.get("cost_details") or {}
    body = (
        '<div class="panel"><div class="grid">'
        f'<div class="metric"><div class="label">Trace ID</div><div class="value"><code>{safe(trace_id)}</code></div></div>'
        f'<div class="metric"><div class="label">Correlation ID</div><div class="value">{safe(metadata.get("correlation_id"))}</div></div>'
        f'<div class="metric"><div class="label">Prompt</div><div class="value">{safe(metadata.get("prompt_name"))} v{safe(metadata.get("prompt_version"))}</div></div>'
        f'<div class="metric"><div class="label">Model</div><div class="value">{safe(generation.get("model"))}</div></div>'
        f'<div class="metric"><div class="label">Tokens</div><div class="value">{safe(usage.get("input_tokens"))} in / {safe(usage.get("output_tokens"))} out</div></div>'
        f'<div class="metric"><div class="label">Cost</div><div class="value">${float(costs.get("total") or 0):.6f}</div></div>'
        "</div></div>"
        '<div class="panel"><h2>Safe metadata</h2><pre>'
        + safe(
            dump(
                {
                    "correlation_id": metadata.get("correlation_id"),
                    "feature": metadata.get("feature"),
                    "prompt_name": metadata.get("prompt_name"),
                    "prompt_label": metadata.get("prompt_label"),
                    "prompt_version": metadata.get("prompt_version"),
                    "model": generation.get("model"),
                    "usage_details": usage,
                    "cost_details": costs,
                    "latency_seconds": generation.get("latency"),
                }
            )
        )
        + "</pre></div>"
    )
    (EVIDENCE_DIR / "08-trace-metadata.html").write_text(
        page(
            "Langfuse trace metadata evidence",
            "Real generation observation metadata with input/output previews excluded.",
            body,
        ),
        encoding="utf-8",
    )


def write_prompt_versions(client: Any) -> None:
    meta = client.api.prompts.list(name=PROMPT_NAME, limit=20)
    versions = []
    for version in getattr(meta, "data", [])[0].versions:
        prompt = client.api.prompts.get(PROMPT_NAME, version=version)
        versions.append(prompt.model_dump())
    rows = "".join(
        "<tr>"
        f"<td>{safe(item.get('version'))}</td><td>{safe(', '.join(item.get('labels') or []))}</td>"
        f"<td>{safe(item.get('commit_message'))}</td><td><pre>{safe(item.get('prompt'))}</pre></td>"
        "</tr>"
        for item in versions
    )
    body = '<div class="panel"><h2>Prompt versions</h2><table><thead><tr><th>Version</th><th>Labels</th><th>Commit message</th><th>Template</th></tr></thead><tbody>' + rows + "</tbody></table></div>"
    (EVIDENCE_DIR / "09-prompt-versions.html").write_text(
        page(
            "Langfuse prompt versions evidence",
            "Prompt day13-chat queried from the personal Langfuse project.",
            body,
        ),
        encoding="utf-8",
    )


def write_rollback(client: Any, rows: list[dict[str, Any]]) -> None:
    production = client.api.prompts.get(PROMPT_NAME, label="production")
    version4 = next((row for row in rows if (row.get("metadata") or {}).get("prompt_version") == 4), None)
    version3 = next((row for row in rows if (row.get("metadata") or {}).get("prompt_version") == 3), None)
    body = (
        '<div class="panel"><h2>Rollback result</h2><div class="grid">'
        f'<div class="metric"><div class="label">Current production version</div><div class="value">{safe(production.version)}</div></div>'
        f'<div class="metric"><div class="label">Candidate version trace</div><div class="value"><code>{safe(version4.get("trace_id") if version4 else "not found")}</code></div></div>'
        f'<div class="metric"><div class="label">Rollback version trace</div><div class="value"><code>{safe(version3.get("trace_id") if version3 else "not found")}</code></div></div>'
        "</div></div>"
        '<div class="panel"><pre>'
        + safe(
            "1. promote version 4 to production\n"
            "2. run load test and observe prompt_version=4\n"
            "3. rollback production to version 3\n"
            "4. run load test and observe prompt_version=3\n"
        )
        + "</pre></div>"
    )
    (EVIDENCE_DIR / "10-prompt-rollback.html").write_text(
        page(
            "Langfuse prompt rollback evidence",
            "Current production label and real trace IDs from promote/rollback runs.",
            body,
        ),
        encoding="utf-8",
    )


def write_incident_trace(rows: list[dict[str, Any]], trace_id: str) -> None:
    write_waterfall(rows, trace_id)
    source = EVIDENCE_DIR / "07-trace-waterfall.html"
    target = EVIDENCE_DIR / "14-incident-trace.html"
    target.write_text(
        source.read_text(encoding="utf-8").replace(
            "Langfuse trace waterfall evidence",
            "Langfuse incident trace evidence",
        ),
        encoding="utf-8",
    )


def main() -> None:
    load_dotenv()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    client = get_client()
    rows = observation_rows(client)
    challenge_root = next(
        row
        for row in roots(rows)
        if (row.get("metadata") or {}).get("correlation_id") == "req-6116552c"
    )
    write_trace_list(rows)
    write_waterfall(rows, challenge_root["trace_id"])
    write_metadata(rows, challenge_root["trace_id"])
    write_prompt_versions(client)
    write_rollback(client, rows)
    write_incident_trace(rows, challenge_root["trace_id"])
    print(f"Exported Langfuse evidence for {len(roots(rows))} root traces")
    print(f"Challenge trace: {challenge_root['trace_id']}")


if __name__ == "__main__":
    main()
