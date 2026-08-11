# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: DaiSuQuanHanViet
- Repository URL: https://github.com/jaesungl33/Day13-K3-Observability-DaiSuQuanHanViet
- Commit SHA cuối: _(điền sau khi push)_
- Thành viên và vai trò:
  - Logging & PII / Tracing & Prompt Version / Dashboard, SLO & Alert / Incident, Report & Demo

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: **100/100** — `submission/evidence/validate_logs.txt`
- Tổng số traces Langfuse lấy mẫu: **17+** — `submission/evidence/langfuse_traces.json`, `submission/evidence/trace_list.txt`
- Số PII leak còn lại: **0**
- Dashboard:
  - Contract: `config/dashboard.yaml`
  - Runtime: `submission/evidence/dashboard.html`, `submission/evidence/dashboard.png`

## 3. Logging và tracing

- Evidence correlation ID: `submission/evidence/correlation_id_sample.json`
- Evidence PII redaction: `submission/evidence/pii_redaction_samples.json`
- Evidence Langfuse waterfall: `submission/evidence/langfuse_waterfall.json`
  - Trace ID ví dụ: `b45c6bf17e03d36e9219b3007f30523f`
  - Nested observations: `chat-turn` → `retrieve-context` + `generate-response`
- Giải thích span đáng chú ý:
  - Challenge `rag_slow` làm `retrieve-context` chậm (~2.5s); generation chỉ ~150ms. Metadata `latency_ms≈2684` và feature=`refund`.

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Version/label baseline: **v1 / baseline** (cũng gắn `production`)
- Version/label candidate: **v2 / candidate**
- Trace ID của mỗi version:
  - baseline v1: xem `submission/evidence/prompt_resolved_traces.json`
  - candidate v2: cùng file; metadata có `prompt_source=langfuse`
- Bằng chứng đổi label:
  - Chạy cùng input với `LANGFUSE_PROMPT_LABEL=baseline` và `candidate`
  - Trace metadata ghi đúng `prompt_version` 1 vs 2
  - Chi tiết: `submission/evidence/prompt_versioning_note.txt`
  - Script tạo prompt: `scripts/setup_langfuse_prompts.py`

## 5. Dashboard, SLO và alerts

- `validate_dashboard.py`: **HỢP LỆ: 6/6 panel**
- Evidence: `submission/evidence/dashboard.png`
- SLO: `config/slo.yaml` (P95≤3000ms, error≤2%, cost≤2.5, quality≥0.75)
- Alerts/runbook: `config/alert_rules.yaml`, `docs/alerts.md`

## 6. Điều tra challenge

- Challenge ID: `day13-k3-observability-v1`
- Triệu chứng metrics: P95 tăng mạnh khi bật `rag_slow` trên feature `refund`
- Trace ID liên quan: `b45c6bf17e03d36e9219b3007f30523f` (và các refund traces trong `langfuse_traces.json`)
- Correlation IDs: xem `submission/evidence/challenge_slow_responses.json`
- Root cause: `retrieve()` sleep 2.5s khi `STATE["rag_slow"]` (span `retrieve-context`)
- Fix action: disable incident; thêm timeout/circuit breaker cho retrieval
- Preventive measure: alert `high_latency_p95` + theo dõi P95 theo feature

## 7. Đóng góp cá nhân

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| DaiSuQuanHanViet | Logging/PII, nested Langfuse tracing, prompt v1/v2, dashboard/SLO/alerts, challenge report | fork `main` | Nested retriever/generation spans giúp khoanh vùng rag_slow nhanh hơn average latency |
