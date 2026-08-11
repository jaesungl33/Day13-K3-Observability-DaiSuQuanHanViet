from __future__ import annotations

import json
from pathlib import Path

def export_audit_sample():
    audit_file = Path("data/audit.jsonl")
    sample_file = Path("submission/evidence/audit_log_sample.json")

    if not audit_file.exists():
        print("data/audit.jsonl not found.")
        return

    records = []
    with audit_file.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    pass

    sample_records = records[-10:] if len(records) >= 10 else records
    sample_file.parent.mkdir(parents=True, exist_ok=True)
    sample_file.write_text(json.dumps(sample_records, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Exported {len(sample_records)} audit records to {sample_file}")

if __name__ == "__main__":
    export_audit_sample()
