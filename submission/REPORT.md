# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Lê Nguyễn Thái Dương
- **MSSV:** 2A202602383
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/thaiduongpc7/K4-L3A-Day13-LeNguyenThaiDuong-2A202602383-Monitoring-LLMOps
- **Commit SHA cuối:** `8c19544b5a4eb24e656c81f664c0fdbdecb21398` (working tree has later uncommitted changes)
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
| Trace list | **Chưa xác nhận: API process chưa export được tới Langfuse Cloud** |
| Trace waterfall | **Chưa có evidence runtime** |
| Trace metadata | **Chưa có evidence runtime** |
| Prompt versions | **Chưa tạo/xác nhận trên Langfuse** |
| Prompt rollback | **Chưa có: chưa có trace/evidence runtime** |
| Dashboard runtime | `evidence/11-dashboard-overview.html` generated; capture `evidence/11-dashboard-overview.png` from browser |
| Incident metric | `evidence/12-incident-metric.txt` |
| Incident log | `evidence/13-incident-log.txt` |
| Incident trace | **Chưa có: API process chưa export được tới Langfuse Cloud** |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100; 20 missing required, 20 missing enrichment, 0 correlation IDs | 100/100; 0 missing required/enrichment, 154 correlation IDs | CP1 complete |
| `validate_dashboard.py` | 6/6 panels | 6/6 panels | Passed |
| `pytest` | 22 passed | 28 passed | All current tests pass |
| Số traces hợp lệ | 0; Langfuse chưa cấu hình | Chưa xác nhận; API process bị chặn outbound HTTPS | CP2 blocked by runtime network |
| Số PII leak | 0 detected | 0 detected | Verified across 312 current JSONL records |
| Latency P95 / TTFT P95 | 151 ms / 50 ms | 151 ms / 50 ms | From 10 CP1 requests |
| Retrieval success rate | 100% (10/10) | 100% (10/10) | `tool_success=true` on all responses |

### CP0 baseline

- Run date: 2026-09-29 (Asia/Bangkok).
- `GET http://127.0.0.1:8000/health` returned `ok: true`; the latest restart returned `tracing_enabled=true` after `.env` was filled.
- `data/logs.jsonl` was created with 21 JSONL records: 1 `app_started`, 10 `request_received`, and 10 `response_sent`.
- Runtime metrics after `python scripts/load_test.py`: traffic 10, latency P50/P95/P99 150/151/151 ms, TTFT P95 50 ms, total cost USD 0.0199, tokens in/out 338/1256, quality average 0.88.
- The log validator failure is expected at CP0 because correlation ID and log-enrichment TODOs are not implemented yet.
- Langfuse prompt settings and non-empty credentials are present in local `.env` (the file is ignored). A read-only request to `https://us.cloud.langfuse.com` was authenticated but the legacy trace endpoint returned `410 LEGACY_API_UNAVAILABLE_FOR_NEW_ORGANIZATION`; the v2 observations endpoint is the correct read path. The API process still could not export observations because sandbox outbound HTTPS returned `WinError 10013`. No secret or API key is recorded in this report.

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** middleware clears old context, accepts `x-request-id`, or generates `req-<8-hex>`, binds it, stores it in `request.state`, and returns it in `x-request-id` with `x-response-time-ms`.
- **Các metadata được ghi vào structured log:** `user_id_hash`, `session_id`, `feature`, `model`, `env`, correlation ID, latency, TTFT, token counts, cost, quality, retrieval status, and safe payload previews.
- **Cách bảo đảm PII được scrub trước khi ghi:** `scrub_event` recursively redacts strings before both `JsonlFileProcessor` and the final JSON renderer. Rules cover email, Vietnamese phone, CCCD, and payment-card formats.
- **Cách kiểm chứng kết quả:** the current `data/logs.jsonl` contains 312 records; `validate_logs.py` reports `100/100`, 154 unique correlation IDs, and 0 potential PII leaks. The clean validator output is saved in `evidence/02-log-validator.txt`.

## 5. Tracing và prompt versioning

- **Cấu trúc root/retrieval/generation observations:** `LabAgent.run` remains the root agent observation. It creates a `retriever` child for context lookup and a `generation` child for the mock LLM call.
- **Cách nối trace với log:** `correlation_id` is included in root metadata and both child observation metadata; it is the same ID emitted by structured logs.
- **Cách gửi trace:** Langfuse v4 uses the configured `LANGFUSE_BASE_URL` and OTEL ingestion path. The app uses small lab batches (`LANGFUSE_FLUSH_AT=1`, `LANGFUSE_FLUSH_INTERVAL=1`), flushes after each completed request, and flushes/shuts down the client during application shutdown.
- **Bảo vệ dữ liệu trace:** raw prompt/output are not captured. Trace input/output uses scrubbed previews, counts, prompt metadata, token usage, TTFT, and cost.
- **Prompt name:** `day13-chat` from `LANGFUSE_PROMPT_NAME`.
- **Version/label baseline:** `production` from `LANGFUSE_PROMPT_LABEL`; resolved prompt version is stored in root and generation metadata.
- **Version/label candidate:** Chưa tạo/xác nhận trên Langfuse because the API process could not reach the Cloud prompt/OTEL endpoints from the sandbox.
- **Trace ID của mỗi version:** Chưa có; không được bịa trace ID hoặc dùng evidence của người khác.
- **Cách promote và rollback `production`:** manage `baseline` and `candidate` versions in Langfuse, run the same sample queries, then move the `production` label to the chosen version. Rollback is the same label move back to the previous version; record both trace IDs in the evidence section.
- **Kiểm chứng:** `tests/test_agent_observations.py` verifies child types, correlation metadata, usage/cost fields, prompt reference, and PII-safe trace fields. The API reported `tracing_enabled=true`, but prompt fetch and OTEL export failed with `WinError 10013` from the sandbox, so the 10-trace and prompt rollback requirements remain unverified.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** `config/dashboard.yaml` keeps exactly six panels backed by `data/logs.jsonl`: latency with P50/P95/P99/TTFT, traffic, errors plus retrieval success, cost, tokens, and quality. The errors query now reads `response_sent.tool_success`. A local runtime dashboard can be generated with `python scripts/render_dashboard.py` and opened from `submission/evidence/11-dashboard-overview.html`.
- **SLO và lý do chọn:** 99.5% of requests must complete within 3000 ms with successful retrieval over 28 days. This matches the existing latency threshold and treats failed retrieval as user-visible degradation.
- **Cách tính error budget:** `100% - 99.5% = 0.5%`; over 28 days this is `40320 * 0.005 = 201.6` allowed bad minutes, with the same 0.5% bad-request ratio.
- **Ba alert và runbook tương ứng:** `user_latency_p95_high`, `request_error_rate_high`, and `retrieval_success_degraded` are symptom-based alerts with duration, severity, owner, Slack channel, and links to `docs/alerts.md`.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`; cohort `K4`; Lab Coach file used directly from `config/challenge.json`; incident `rag_slow`; affected feature `monitoring`; challenge latency threshold `2000 ms`.
- **Khoảng thời gian điều tra:** 2026-09-29 20:06:17-20:06:34 Asia/Bangkok. The challenge request logs ran from `2026-09-29T13:06:17Z` to `2026-09-29T13:06:34Z`.
- **Triệu chứng từ metrics:** dashboard panel `latency` / `/metrics` showed traffic `5`, latency P50/P95/P99 `2652/3641/3641 ms`, TTFT P95 `50 ms`, `error_breakdown={}`, quality average `0.84`, and total cost `0.0096 USD`. Latency P95 exceeded the challenge threshold `2000 ms`, while TTFT, errors, quality, and cost stayed normal.
- **Log line và correlation ID liên quan:** representative abnormal request `req-e6bb77cb` in `data/logs.jsonl`. The request used feature `monitoring`, session `k4-l3a-challenge-s02`, and response logged `latency_ms=3641`, `ttft_ms=50`, `tool_name=retrieval`, `tool_success=true`.
- **Trace ID và span gây ảnh hưởng:** still needs the Langfuse Cloud runtime screenshot/trace ID. Run Uvicorn from a local terminal with outbound HTTPS allowed, rerun the same challenge, and record the trace with the selected `correlation_id`; compare root `lab-agent-run`, child `retrieve-context` (`retriever`), and child `llm-generate` (`generation`). The expected slow span is `retrieve-context`, but this must be confirmed by the actual trace.
- **Root cause:** the Lab Coach challenge enabled `rag_slow`. In `app/mock_rag.py`, `retrieve()` checks `STATE["rag_slow"]` and sleeps for `2.5` seconds before returning documents, adding about 2500 ms to each affected monitoring request.
- **Fix action:** disable the incident with `python scripts/inject_incident.py --disable` or `POST /incidents/rag_slow/disable`, then rerun the load test and confirm latency P95 returns below `2000 ms`.
- **Preventive measure:** add a retrieval-span duration alert/runbook and require Langfuse credentials before CP3 so every abnormal log correlation ID can be joined to a concrete trace ID and span waterfall. Do not mark the incident complete until the trace evidence exists.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** giữ structured logs ở JSONL và truyền cùng `correlation_id` qua middleware để nối request, metrics và trace metadata mà không ghi raw PII.
- **Một lỗi/blocker đã gặp:** `WinError 10061` xảy ra khi chạy script trước khi Uvicorn được khởi động. Sau đó API báo `tracing_enabled=true`, nhưng process sandbox bị `WinError 10013` khi fetch prompt và export OTEL traces ra Langfuse Cloud.
- **Cách tìm nguyên nhân và xử lý:** metrics cho thấy P95 tăng lên `3641 ms`; log chọn `req-e6bb77cb`; source cho thấy `rag_slow` thêm `2.5 s` trong retrieval. Incident đã được disable; trace cần được xác nhận sau khi chạy API ở môi trường cho phép outbound HTTPS.
- **Cách hiểu luồng Metrics → Logs → Traces:** metrics khoanh vùng triệu chứng/thời gian, logs xác định request qua correlation ID, trace phân rã duration/status theo span, rồi mới kết luận root cause.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** prompt version giúp truy vết thay đổi, token/cost phát hiện tiêu thụ bất thường, SLO/error budget định lượng ảnh hưởng, còn rollback đưa label production về version ổn định.
- **Điều quan trọng nhất đã học:** validator pass không thay thế runtime evidence; incident chỉ hoàn chỉnh khi metric, log và trace cùng nối tới một request.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** credentials đã điền và được Cloud nhận diện, nhưng process hiện tại bị chặn outbound HTTPS; vì vậy chưa có 10 trace IDs, prompt v1/v2, rollback evidence và incident trace. Local dashboard runtime HTML đã tạo, nhưng PNG screenshot vẫn cần chụp trong browser. Bài chưa đáp ứng đầy đủ rubric cho tới khi có runtime trace/prompt screenshots thật.

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [x] Các output validator hiện có dùng đường dẫn tương đối trong report.
- [ ] Incident evidence nối đủ metric → log → trace; hiện còn thiếu trace ID.
- [x] Repository chạy lại được theo flow API/load test/validators.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác trong working tree được kiểm tra.
- [ ] Có đủ 10 trace IDs, trace waterfall, prompt rollback và dashboard runtime evidence.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
