from __future__ import annotations

import json
import os
import sys
from pathlib import Path
import yaml

LOG_PATH = Path(os.getenv("LOG_PATH", "data/logs.jsonl"))
AUDIT_LOG_PATH = Path(os.getenv("AUDIT_LOG_PATH", "data/audit.jsonl"))
SLO_CONFIG_PATH = Path("config/slo.yaml")


def calculate_percentile(values: list[float | int], percentile: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * (percentile / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(sorted_vals):
        return float(sorted_vals[-1])
    weight = k - f
    return float(sorted_vals[f] * (1 - weight) + sorted_vals[c] * weight)


def main() -> int:
    print("--- Lab SLO Evaluation Scorecard ---")

    if not LOG_PATH.exists():
        print(f"Error: {LOG_PATH} not found. Run the app and load test first.")
        return 1

    if not SLO_CONFIG_PATH.exists():
        print(f"Error: {SLO_CONFIG_PATH} not found.")
        return 1

    with SLO_CONFIG_PATH.open("r", encoding="utf-8") as f:
        slo_config = yaml.safe_load(f)

    slis_config = slo_config.get("slis", {})

    latencies: list[int] = []
    costs: list[float] = []
    quality_scores: list[float] = []
    total_requests = 0
    error_requests = 0

    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            event = record.get("event")
            if event == "response_sent":
                total_requests += 1
                if "latency_ms" in record:
                    latencies.append(record["latency_ms"])
                if "cost_usd" in record:
                    costs.append(record["cost_usd"])
                if "quality_score" in record:
                    quality_scores.append(record["quality_score"])
            elif event == "request_failed":
                total_requests += 1
                error_requests += 1

    audit_events_count = 0
    if AUDIT_LOG_PATH.exists():
        with AUDIT_LOG_PATH.open("r", encoding="utf-8") as f:
            audit_events_count = sum(1 for line in f if line.strip())

    if total_requests == 0:
        print("Warning: No request events found in logs.")
        return 1

    p95_latency = calculate_percentile(latencies, 95)
    error_rate_pct = (error_requests / total_requests) * 100.0
    total_cost_usd = sum(costs)
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

    target_latency = slis_config.get("latency_p95_ms", {}).get("objective", 3000)
    target_error = slis_config.get("error_rate_pct", {}).get("objective", 2)
    target_cost = slis_config.get("daily_cost_usd", {}).get("objective", 2.5)
    target_quality = slis_config.get("quality_score_avg", {}).get("objective", 0.75)

    latency_pass = p95_latency <= target_latency
    error_pass = error_rate_pct <= target_error
    cost_pass = total_cost_usd <= target_cost
    quality_pass = avg_quality >= target_quality

    print(f"Total Requests Analyzed: {total_requests}")
    print(f"Total Audit Trail Events: {audit_events_count} (in {AUDIT_LOG_PATH})")
    print("\n--- SLO Performance Results ---")

    print(f"1. Latency P95: {p95_latency:.1f}ms / Objective <= {target_latency}ms -> [{'PASSED' if latency_pass else 'FAILED'}]")
    print(f"2. Error Rate:  {error_rate_pct:.2f}% / Objective <= {target_error}% -> [{'PASSED' if error_pass else 'FAILED'}]")
    print(f"3. Total Cost:  ${total_cost_usd:.6f} / Objective <= ${target_cost} -> [{'PASSED' if cost_pass else 'FAILED'}]")
    print(f"4. Quality Avg: {avg_quality:.2f} / Objective >= {target_quality} -> [{'PASSED' if quality_pass else 'FAILED'}]")

    all_passed = latency_pass and error_pass and cost_pass and quality_pass
    print(f"\nOverall SLO Status: {'ALL SLOs PASSED (100%)' if all_passed else 'SOME SLOs BREACHED'}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
