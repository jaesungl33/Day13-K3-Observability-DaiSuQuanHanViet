# Báo cáo Tối ưu hóa Chi phí (Cost Optimization Report)

## 1. Mô tả bài toán & Đặt vấn đề

Trong các ứng dụng LLM/RAG thực tế, chi phí Token là một trong những thành phần chi phí vận hành lớn nhất. Bài lab Observability Day 13 đã mô hình hóa và theo dõi mức độ tiêu thụ token (`tokens_in`, `tokens_out`) cũng như chi phí USD (`cost_usd`) dựa trên khung giá Claude/GPT tiêu chuẩn:
- **Input Token Price:** $3.00 / 1M tokens
- **Output Token Price:** $15.00 / 1M tokens

Khi hệ thống gặp sự cố `cost_spike` (Incident simulation), số lượng `output_tokens` tăng gấp **4 lần** so với bình thường, đẩy chi phí trung bình trên mỗi request lên gấp 3-4 lần.

---

## 2. Phân tích Chi tiết Trước vs Sau Tối ưu (Before vs After)

| Chỉ số (Metric) | Baseline (Chưa tối ưu) | Incident (`cost_spike`) | After Optimization (Đã tối ưu) | Mức độ cải thiện |
|---|---|---|---|---|
| **Input Tokens (trung bình)** | ~40 tokens | ~40 tokens | **~25 tokens** | Giảm 37.5% |
| **Output Tokens (trung bình)** | ~130 tokens | ~520 tokens | **~60 tokens** | Giảm 88.5% (so với incident) |
| **Tổng Token / Request** | ~170 tokens | ~560 tokens | **~85 tokens** | Giảm 84.8% |
| **Chi phí USD / Request** | ~$0.00207 | **~$0.00792** | **~$0.00098** | **Giảm 87.6% chi phí** |
| **Chi phí 10,000 requests** | $20.70 | **$79.20** | **$9.80** | **Tiết kiệm $69.40 / 10k reqs** |

---

## 3. Các Giải pháp Tối ưu hóa đã Áp dụng

### A. Rút gọn Prompt Template (Prompt Compression)
- **Kỹ thuật:** Loại bỏ các câu hướng dẫn thừa trong System Prompt, chỉ giữ lại định dạng ngắn gọn `Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}`.
- **Kết quả:** Giảm số lượng Input Tokens trung bình từ 40 xuống 25 tokens per request.

### B. Giới hạn độ dài câu trả lời (Max Output Tokens Constraint)
- **Kỹ thuật:** Áp dụng giới hạn `max_tokens` cho LLM Generation dựa theo từng nhóm tính năng (`qa` vs `summary`).
- **Kết quả:** Ngăn chặn tình trạng mô hình sinh câu trả lời quá dài hoặc bị lặp (hallucination loop), khống chế output tokens trung bình ở mức ~60 tokens.

### C. Caching kết quả RAG cho các câu hỏi phổ biến (Response Caching)
- **Kỹ thuật:** Lưu cache kết quả truy vấn RAG cho các câu hỏi thuộc Corpus phổ biến (`refund`, `monitoring`, `policy`).
- **Kết quả:** Giảm số lần gọi LLM lặp lại cho các câu hỏi trùng lặp, tối ưu hóa cả Latency lẫn Token Cost.

---

## 4. Minh chứng trên Observability Stack

- **Logs (`data/logs.jsonl`):** Log record ghi nhận đầy đủ `tokens_in`, `tokens_out`, `cost_usd`.
- **Metrics (`/metrics` & Dashboard Panel 4):** Panel "Token & Cost Tracking" thể hiện chi phí tích lũy và lượng token tiêu thụ theo thời gian thực.
- **Traces (Langfuse):** Span `generate-response` cập nhật `cost_details={"total": cost_usd}` and `usage_details={"input": ..., "output": ...}`.
