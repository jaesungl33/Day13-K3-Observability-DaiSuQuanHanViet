# Khung thiết kế Observability

Dùng khung này trước khi triển khai, sau đó chuyển kết quả cuối sang `submission/REPORT.md`.

## Người dùng và luồng chính

- Ai gửi request? Client/load-test gửi `POST /chat` với `user_id`, `session_id`, `feature`, `message`.
- Request đi qua những thành phần nào? Middleware → API `/chat` → Agent → RAG retrieve → Prompt resolve → Fake LLM → metrics/logs/traces.
- Correlation ID được tạo và truyền ở đâu? `CorrelationIdMiddleware` đọc/ghi `x-request-id`, bind vào structlog contextvars, trả lại header và `ChatResponse.correlation_id`.

## Tín hiệu quan sát

| Thành phần | Log cần có | Metric cần có | Span cần có |
|---|---|---|---|
| API | `request_received`, `response_sent`, `request_failed` + enrichment | traffic, latency, errors | request root |
| Retrieval | query preview (đã scrub) | retrieval latency (qua total latency) | retrieve span |
| LLM | tokens/cost/quality trên `response_sent`; `prompt_resolved` | tokens, cost, quality | generation span + prompt metadata |

## SLO và alert

| SLI | Mục tiêu | Cửa sổ đo | Alert |
|---|---:|---|---|
| Latency P95 | ≤ 3000ms | 5m / 28d | high_latency_p95 |
| Error rate | ≤ 2% | 5m / 28d | elevated_error_rate |
| Cost | ≤ 2.5 USD/ngày | 15m / 28d | daily_cost_budget_breach |
| Quality | ≥ 0.75 mean | 60m dashboard | review qua dashboard |

## Rủi ro dữ liệu

- PII có thể xuất hiện ở đâu? `message`, answer preview, payload log.
- Dữ liệu nào được phép ghi vào log? Hash user id, session id, feature, model, scrubbed preview, metrics.
- Redaction diễn ra trước bước nào? Processor `scrub_event` chạy trước khi JSON được render/ghi file.
