import os
import time

from .incidents import STATE
from .pii import summarize_text
from .tracing import get_langfuse_client, observe

CORPUS = {
    "refund": ["Refunds are available within 7 days with proof of purchase."],
    "monitoring": ["Metrics detect incidents, traces localize them, logs explain root cause."],
    "policy": ["Do not expose PII in logs. Use sanitized summaries only."],
}

RAG_TIMEOUT_SECONDS: float = float(os.getenv("RAG_TIMEOUT_SECONDS", "1.0"))


@observe(name="retrieve-context", as_type="retriever", capture_input=False, capture_output=False)
def retrieve(message: str) -> list[str]:
    client = get_langfuse_client()
    circuit_breaker_enabled = os.getenv("RAG_CIRCUIT_BREAKER_ENABLED", "true").lower() == "true"
    client.update_current_span(
        input={"query_preview": summarize_text(message)},
        metadata={
            "corpus_keys": sorted(CORPUS.keys()),
            "incident_rag_slow": STATE["rag_slow"],
            "circuit_breaker_enabled": circuit_breaker_enabled,
        },
    )
    if STATE["tool_fail"]:
        raise RuntimeError("Vector store timeout")
    if STATE["rag_slow"]:
        if circuit_breaker_enabled and RAG_TIMEOUT_SECONDS < 2.5:
            time.sleep(RAG_TIMEOUT_SECONDS)
            fallback = ["Retrieval timeout reached. Circuit breaker engaged with fallback context."]
            client.update_current_span(
                output={"doc_count": len(fallback), "matched_key": None, "docs": fallback},
                metadata={"circuit_breaker_tripped": True, "timeout_seconds": RAG_TIMEOUT_SECONDS},
            )
            return fallback
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
