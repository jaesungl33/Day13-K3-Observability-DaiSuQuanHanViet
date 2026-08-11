from __future__ import annotations

import time

from .incidents import STATE
from .pii import summarize_text
from .tracing import get_langfuse_client, observe

CORPUS = {
    "refund": ["Refunds are available within 7 days with proof of purchase."],
    "monitoring": ["Metrics detect incidents, traces localize them, logs explain root cause."],
    "policy": ["Do not expose PII in logs. Use sanitized summaries only."],
}


@observe(name="retrieve-context", as_type="retriever", capture_input=False, capture_output=False)
def retrieve(message: str) -> list[str]:
    client = get_langfuse_client()
    client.update_current_span(
        input={"query_preview": summarize_text(message)},
        metadata={"corpus_keys": sorted(CORPUS.keys()), "incident_rag_slow": STATE["rag_slow"]},
    )
    if STATE["tool_fail"]:
        raise RuntimeError("Vector store timeout")
    if STATE["rag_slow"]:
        time.sleep(2.5)
    lowered = message.lower()
    for key, docs in CORPUS.items():
        if key in lowered:
            client.update_current_span(
                output={"doc_count": len(docs), "matched_key": key, "docs": docs},
            )
            return docs
    fallback = ["No domain document matched. Use general fallback answer."]
    client.update_current_span(
        output={"doc_count": len(fallback), "matched_key": None, "docs": fallback},
    )
    return fallback
