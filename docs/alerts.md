# Alerts and Runbooks

Each alert is symptom-based: it describes what users or the SLO experience, not
an internal implementation name. All notifications go to Slack channel
`#llmops-alerts`.

## Alert 1

- Name: `user_latency_p95_high`
- Severity: Critical
- Duration: 10 minutes
- Condition: `latency_p95_ms > 3000`
- SLI/SLO: fast successful requests, with a 3000 ms latency objective
- User impact: requests feel slow or time out before an answer is useful
- First checks:
  1. Check the latency panel for P50, P95, P99, and TTFT, then note the start time.
  2. Compare `response_sent` logs by `correlation_id` and inspect retrieval versus generation spans.
  3. Check whether the affected feature or incident window has a concentrated increase.
- Temporary mitigation: reduce load or concurrency, disable a known slow feature or incident, and keep a sample correlation ID for follow-up.
- Owner: `api-oncall`
- Runbook: inspect `data/logs.jsonl`, then follow the matching trace from the
  same `correlation_id`. Restore normal traffic only after P95 remains below
  3000 ms for the alert duration.

## Alert 2

- Name: `request_error_rate_high`
- Severity: Critical
- Duration: 5 minutes
- Condition: `error_rate_pct > 2`
- SLI/SLO: request success and error-budget consumption
- User impact: users receive failed requests instead of an answer
- First checks:
  1. Use the errors panel to identify the error type and affected time range.
  2. Find a failed log line and its `correlation_id`; verify whether retrieval or generation failed.
  3. Check recent configuration, dependency, and incident changes.
- Temporary mitigation: disable the affected practice incident, route traffic to a
  healthy fallback, or reduce request volume while preserving failed-request
  evidence.
- Owner: `platform-oncall`
- Runbook: page the owner in Slack, link the error sample and trace, and watch
  the error rate until it is at or below 2% for 5 minutes.

## Alert 3

- Name: `retrieval_success_degraded`
- Severity: Warning
- Duration: 5 minutes
- Condition: `retrieval_success_rate_pct < 90`
- SLI/SLO: retrieval success guardrail
- User impact: answers may be incomplete, less relevant, or fall back to generic context
- First checks:
  1. Compare `response_sent.tool_success` with `request_failed.tool_name` in the errors panel.
  2. Select failed requests and trace the retrieval observation using `correlation_id`.
  3. Check retrieval latency, dependency health, and the number of fallback answers.
- Temporary mitigation: use the safe fallback context, reduce retrieval traffic,
  or disable the affected retrieval path until dependency health recovers.
- Owner: `retrieval-oncall`
- Runbook: keep one successful and one failed correlation ID, verify recovery at
  90% or higher for 5 minutes, and then document the dependency cause.

## Error budget calculation

The primary SLO target is 99.5% over 28 days, so the error budget is 0.5%.
There are `28 * 24 * 60 = 40320` minutes in the window:

```text
40320 * 0.005 = 201.6 allowed bad minutes
```

The same 0.5% ratio applies to bad requests when request volume is the more
useful denominator. Slow responses and retrieval failures both consume the
budget because they are not good events for the primary SLO.
