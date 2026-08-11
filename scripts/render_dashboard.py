#!/usr/bin/env python3
"""Render the Day 13 6-panel dashboard from data/logs.jsonl into an HTML evidence file."""

from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio

LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
OUT_PATH = REPO_ROOT / "submission" / "evidence" / "dashboard.html"
THRESHOLDS = {
    "latency_p95": 3000,
    "error_rate": 2.0,
    "cost_total": 2.5,
    "tokens_total": 50000,
    "quality_mean": 0.75,
}


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (pct / 100) * (len(ordered) - 1)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return ordered[low]
    weight = rank - low
    return ordered[low] * (1 - weight) + ordered[high] * weight


def load_records() -> list[dict]:
    if not LOG_PATH.exists():
        raise FileNotFoundError(f"Missing {LOG_PATH}. Run the API and load test first.")
    records: list[dict] = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def summarize(records: list[dict]) -> dict:
    responses = [r for r in records if r.get("event") == "response_sent"]
    received = [r for r in records if r.get("event") == "request_received"]
    failed = [r for r in records if r.get("event") == "request_failed"]
    latencies = [float(r["latency_ms"]) for r in responses if "latency_ms" in r]
    costs = [float(r.get("cost_usd") or 0) for r in responses]
    tokens_in = sum(int(r.get("tokens_in") or 0) for r in responses)
    tokens_out = sum(int(r.get("tokens_out") or 0) for r in responses)
    quality = [float(r["quality_score"]) for r in responses if "quality_score" in r]
    error_types = Counter(r.get("error_type") or "unknown" for r in failed)

    by_minute: dict[str, dict[str, float]] = defaultdict(lambda: {"req": 0, "cost": 0.0})
    for r in received:
        minute = str(r.get("ts", ""))[:16]
        by_minute[minute]["req"] += 1
    for r in responses:
        minute = str(r.get("ts", ""))[:16]
        by_minute[minute]["cost"] += float(r.get("cost_usd") or 0)

    minutes = max(len(by_minute), 1)
    error_rate = (len(failed) / len(received) * 100) if received else 0.0
    return {
        "p50": percentile(latencies, 50),
        "p95": percentile(latencies, 95),
        "p99": percentile(latencies, 99),
        "traffic_count": len(received),
        "rpm": len(received) / minutes,
        "error_rate": error_rate,
        "error_types": dict(error_types),
        "cost_total": sum(costs),
        "cost_by_minute": {k: v["cost"] for k, v in sorted(by_minute.items())},
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "quality_mean": (sum(quality) / len(quality)) if quality else 0.0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def badge(ok: bool) -> str:
    return "OK" if ok else "BREACH"


def render_html(stats: dict) -> str:
    error_rows = "".join(
        f"<tr><td>{name}</td><td>{count}</td></tr>"
        for name, count in sorted(stats["error_types"].items())
    ) or "<tr><td colspan='2'>No errors</td></tr>"
    cost_rows = "".join(
        f"<tr><td>{minute}</td><td>{cost:.6f}</td></tr>"
        for minute, cost in list(stats["cost_by_minute"].items())[-12:]
    ) or "<tr><td colspan='2'>No cost data</td></tr>"

    checks = {
        "Latency P95 ≤ 3000 ms": stats["p95"] <= THRESHOLDS["latency_p95"],
        "Error rate ≤ 2%": stats["error_rate"] <= THRESHOLDS["error_rate"],
        "Cost total ≤ 2.5 USD": stats["cost_total"] <= THRESHOLDS["cost_total"],
        "Tokens ≤ 50000": (stats["tokens_in"] + stats["tokens_out"]) <= THRESHOLDS["tokens_total"],
        "Quality mean ≥ 0.75": stats["quality_mean"] >= THRESHOLDS["quality_mean"],
    }
    check_rows = "".join(
        f"<tr><td>{name}</td><td class='{'ok' if ok else 'bad'}'>{badge(ok)}</td></tr>"
        for name, ok in checks.items()
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Day 13 AI Observability Dashboard</title>
  <style>
    :root {{
      --bg: #0f172a;
      --panel: #1e293b;
      --text: #e2e8f0;
      --muted: #94a3b8;
      --accent: #38bdf8;
      --ok: #4ade80;
      --bad: #f87171;
      --line: #334155;
    }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      background:
        radial-gradient(1200px 600px at 10% -10%, #1d4ed833, transparent),
        radial-gradient(900px 500px at 90% 0%, #0ea5e933, transparent),
        var(--bg);
      color: var(--text);
    }}
    header {{
      padding: 24px 32px 8px;
    }}
    h1 {{ margin: 0 0 6px; font-size: 28px; }}
    .meta {{ color: var(--muted); font-size: 14px; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
      padding: 16px 32px 32px;
    }}
    .panel {{
      background: color-mix(in srgb, var(--panel) 92%, black);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      min-height: 220px;
    }}
    .panel h2 {{
      margin: 0 0 4px;
      font-size: 16px;
      letter-spacing: 0.02em;
    }}
    .unit {{ color: var(--muted); font-size: 12px; margin-bottom: 12px; }}
    .metric {{
      font-size: 28px;
      font-weight: 700;
      color: var(--accent);
      margin: 4px 0;
    }}
    .sub {{ color: var(--muted); font-size: 13px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    td, th {{ border-bottom: 1px solid var(--line); padding: 6px 0; text-align: left; }}
    .ok {{ color: var(--ok); font-weight: 700; }}
    .bad {{ color: var(--bad); font-weight: 700; }}
    .threshold {{
      margin-top: 12px;
      padding-top: 10px;
      border-top: 1px dashed var(--line);
      font-size: 12px;
      color: var(--muted);
    }}
    @media (max-width: 1100px) {{
      .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Day 13 AI Observability</h1>
    <div class="meta">
      Source: <code>data/logs.jsonl</code> · Time range: last 60 minutes · Refresh: 30s ·
      Generated (UTC): {stats["generated_at"]}
    </div>
  </header>
  <main class="grid">
    <section class="panel" id="latency">
      <h2>1. Latency percentiles</h2>
      <div class="unit">Unit: ms · Threshold: P95 ≤ 3000</div>
      <div class="metric">P95 {stats["p95"]:.0f}</div>
      <div class="sub">P50 {stats["p50"]:.0f} · P99 {stats["p99"]:.0f}</div>
      <div class="threshold">SLO line: 3000 ms</div>
    </section>
    <section class="panel" id="traffic">
      <h2>2. Request traffic</h2>
      <div class="unit">Unit: requests_per_minute · Threshold: ≥ 1</div>
      <div class="metric">{stats["rpm"]:.2f} rpm</div>
      <div class="sub">Total requests: {stats["traffic_count"]}</div>
      <div class="threshold">Traffic must stay above 1 rpm in active windows</div>
    </section>
    <section class="panel" id="errors">
      <h2>3. Error rate and breakdown</h2>
      <div class="unit">Unit: percent · Threshold: ≤ 2%</div>
      <div class="metric">{stats["error_rate"]:.2f}%</div>
      <table><thead><tr><th>error_type</th><th>count</th></tr></thead><tbody>{error_rows}</tbody></table>
      <div class="threshold">SLO line: 2%</div>
    </section>
    <section class="panel" id="cost">
      <h2>4. Cost over time</h2>
      <div class="unit">Unit: usd · Threshold: total ≤ 2.5</div>
      <div class="metric">${stats["cost_total"]:.6f}</div>
      <table><thead><tr><th>minute (UTC)</th><th>cost</th></tr></thead><tbody>{cost_rows}</tbody></table>
      <div class="threshold">Budget line: $2.50</div>
    </section>
    <section class="panel" id="tokens">
      <h2>5. Input and output tokens</h2>
      <div class="unit">Unit: tokens · Threshold: ≤ 50000</div>
      <div class="metric">{stats["tokens_in"] + stats["tokens_out"]}</div>
      <div class="sub">tokens_in={stats["tokens_in"]} · tokens_out={stats["tokens_out"]}</div>
      <div class="threshold">Token budget line: 50000</div>
    </section>
    <section class="panel" id="quality">
      <h2>6. Quality proxy</h2>
      <div class="unit">Unit: score_0_to_1 · Threshold: mean ≥ 0.75</div>
      <div class="metric">{stats["quality_mean"]:.2f}</div>
      <div class="sub">Mean quality_score from response_sent</div>
      <div class="threshold">Quality floor: 0.75</div>
    </section>
  </main>
  <section class="panel" style="margin: 0 32px 32px;">
    <h2>SLO / threshold status</h2>
    <table><thead><tr><th>check</th><th>status</th></tr></thead><tbody>{check_rows}</tbody></table>
  </section>
</body>
</html>
"""


def main() -> int:
    configure_utf8_stdio()
    stats = summarize(load_records())
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(render_html(stats), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    print(
        "summary:",
        json.dumps(
            {
                "p50": round(stats["p50"], 1),
                "p95": round(stats["p95"], 1),
                "p99": round(stats["p99"], 1),
                "error_rate_pct": round(stats["error_rate"], 2),
                "cost_total": round(stats["cost_total"], 6),
                "quality_mean": round(stats["quality_mean"], 2),
            },
            ensure_ascii=False,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
