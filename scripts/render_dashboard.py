from __future__ import annotations

import argparse
import html
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
DEFAULT_OUTPUT = REPO_ROOT / "submission" / "evidence" / "11-dashboard-overview.html"


def parse_ts(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    items = sorted(values)
    idx = max(0, min(len(items) - 1, round((p / 100) * len(items) + 0.5) - 1))
    return float(items[idx])


def minute_key(record: dict[str, Any]) -> str:
    ts = parse_ts(str(record.get("ts", "")))
    if ts is None:
        return "unknown"
    return ts.astimezone(timezone.utc).strftime("%H:%M")


def fmt(value: float, digits: int = 1) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.{digits}f}"


def stat_card(title: str, value: str, unit: str, threshold: str, status: str) -> str:
    return f"""
      <div class="stat">
        <div class="stat-title">{html.escape(title)}</div>
        <div><span class="stat-value">{html.escape(value)}</span><span class="unit">{html.escape(unit)}</span></div>
        <div class="threshold">{html.escape(threshold)}</div>
        <div class="badge {html.escape(status.lower())}">{html.escape(status)}</div>
      </div>
    """


def render_dashboard(records: list[dict[str, Any]], output: Path, range_minutes: int) -> None:
    timestamps = [parse_ts(str(record.get("ts", ""))) for record in records]
    timestamps = [ts for ts in timestamps if ts is not None]
    latest = max(timestamps) if timestamps else datetime.now(timezone.utc)
    window_start = latest - timedelta(minutes=range_minutes)
    window_records = [
        record
        for record in records
        if (ts := parse_ts(str(record.get("ts", "")))) is not None and ts >= window_start
    ]

    requests = [r for r in window_records if r.get("event") == "request_received"]
    responses = [r for r in window_records if r.get("event") == "response_sent"]
    failures = [r for r in window_records if r.get("event") == "request_failed"]

    latencies = [float(r.get("latency_ms", 0)) for r in responses]
    ttfts = [float(r.get("ttft_ms", 0)) for r in responses]
    costs = [float(r.get("cost_usd", 0)) for r in responses]
    tokens_in = sum(int(r.get("tokens_in", 0)) for r in responses)
    tokens_out = sum(int(r.get("tokens_out", 0)) for r in responses)
    quality_values = [float(r.get("quality_score", 0)) for r in responses]

    traffic_count = len(requests)
    active_minutes = max(1, range_minutes)
    rate_per_minute = traffic_count / active_minutes
    error_rate = (len(failures) / traffic_count * 100) if traffic_count else 0.0
    retrieval_success = (
        sum(1 for r in responses if r.get("tool_success") is True) / len(responses) * 100
        if responses
        else 0.0
    )
    quality_avg = mean(quality_values) if quality_values else 0.0

    cost_by_minute: dict[str, float] = defaultdict(float)
    for record in responses:
        cost_by_minute[minute_key(record)] += float(record.get("cost_usd", 0))

    traffic_by_minute = Counter(minute_key(record) for record in requests)
    error_types = Counter(str(record.get("error_type", "unknown")) for record in failures)

    p95 = percentile(latencies, 95)
    total_cost = sum(costs)
    status_latency = "PASS" if p95 <= 3000 else "WARN"
    status_errors = "PASS" if error_rate <= 2 else "WARN"
    status_retrieval = "PASS" if retrieval_success >= 90 else "WARN"
    status_cost = "PASS" if total_cost <= 2.5 else "WARN"
    status_tokens = "PASS" if max(tokens_in, tokens_out) <= 50000 else "WARN"
    status_quality = "PASS" if quality_avg >= 0.75 else "WARN"

    rows_cost = "\n".join(
        f"<tr><td>{html.escape(minute)}</td><td>${value:.6f}</td></tr>"
        for minute, value in sorted(cost_by_minute.items())[-12:]
    )
    rows_traffic = "\n".join(
        f"<tr><td>{html.escape(minute)}</td><td>{count}</td></tr>"
        for minute, count in sorted(traffic_by_minute.items())[-12:]
    )
    error_breakdown = ", ".join(f"{key}: {value}" for key, value in error_types.items()) or "none"

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>K4-L3A Day 13 Dashboard</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8fb;
      --panel: #ffffff;
      --ink: #18212f;
      --muted: #5c667a;
      --line: #d9dfeb;
      --accent: #116f9a;
      --good: #0b7a4b;
      --warn: #a95d00;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
      letter-spacing: 0;
    }}
    header {{
      padding: 24px 32px 16px;
      border-bottom: 1px solid var(--line);
      background: #ffffff;
    }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    .meta {{ color: var(--muted); font-size: 14px; line-height: 1.6; }}
    main {{
      padding: 24px 32px 32px;
      display: grid;
      grid-template-columns: repeat(3, minmax(260px, 1fr));
      gap: 16px;
    }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      min-height: 250px;
    }}
    h2 {{ margin: 0 0 14px; font-size: 18px; }}
    .stat {{ border-top: 1px solid var(--line); padding: 12px 0; }}
    .stat:first-of-type {{ border-top: 0; }}
    .stat-title {{ color: var(--muted); font-size: 13px; margin-bottom: 4px; }}
    .stat-value {{ color: var(--accent); font-size: 34px; font-weight: 700; line-height: 1; }}
    .unit {{ margin-left: 6px; color: var(--muted); font-size: 13px; }}
    .threshold {{ color: var(--muted); font-size: 12px; margin-top: 6px; }}
    .badge {{ display: inline-block; margin-top: 8px; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: 700; }}
    .pass {{ color: var(--good); background: #e8f5ee; }}
    .warn {{ color: var(--warn); background: #fff3df; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
    td, th {{ border-top: 1px solid var(--line); padding: 7px 0; text-align: left; }}
    th {{ color: var(--muted); font-weight: 600; }}
    @media (max-width: 960px) {{ main {{ grid-template-columns: 1fr; padding: 16px; }} header {{ padding: 20px 16px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>K4-L3A Day 13 Monitoring & LLMOps Dashboard</h1>
    <div class="meta">
      Source: data/logs.jsonl | Time range: last {range_minutes} minutes from latest log |
      Latest log: {html.escape(latest.isoformat())} | Refresh: 30 seconds | Records in range: {len(window_records)}
    </div>
  </header>
  <main>
    <section>
      <h2>Latency percentiles and TTFT</h2>
      {stat_card("Latency P50", fmt(percentile(latencies, 50)), "ms", "Shown with P95/P99", "PASS")}
      {stat_card("Latency P95", fmt(p95), "ms", "Threshold: <= 3000 ms", status_latency)}
      {stat_card("Latency P99", fmt(percentile(latencies, 99)), "ms", "SLO guardrail", status_latency)}
      {stat_card("TTFT P95", fmt(percentile(ttfts, 95)), "ms", "Generation first-token proxy", "PASS")}
    </section>
    <section>
      <h2>Request traffic</h2>
      {stat_card("Requests", str(traffic_count), "count", "Event: request_received", "PASS")}
      {stat_card("Rate", f"{rate_per_minute:.2f}", "requests/min", "Threshold: >= 1 rpm during active test", "PASS" if rate_per_minute >= 1 else "WARN")}
      <table><thead><tr><th>Minute UTC</th><th>Requests</th></tr></thead><tbody>{rows_traffic}</tbody></table>
    </section>
    <section>
      <h2>Error rate and retrieval success</h2>
      {stat_card("Error rate", f"{error_rate:.2f}", "%", "Threshold: <= 2%", status_errors)}
      {stat_card("Retrieval success", f"{retrieval_success:.2f}", "%", "Threshold: >= 90%", status_retrieval)}
      <div class="threshold">Error breakdown: {html.escape(error_breakdown)}</div>
    </section>
    <section>
      <h2>Cost over time</h2>
      {stat_card("Total cost", f"${total_cost:.6f}", "USD", "Threshold: <= $2.50", status_cost)}
      {stat_card("Average cost", f"${(mean(costs) if costs else 0):.6f}", "USD/request", "Informational", "PASS")}
      <table><thead><tr><th>Minute UTC</th><th>Cost</th></tr></thead><tbody>{rows_cost}</tbody></table>
    </section>
    <section>
      <h2>Input and output tokens</h2>
      {stat_card("Input tokens", str(tokens_in), "tokens", "Threshold: <= 50000", status_tokens)}
      {stat_card("Output tokens", str(tokens_out), "tokens", "Threshold: <= 50000", status_tokens)}
    </section>
    <section>
      <h2>Quality proxy</h2>
      {stat_card("Average quality", f"{quality_avg:.2f}", "score 0-1", "Threshold: >= 0.75", status_quality)}
      {stat_card("Samples", str(len(quality_values)), "responses", "Event: response_sent", "PASS")}
    </section>
  </main>
</body>
</html>
""",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a local six-panel dashboard from JSONL logs.")
    parser.add_argument("--logs", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--range-minutes", type=int, default=60)
    args = parser.parse_args()

    records = load_records(args.logs)
    render_dashboard(records, args.output, args.range_minutes)
    print(f"Rendered dashboard: {args.output}")


if __name__ == "__main__":
    main()
