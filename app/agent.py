from __future__ import annotations

import os
import time
from dataclasses import dataclass

from . import metrics
from .logging_config import get_logger
from .mock_llm import FakeLLM
from .mock_rag import retrieve
from .pii import hash_user_id, summarize_text
from .prompt_management import resolve_prompt
from .tracing import get_langfuse_client, observe, tracing_enabled

log = get_logger()


@dataclass
class AgentResult:
    answer: str
    latency_ms: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    quality_score: float


class LabAgent:
    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.model = model
        self.llm = FakeLLM(model=model)

    @observe(name="chat-turn", as_type="agent", capture_input=False, capture_output=False)
    def run(
        self,
        user_id: str,
        feature: str,
        session_id: str,
        message: str,
        *,
        correlation_id: str | None = None,
    ) -> AgentResult:
        started = time.perf_counter()
        langfuse_client = get_langfuse_client()
        safe_message = summarize_text(message)

        langfuse_client.update_current_trace(
            name="chat-turn",
            user_id=hash_user_id(user_id),
            session_id=session_id,
            tags=["lab", feature, self.model, os.getenv("APP_ENV", "dev")],
            input={"message": safe_message, "feature": feature},
            metadata={
                "feature": feature,
                "correlation_id": correlation_id,
                "env": os.getenv("APP_ENV", "dev"),
            },
        )
        langfuse_client.update_current_span(
            input={"message": safe_message, "feature": feature},
            metadata={"correlation_id": correlation_id, "model": self.model},
        )

        docs = retrieve(message)
        prompt = resolve_prompt(
            langfuse_client,
            feature=feature,
            docs=docs,
            message=message,
            enabled=tracing_enabled(),
        )
        response = self.llm.generate(
            prompt.text,
            managed_prompt=prompt.managed_prompt,
            prompt_metadata={
                "doc_count": len(docs),
                "query_preview": safe_message,
                "prompt_name": prompt.name,
                "prompt_label": prompt.label,
                "prompt_version": prompt.version,
                "prompt_source": prompt.source,
                "prompt_fetch_error": prompt.fetch_error,
            },
        )
        quality_score = self._heuristic_quality(message, response.text, docs)
        latency_ms = int((time.perf_counter() - started) * 1000)
        cost_usd = self._estimate_cost(response.usage.input_tokens, response.usage.output_tokens)

        log.info(
            "prompt_resolved",
            service="agent",
            payload={
                "prompt_name": prompt.name,
                "prompt_label": prompt.label,
                "prompt_version": prompt.version,
                "prompt_source": prompt.source,
                "prompt_fetch_error": prompt.fetch_error,
                "query_preview": safe_message,
            },
        )

        langfuse_client.update_current_trace(
            output={"answer": summarize_text(response.text), "quality_score": quality_score},
            metadata={
                "feature": feature,
                "correlation_id": correlation_id,
                "env": os.getenv("APP_ENV", "dev"),
                "prompt_name": prompt.name,
                "prompt_label": prompt.label,
                "prompt_version": prompt.version,
                "prompt_source": prompt.source,
                "latency_ms": latency_ms,
                "quality_score": quality_score,
            },
        )
        langfuse_client.update_current_span(
            output={
                "answer": summarize_text(response.text),
                "latency_ms": latency_ms,
                "quality_score": quality_score,
            },
        )

        metrics.record_request(
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            quality_score=quality_score,
        )

        return AgentResult(
            answer=response.text,
            latency_ms=latency_ms,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            cost_usd=cost_usd,
            quality_score=quality_score,
        )

    def _estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        input_cost = (tokens_in / 1_000_000) * 3
        output_cost = (tokens_out / 1_000_000) * 15
        return round(input_cost + output_cost, 6)

    def _heuristic_quality(self, question: str, answer: str, docs: list[str]) -> float:
        score = 0.5
        if docs:
            score += 0.2
        if len(answer) > 40:
            score += 0.1
        if question.lower().split()[0:1] and any(
            token in answer.lower() for token in question.lower().split()[:3]
        ):
            score += 0.1
        if "[REDACTED" in answer:
            score -= 0.2
        return round(max(0.0, min(1.0, score)), 2)
