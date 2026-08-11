from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

LOG_PATH = Path(os.getenv("LOG_PATH", "data/logs.jsonl"))
PII_PATTERNS = {
    "email": r"[\w\.-]+@[\w\.-]+\.\w+",
    "phone_vn": r"(?<!\d)(?:\+84|0)(?:[ .-]?\d){9}(?!\d)",
    "cccd": r"\b\d{12}\b",
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
}


def scan_for_unredacted_pii(text: str) -> list[str]:
    leaks = []
    for p_name, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, text)
        for match in matches:
            if not match.startswith("[REDACTED"):
                leaks.append(f"{p_name}:{match}")
    return leaks


def main() -> int:
    print("=== Custom Anomaly & Security Scanner ===")

    if not LOG_PATH.exists():
        print(f"Error: {LOG_PATH} does not exist.")
        return 1

    pii_anomalies = []
    slo_latency_anomalies = []
    error_anomalies = []
    cost_anomalies = []
    total_records = 0

    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line_idx, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            total_records += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            # 1. PII Leak Check
            raw_str = json.dumps(record, ensure_ascii=False)
            # Remove legitimate REDACTED tokens from text check
            cleaned_str = re.sub(r"\[REDACTED_[A-Z_]+\]", "", raw_str)
            leaks = scan_for_unredacted_pii(cleaned_str)
            if leaks:
                pii_anomalies.append({
                    "line": line_idx,
                    "event": record.get("event"),
                    "correlation_id": record.get("correlation_id"),
                    "leaks": leaks,
                })

            # 2. SLO Latency Anomaly Check (> 3000ms)
            latency = record.get("latency_ms")
            if isinstance(latency, (int, float)) and latency > 3000:
                slo_latency_anomalies.append({
                    "line": line_idx,
                    "correlation_id": record.get("correlation_id"),
                    "latency_ms": latency,
                    "feature": record.get("feature"),
                })

            # 3. Error Anomaly Check
            if record.get("event") == "request_failed" or record.get("level") == "error":
                error_anomalies.append({
                    "line": line_idx,
                    "correlation_id": record.get("correlation_id"),
                    "error_type": record.get("error_type") or record.get("payload", {}).get("detail"),
                })

            # 4. Cost Spike Anomaly Check (> $0.005)
            cost = record.get("cost_usd")
            if isinstance(cost, (int, float)) and cost > 0.005:
                cost_anomalies.append({
                    "line": line_idx,
                    "correlation_id": record.get("correlation_id"),
                    "cost_usd": cost,
                })

    report = {
        "total_log_records": total_records,
        "anomalies_summary": {
            "pii_leaks": len(pii_anomalies),
            "slo_latency_breaches": len(slo_latency_anomalies),
            "error_events": len(error_anomalies),
            "cost_spikes": len(cost_anomalies),
        },
        "pii_anomalies": pii_anomalies,
        "slo_latency_anomalies": slo_latency_anomalies,
        "error_anomalies": error_anomalies,
        "cost_anomalies": cost_anomalies,
    }

    print(f"Log Records Analyzed : {total_records}")
    print(f"PII Leaks Detected   : {len(pii_anomalies)}")
    print(f"SLO Latency Breaches : {len(slo_latency_anomalies)}")
    print(f"Error Events         : {len(error_anomalies)}")
    print(f"Cost Spikes (> $0.005): {len(cost_anomalies)}")

    out_json = Path("submission/evidence/anomaly_detection_report.json")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    out_txt = Path("submission/evidence/anomaly_detection_report.txt")
    with out_txt.open("w", encoding="utf-8") as f:
        f.write("=== AUTOMATED LOG ANOMALY SCAN REPORT ===\n")
        f.write(f"Total Log Records Scanned : {total_records}\n")
        f.write(f"Unredacted PII Leaks      : {len(pii_anomalies)}\n")
        f.write(f"SLO Latency Breaches (>3s): {len(slo_latency_anomalies)}\n")
        f.write(f"Error Events              : {len(error_anomalies)}\n")
        f.write(f"Cost Spike Anomalies      : {len(cost_anomalies)}\n\n")
        f.write("STATUS: " + ("CLEAN (No PII leaks or errors)" if len(pii_anomalies) == 0 else "WARNING (Anomalies detected)"))

    print(f"\nReport written to {out_json} & {out_txt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
