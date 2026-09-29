# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Lê Nguyễn Thái Dương
- **MSSV:** 2A202602383
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/thaiduongpc7/K4-L3A-Day13-LeNguyenThaiDuong-2A202602383-Monitoring-LLMOps
- **Commit SHA cuối:** cập nhật sau commit cuối bằng `git log -1 --format=%H`
- **Challenge ID:** day13-k4-l3a-monitoring-llmops-v1

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.txt` |
| Log validator | `evidence/02-log-validator.txt` |
| Dashboard validator | `evidence/03-dashboard-validator.txt` |
| Structured log | `evidence/04-structured-log.txt` |
| PII redaction | `evidence/05-pii-redaction.txt` |
| Trace list | `evidence/langfuse_project.png` và `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.txt` |
| Incident log | `evidence/13-incident-log.txt` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100; 20 missing required, 20 missing enrichment, 0 correlation IDs | 100/100; 0 missing required/enrichment, 181 correlation IDs | CP1 complete |
| `validate_dashboard.py` | 6/6 panels | 6/6 panels | Passed |
| `pytest` | 22 passed | 28 passed | All current tests pass |
| Số traces hợp lệ | 0; Langfuse chưa cấu hình | 90 root traces trong project cá nhân | CP2 complete |
| Số PII leak | 0 detected | 0 detected | Verified across 365 current JSONL records |
| Latency P95 / TTFT P95 | 151 ms / 50 ms | 151 ms / 50 ms | From 10 CP1 requests |
| Retrieval success rate | 100% (10/10) | 100% (10/10) | `tool_success=true` on all responses |

### CP0 baseline

- Run date: 2026-09-29 (Asia/Bangkok).
- `GET http://127.0.0.1:8000/health` returned `ok: true`; the latest restart returned `tracing_enabled=true` after `.env` was filled.
- `data/logs.jsonl` was created with 21 JSONL records: 1 `app_started`, 10 `request_received`, and 10 `response_sent`.
- Runtime metrics after `python scripts/load_test.py`: traffic 10, latency P50/P95/P99 150/151/151 ms, TTFT P95 50 ms, total cost USD 0.0199, tokens in/out 338/1256, quality average 0.88.
- The log validator failure is expected at CP0 because correlation ID and log-enrichment TODOs are not implemented yet.
- Langfuse prompt settings and non-empty credentials are present in local `.env` (the file is ignored). The project dashboard showed 10 traces and the Langfuse v2 observations API confirmed the runtime observations. No secret or API key is recorded in this report.

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** middleware clears old context, accepts `x-request-id`, or generates `req-<8-hex>`, binds it, stores it in `request.state`, and returns it in `x-request-id` with `x-response-time-ms`.
- **Các metadata được ghi vào structured log:** `user_id_hash`, `session_id`, `feature`, `model`, `env`, correlation ID, latency, TTFT, token counts, cost, quality, retrieval status, and safe payload previews.
- **Cách bảo đảm PII được scrub trước khi ghi:** `scrub_event` recursively redacts strings before both `JsonlFileProcessor` and the final JSON renderer. Rules cover email, Vietnamese phone, CCCD, and payment-card formats.
- **Cách kiểm chứng kết quả:** the current `data/logs.jsonl` contains 365 records; `validate_logs.py` reports `100/100`, 181 unique correlation IDs, and 0 potential PII leaks. The clean validator output is saved in `evidence/02-log-validator.txt`.

## 5. Tracing và prompt versioning

- **Cấu trúc root/retrieval/generation observations:** `LabAgent.run` remains the root agent observation. It creates a `retriever` child for context lookup and a `generation` child for the mock LLM call.
- **Cách nối trace với log:** `correlation_id` is included in root metadata and both child observation metadata; it is the same ID emitted by structured logs.
- **Cách gửi trace:** Langfuse v4 uses the configured `LANGFUSE_BASE_URL` and OTEL ingestion path. The app uses small lab batches (`LANGFUSE_FLUSH_AT=1`, `LANGFUSE_FLUSH_INTERVAL=1`), flushes after each completed request, and flushes/shuts down the client during application shutdown.
- **Bảo vệ dữ liệu trace:** raw prompt/output are not captured. Trace input/output uses scrubbed previews, counts, prompt metadata, token usage, TTFT, and cost.
- **Prompt name:** `day13-chat` from `LANGFUSE_PROMPT_NAME`.
- **Version/label baseline:** `production` from `LANGFUSE_PROMPT_LABEL`; resolved prompt version is stored in root and generation metadata.
- **Version/label candidate:** Langfuse prompt `day13-chat` has versions 1–4. Version 3 carries `baseline, production`; version 4 carries `candidate, latest` after rollback.
- **Trace ID của mỗi version:** challenge trace `d58f1161fa5c2bd9ca3e8a0dfb113b85` used production version 3. Candidate trace `d7052d26ca089057bb33981ed9eb6519` used version 4. Rollback trace `98223f10682bf018f50e996e42a18561` used version 3 again.
- **Cách promote và rollback `production`:** promoted version 4, ran the same load-test workflow, rolled production back to version 3, then ran the workflow again. Evidence is exported from Langfuse v2 observations and prompt APIs without raw input/output or credentials.
- **Kiểm chứng:** `tests/test_agent_observations.py` verifies child types, correlation metadata, usage/cost fields, prompt reference, and PII-safe trace fields. Runtime evidence confirms 90 root traces, retrieval/generation children, prompt versions, token usage and cost.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** `config/dashboard.yaml` keeps exactly six panels backed by `data/logs.jsonl`: latency with P50/P95/P99/TTFT, traffic, errors plus retrieval success, cost, tokens, and quality. The errors query now reads `response_sent.tool_success`. Runtime evidence is in `evidence/11-dashboard-overview.png`.
- **SLO và lý do chọn:** 99.5% of requests must complete within 3000 ms with successful retrieval over 28 days. This matches the existing latency threshold and treats failed retrieval as user-visible degradation.
- **Cách tính error budget:** `100% - 99.5% = 0.5%`; over 28 days this is `40320 * 0.005 = 201.6` allowed bad minutes, with the same 0.5% bad-request ratio.
- **Ba alert và runbook tương ứng:** `user_latency_p95_high`, `request_error_rate_high`, and `retrieval_success_degraded` are symptom-based alerts with duration, severity, owner, Slack channel, and links to `docs/alerts.md`.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`; cohort `K4`; Lab Coach file used directly from `config/challenge.json`; incident `rag_slow`; affected feature `monitoring`; challenge latency threshold `2000 ms`.
- **Khoảng thời gian điều tra:** 2026-09-29 20:06:17-20:06:34 Asia/Bangkok. The challenge request logs ran from `2026-09-29T13:06:17Z` to `2026-09-29T13:06:34Z`.
- **Triệu chứng từ metrics:** dashboard panel `latency` / `/metrics` showed traffic `5`, latency P50/P95/P99 `2652/3641/3641 ms`, TTFT P95 `50 ms`, `error_breakdown={}`, quality average `0.84`, and total cost `0.0096 USD`. Latency P95 exceeded the challenge threshold `2000 ms`, while TTFT, errors, quality, and cost stayed normal.
- **Log line và correlation ID liên quan:** representative abnormal request `req-6116552c` in `data/logs.jsonl`. The request used feature `monitoring`, session `k4-l3a-challenge-s04`, and response logged `latency_ms=2652`, `ttft_ms=50`, `tool_name=retrieval`, `tool_success=true`.
- **Trace ID và span gây ảnh hưởng:** trace `d58f1161fa5c2bd9ca3e8a0dfb113b85` has correlation ID `req-6116552c`. Root `lab-agent-run` lasted `2.653 s`; child `retrieve-context` lasted `2.500 s`; child `llm-generate` lasted `0.152 s`. The retrieval span is the bottleneck.
- **Root cause:** the Lab Coach challenge enabled `rag_slow`. In `app/mock_rag.py`, `retrieve()` checks `STATE["rag_slow"]` and sleeps for `2.5` seconds before returning documents, adding about 2500 ms to each affected monitoring request.
- **Fix action:** disable the incident with `python scripts/inject_incident.py --disable` or `POST /incidents/rag_slow/disable`, then rerun the load test and confirm latency P95 returns below `2000 ms`.
- **Preventive measure:** add a retrieval-span duration alert/runbook and require Langfuse credentials before CP3 so every abnormal log correlation ID can be joined to a concrete trace ID and span waterfall. Do not mark the incident complete until the trace evidence exists.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** giữ structured logs ở JSONL và truyền cùng `correlation_id` qua middleware để nối request, metrics và trace metadata mà không ghi raw PII.
- **Một lỗi/blocker đã gặp:** `WinError 10061` xảy ra khi chạy script trước khi Uvicorn được khởi động. Sau đó API báo `tracing_enabled=true`, nhưng process sandbox bị `WinError 10013` khi fetch prompt và export OTEL traces ra Langfuse Cloud.
- **Cách tìm nguyên nhân và xử lý:** metrics cho thấy P95 tăng lên `3641 ms`; log chọn `req-6116552c`; trace `d58f1161fa5c2bd9ca3e8a0dfb113b85` với cùng correlation ID cho thấy retrieval mất `2.500 s` trong khi generation chỉ mất `0.152 s`. Source xác nhận `rag_slow` thêm `2.5 s` trong retrieval. Incident đã được disable.
- **Cách hiểu luồng Metrics → Logs → Traces:** metrics khoanh vùng triệu chứng/thời gian, logs xác định request qua correlation ID, trace phân rã duration/status theo span, rồi mới kết luận root cause.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** prompt version giúp truy vết thay đổi, token/cost phát hiện tiêu thụ bất thường, SLO/error budget định lượng ảnh hưởng, còn rollback đưa label production về version ổn định.
- **Điều quan trọng nhất đã học:** validator pass không thay thế runtime evidence; incident chỉ hoàn chỉnh khi metric, log và trace cùng nối tới một request.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Langfuse Cloud legacy trace-list API của project mới trả 410, nên evidence trace list/metadata được xuất qua v2 observations API; project UI screenshot vẫn được lưu. Challenge file được giữ local và không commit theo quy định.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Các output validator hiện có dùng đường dẫn tương đối trong report.
- [x] Incident evidence nối đủ metric → log → trace bằng `req-6116552c`.
- [x] Repository chạy lại được theo flow API/load test/validators.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác trong working tree được kiểm tra.
- [x] Có đủ 10 trace IDs, trace waterfall, prompt rollback và dashboard runtime evidence.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
