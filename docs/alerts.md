# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: high_latency_p95
- Severity: warning
- SLI/SLO liên quan: latency_p95_ms ≤ 3000ms (target 99.5%)
- Điều kiện và thời gian duy trì: P95 latency > 3000ms trong 5 phút liên tiếp
- Ảnh hưởng tới người dùng: Chat trả lời chậm; trải nghiệm refund/QA bị treo
- Ba bước kiểm tra đầu tiên:
  1. Mở panel Latency và xác nhận P95/P99 trong cửa sổ 60 phút.
  2. Lọc traces có latency bất thường theo feature bị ảnh hưởng.
  3. So sánh span retrieval vs LLM; tìm log cùng correlation ID.
- Mitigation tạm thời: giảm concurrency, tắt feature nặng, rollback prompt `production` nếu vừa đổi label.
- Owner: oncall-platform

## Alert 2

- Tên: elevated_error_rate
- Severity: critical
- SLI/SLO liên quan: error_rate_pct ≤ 2% (target 99.0%)
- Điều kiện và thời gian duy trì: error rate > 2% trong 5 phút liên tiếp
- Ảnh hưởng tới người dùng: request thất bại, agent không trả lời được
- Ba bước kiểm tra đầu tiên:
  1. Xem panel Errors và breakdown theo `error_type`.
  2. Mở một `request_failed` log gần nhất kèm correlation ID.
  3. Kiểm tra incident flags (`tool_fail`) và dependency RAG/LLM.
- Mitigation tạm thời: disable incident/tool lỗi, trả fallback message, scale lại dependency.
- Owner: oncall-platform

## Alert 3

- Tên: daily_cost_budget_breach
- Severity: warning
- SLI/SLO liên quan: daily_cost_usd ≤ 2.5
- Điều kiện và thời gian duy trì: tổng cost cửa sổ hiện tại > 2.5 USD duy trì 15 phút
- Ảnh hưởng tới người dùng: không trực tiếp; rủi ro vượt ngân sách và phải cắt traffic
- Ba bước kiểm tra đầu tiên:
  1. So sánh Cost panel với Traffic panel — cost tăng mà traffic không tăng là bất thường.
  2. Kiểm tra `tokens_out`/`tokens_in` trên traces gần đây.
  3. Xác nhận có `cost_spike` hoặc prompt dài bất thường.
- Mitigation tạm thời: giới hạn max tokens, chuyển về prompt baseline ngắn hơn, rate-limit feature tốn kém.
- Owner: oncall-ai
