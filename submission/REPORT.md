# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: DaiSuQuanHanViet
- Repository URL: https://github.com/jaesungl33/Day13-K3-Observability-DaiSuQuanHanViet
- Commit SHA cuối: 46a7b4685808521dbfcb0284a6702505da7ef731
- Thành viên và vai trò:
  - **Vũ Đức Duy - 2A202601023 — SRE & Alerts Engineer:** Phụ trách CP2 (Cấu hình Langfuse, thiết lập SLO/Alert Rules, viết tài liệu Alert Runbook).

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: **100/100** — `submission/evidence/validate_logs.txt`
- Test tự động: **22/22 passed** — `submission/evidence/pytest.xml`
- Runtime load test: **10/10 HTTP 200** — `submission/evidence/load_test.txt`
- Langfuse SDK: **3.15.0**, tương thích contract `<4` — `submission/evidence/sdk_version.txt`
- Tổng số traces Langfuse lấy mẫu: **17+** — `submission/evidence/langfuse_traces.json`, `submission/evidence/trace_list.txt`
- Ảnh danh sách Langfuse: `submission/evidence/langfuse_trace_list.png` (giao diện hiển thị 27 root observations / 54 observations `chat-turn`)
- Số PII leak còn lại: **0**
- Dashboard:
  - Contract: `config/dashboard.yaml`
  - Runtime: `submission/evidence/dashboard.html`, `submission/evidence/dashboard.png`

## 3. Logging và tracing

- Evidence correlation ID: `submission/evidence/correlation_id_sample.json`
- Evidence PII redaction: `submission/evidence/pii_redaction_samples.json`
- Evidence Langfuse waterfall: `submission/evidence/langfuse_waterfall.json`, `submission/evidence/langfuse_trace_waterfall.png`
  - Trace ID ví dụ: `b45c6bf17e03d36e9219b3007f30523f`
  - Nested observations: `chat-turn` → `retrieve-context` + `generate-response`
  - Audit theo Langfuse best practices: một trace cho mỗi chat turn; tên span ổn định và theo hành động; generation có model/token/cost; root có input/output, session/user/tags; correlation ID nằm trong metadata.
- Giải thích span đáng chú ý:
  - Challenge `rag_slow` làm `retrieve-context` chậm (~2.5s); generation chỉ ~150ms. Metadata `latency_ms≈2684` và feature=`refund`.

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Version/label baseline: **v1 / baseline** (cũng gắn `production`)
- Version/label candidate: **v2 / candidate**
- Trace ID của mỗi version:
  - baseline v1: `9d0cb651246df3cb623512c10d13e043`
  - candidate v2: `a910b1f54ec4227699e01e983807c6d0`
  - Metadata kiểm chứng: `submission/evidence/prompt_resolved_traces.json`
- Bằng chứng đổi label:
  - Chạy cùng input với `LANGFUSE_PROMPT_LABEL=baseline` và `candidate`
  - Trace metadata ghi đúng `prompt_version` 1 vs 2
  - Ảnh candidate v2: `submission/evidence/langfuse_prompt_candidate_v2.png`
  - Ảnh sau rollback: `submission/evidence/langfuse_prompt_versions_after_rollback.png` — version 2 giữ `candidate`, còn `production` đã trở về version 1 cùng `baseline`
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

## 7. Giới hạn runtime đã quan sát

- Lần load test xác minh cuối có 10/10 HTTP 200 và validator log đạt 100/100.
- Langfuse Cloud đã timeout khi fetch prompt/export trace trong lần chạy cuối, nên app dùng `local-fallback` theo thiết kế. Không tuyên bố các request xác minh cuối đã tạo trace cloud mới; evidence trace/prompt dùng các trace ID Langfuse đã thu thập trước đó và được lưu trong `submission/evidence/`.

## 8. Đóng góp cá nhân

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Vũ Đức Duy - 2A202601023 | SRE & Alerts Engineer — CP2: cấu hình Langfuse, thiết lập SLO/Alert Rules, viết tài liệu Alert Runbook | fork `main` | Nested retriever/generation spans giúp khoanh vùng rag_slow nhanh hơn average latency |
