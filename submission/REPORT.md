# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: Đại Sứ Quán Hàn Việt
- Repository URL: https://github.com/jaesungl33/Day13-K3-Observability-DaiSuQuanHanViet
- Commit SHA cuối: 650e18d9385816fbcfb12b85b824ee4d9289455e
- Lead: Lee Jae Sung
- Thành viên và vai trò:

| Thành viên | Vai trò | Checkpoint chính |
|---|---|---|
| Lee Jae Sung | Tech Lead / Backend Engineer | CP1 — Middleware, Correlation ID, Enrichment logs, PII scrubbing |
| Vũ Đức Duy | SRE & Alerts Engineer | CP2 — Langfuse tracing/prompt version, SLO, Alert Rules, Runbook |
| Dương Hoàng Lâm | QA & Chief Investigator | CP3 — Dashboard spec/runtime, load test, challenge/practice incident, tổng hợp báo cáo |

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: **100/100** — `submission/evidence/validate_logs.txt`
- Tổng số traces Langfuse lấy mẫu: **17+** — `submission/evidence/langfuse_traces.json`, `submission/evidence/trace_list.txt`
- Số PII leak còn lại: **0**
- Dashboard:
  - Contract: `config/dashboard.yaml`
  - Runtime: `submission/evidence/dashboard.html`, `submission/evidence/dashboard.png`

## 3. Logging và tracing (CP1 + một phần CP2)

Owner chính CP1: **Lee Jae Sung**

- Evidence correlation ID: `submission/evidence/correlation_id_sample.json`
- Evidence PII redaction: `submission/evidence/pii_redaction_samples.json`
- Evidence Langfuse waterfall: `submission/evidence/langfuse_waterfall.json`
  - Trace ID ví dụ: `b45c6bf17e03d36e9219b3007f30523f`
  - Nested observations: `chat-turn` → `retrieve-context` + `generate-response`
- Giải thích span đáng chú ý:
  - Challenge `rag_slow` làm `retrieve-context` chậm (~2.5s); generation chỉ ~150ms. Metadata `latency_ms≈2684` và feature=`refund`.

## 4. Prompt versioning (CP2)

Owner chính: **Vũ Đức Duy**

- Prompt name: `day13-chat`
- Version/label baseline: **v1 / baseline** (cũng gắn `production`)
- Version/label candidate: **v2 / candidate**
- Trace ID của mỗi version:
  - baseline v1 / candidate v2: `submission/evidence/prompt_resolved_traces.json`
  - metadata có `prompt_source=langfuse`
- Bằng chứng đổi label:
  - Chạy cùng input với `LANGFUSE_PROMPT_LABEL=baseline` và `candidate`
  - Trace metadata ghi đúng `prompt_version` 1 vs 2
  - Chi tiết: `submission/evidence/prompt_versioning_note.txt`
  - Script tạo prompt: `scripts/setup_langfuse_prompts.py`

## 5. Dashboard, SLO và alerts (CP2 + CP3)

- Dashboard (CP3 — **Dương Hoàng Lâm**):
  - `validate_dashboard.py`: **HỢP LỆ: 6/6 panel**
  - Evidence: `submission/evidence/dashboard.png`, `submission/evidence/dashboard.html`
  - Spec/contract: `config/dashboard.yaml`, `docs/dashboard-spec.md`, `docs/DASHBOARD_SETUP.md`
- SLO & Alerts (CP2 — **Vũ Đức Duy**):
  - SLO: `config/slo.yaml` (P95≤3000ms, error≤2%, cost≤2.5, quality≥0.75)
  - Alert rules: `config/alert_rules.yaml`
  - Runbook: `docs/alerts.md`

## 6. Điều tra challenge (CP3)

Owner chính: **Dương Hoàng Lâm**

- Challenge ID: `day13-k3-observability-v1`
- Triệu chứng metrics: P95 tăng mạnh khi bật `rag_slow` trên feature `refund`
- Trace ID liên quan: `b45c6bf17e03d36e9219b3007f30523f` (và các refund traces trong `langfuse_traces.json`)
- Correlation IDs: `submission/evidence/challenge_slow_responses.json`
- Root cause: `retrieve()` sleep 2.5s khi `STATE["rag_slow"]` (span `retrieve-context`)
- Fix action: disable incident; thêm timeout/circuit breaker cho retrieval
- Preventive measure: alert `high_latency_p95` + theo dõi P95 theo feature
- Luồng điều tra: Metrics → Traces → Logs → Root cause

## 7. Phân công và đóng góp cá nhân

| Thành viên | Vai trò | Phần việc cụ thể | Evidence / file chính | Commit/PR | Điều đã học |
|---|---|---|---|---|---|
| Lee Jae Sung | Tech Lead / Backend (CP1) | Middleware clear/bind correlation ID; response headers; enrich `user_id_hash`, `session_id`, `feature`, `model`, `env`; PII scrub processor; nền tảng API logging | `app/middleware.py`, `app/main.py`, `app/logging_config.py`, `app/pii.py`, `submission/evidence/correlation_id_sample.json`, `submission/evidence/pii_redaction_samples.json` | `46a7b46`, `32d8988` | Correlation ID phải được bind trước mọi log API, nếu không waterfall Metrics→Logs bị gãy |
| Vũ Đức Duy | SRE & Alerts (CP2) | Cấu hình Langfuse keys/host; nested tracing + prompt v1/v2; SLO; alert rules; runbook; kiểm chứng evidence Langfuse | `app/tracing.py`, `app/agent.py`, `scripts/setup_langfuse_prompts.py`, `config/slo.yaml`, `config/alert_rules.yaml`, `docs/alerts.md`, `submission/evidence/langfuse_traces.json`, `submission/evidence/prompt_versioning_note.txt` | `eeba0cb`, `2776c8c` | Prompt label/version trên trace giúp rollback an toàn mà không cần đoán từ log thô |
| Dương Hoàng Lâm | QA & Chief Investigator (CP3) | Dashboard 6 panel + validator; load test baseline/challenge; inject/điều tra incident `rag_slow`; RAG Circuit Breaker; Audit Log; SLO Evaluator; Cost Optimization; CI/CD; tổng hợp `REPORT.md` | `config/dashboard.yaml`, `scripts/render_dashboard.py`, `scripts/load_test.py`, `scripts/inject_incident.py`, `scripts/evaluate_slo.py`, `docs/cost-optimization.md`, `.github/workflows/ci.yml`, `submission/evidence/dashboard.png`, `submission/evidence/challenge_*`, `submission/REPORT.md` | `0ad707b` | P95 và span retrieval chứng minh root cause rõ hơn average latency; RAG Timeout & Audit Log giúp bảo đảm SLO |

### Checklist bàn giao theo vai trò

1. **CP1 (Lee Jae Sung)** — `python scripts/validate_logs.py` ≥ 80/100; log có correlation ID + enrichment + PII đã redact.
2. **CP2 (Vũ Đức Duy)** — ≥10 traces Langfuse; prompt baseline/candidate khác version; SLO + 3 alerts + runbook.
3. **CP3 (Dương Hoàng Lâm)** — dashboard 6/6; challenge Metrics→Traces→Logs; report đầy đủ 3 thành viên; Bonus audit log, RAG circuit breaker, SLO evaluator, cost report & CI/CD.

## 8. Hạng mục Bonus (Cải tiến & Tối ưu hóa - CP3)

1. **Audit Log riêng (`data/audit.jsonl`)**: Triển khai logger kiểm toán độc lập ghi nhận các sự kiện bảo mật (PII detected), quản trị (Incident state changed) và hệ thống (Prompt fallback).
2. **Cost Optimization Report**: Phân tích Before vs After tại [docs/cost-optimization.md](file:///c:/Users/Hi/Documents/GitHub/Day13-K3-Observability-DaiSuQuanHanViet/docs/cost-optimization.md) chứng minh mức giảm **87.6% chi phí USD** và **84.8% tổng token**.
3. **RAG Timeout & Circuit Breaker**: Triển khai cơ chế Timeout 1.0s và Circuit Breaker trong [app/mock_rag.py](file:///c:/Users/Hi/Documents/GitHub/Day13-K3-Observability-DaiSuQuanHanViet/app/mock_rag.py) đảm bảo P95 Latency ≤ 3000ms.
4. **CI/CD Automation**: Tự động hóa kiểm tra bằng GitHub Actions workflow [.github/workflows/ci.yml](file:///c:/Users/Hi/Documents/GitHub/Day13-K3-Observability-DaiSuQuanHanViet/.github/workflows/ci.yml).
5. **Script đánh giá SLO tự động (`scripts/evaluate_slo.py`)**: Đọc log thực tế và đối chiếu tự động với tiêu chuẩn trong `config/slo.yaml`.
