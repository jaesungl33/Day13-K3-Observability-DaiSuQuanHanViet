from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Ensure root workspace directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
load_dotenv()

from app.incidents import disable, enable
from app.agent import LabAgent

EVIDENCE_DIR = Path("submission/evidence")


def run_batch_load_test(opt_enabled: bool) -> dict:
    os.environ["COST_OPTIMIZATION_ENABLED"] = "true" if opt_enabled else "false"
    agent = LabAgent()

    total_cost = 0.0
    total_tokens_in = 0
    total_tokens_out = 0
    latencies = []

    sample_messages = [
        "Explain tracing in microservices with example code and architecture overview.",
        "How do I setup Prometheus and Grafana for monitoring FastAPI applications?",
        "What is the policy for PII and credit card handling in logs?",
        "How to debug tail latency issues in distributed RAG architectures?",
        "Summary of observability best practices for production AI applications."
    ]

    for idx, msg in enumerate(sample_messages):
        t0 = time.perf_counter()
        res = agent.run(
            user_id=f"user-{idx}",
            feature="qa",
            session_id=f"sess-{idx}",
            message=msg,
            correlation_id=f"req-cost-{idx}",
        )
        dt = (time.perf_counter() - t0) * 1000
        latencies.append(dt)
        total_cost += res.cost_usd
        total_tokens_in += res.tokens_in
        total_tokens_out += res.tokens_out

    return {
        "requests": len(sample_messages),
        "total_cost_usd": round(total_cost, 6),
        "avg_cost_usd": round(total_cost / len(sample_messages), 6),
        "total_tokens_in": total_tokens_in,
        "total_tokens_out": total_tokens_out,
        "avg_tokens_out": round(total_tokens_out / len(sample_messages), 1),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 1),
    }


def main() -> int:
    print("=== Cost Optimization Experiment Runner ===")
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Enable cost_spike incident
    enable("cost_spike")
    print("[1] Incident 'cost_spike' enabled.")

    # 2. Measure BEFORE (Without Optimization)
    print("[2] Running load test BEFORE optimization...")
    before_metrics = run_batch_load_test(opt_enabled=False)
    print(f"    BEFORE Total Cost: ${before_metrics['total_cost_usd']:.6f} | Avg Tokens Out: {before_metrics['avg_tokens_out']}")

    # 3. Measure AFTER (With Optimization)
    print("[3] Running load test AFTER optimization (capped tokens & compressed prompt)...")
    after_metrics = run_batch_load_test(opt_enabled=True)
    print(f"    AFTER  Total Cost: ${after_metrics['total_cost_usd']:.6f} | Avg Tokens Out: {after_metrics['avg_tokens_out']}")

    # 4. Disable incident
    disable("cost_spike")
    os.environ["COST_OPTIMIZATION_ENABLED"] = "false"
    print("[4] Incident 'cost_spike' disabled.")

    cost_saved = before_metrics['total_cost_usd'] - after_metrics['total_cost_usd']
    pct_saved = (cost_saved / before_metrics['total_cost_usd']) * 100.0 if before_metrics['total_cost_usd'] > 0 else 0.0

    experiment_result = {
        "scenario": "cost_spike",
        "before_optimization": before_metrics,
        "after_optimization": after_metrics,
        "savings_summary": {
            "usd_saved_per_batch": round(cost_saved, 6),
            "percentage_cost_reduction": round(pct_saved, 2),
            "tokens_out_reduced_pct": round(((before_metrics['avg_tokens_out'] - after_metrics['avg_tokens_out']) / before_metrics['avg_tokens_out']) * 100.0, 2),
        }
    }

    # Write evidence files
    json_path = EVIDENCE_DIR / "cost_optimization_before_after.json"
    txt_path = EVIDENCE_DIR / "cost_optimization_before_after.txt"

    json_path.write_text(json.dumps(experiment_result, indent=2, ensure_ascii=False), encoding="utf-8")

    with txt_path.open("w", encoding="utf-8") as f:
        f.write("=== COST OPTIMIZATION BEFORE / AFTER EXPERIMENT ===\n\n")
        f.write(f"Scenario           : cost_spike\n")
        f.write(f"Batch Request Count: {before_metrics['requests']}\n\n")
        f.write(f"--- BEFORE OPTIMIZATION (Cost Spike Active) ---\n")
        f.write(f"Total USD Cost     : ${before_metrics['total_cost_usd']:.6f}\n")
        f.write(f"Avg Output Tokens  : {before_metrics['avg_tokens_out']} tokens\n")
        f.write(f"Avg Latency        : {before_metrics['avg_latency_ms']} ms\n\n")
        f.write(f"--- AFTER OPTIMIZATION (Capped Tokens & Caching) ---\n")
        f.write(f"Total USD Cost     : ${after_metrics['total_cost_usd']:.6f}\n")
        f.write(f"Avg Output Tokens  : {after_metrics['avg_tokens_out']} tokens\n")
        f.write(f"Avg Latency        : {after_metrics['avg_latency_ms']} ms\n\n")
        f.write(f"--- SAVINGS IMPACT ---\n")
        f.write(f"USD Saved per Batch: ${cost_saved:.6f}\n")
        f.write(f"Cost Reduction %   : {pct_saved:.2f}%\n")

    print(f"\n[SUCCESS] Cost Optimization Evidence saved to:\n - {json_path}\n - {txt_path}")
    print(f"Cost Reduction Achieved: {pct_saved:.2f}% (${cost_saved:.6f} saved per 5 requests)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
