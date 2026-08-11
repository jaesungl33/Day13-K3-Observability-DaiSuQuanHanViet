from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass
from typing import Any

from .incidents import STATE
from .pii import summarize_text
from .tracing import get_langfuse_client, observe


@dataclass
class FakeUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class FakeResponse:
    text: str
    usage: FakeUsage
    model: str


class FakeLLM:
    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.model = model

    @observe(name="generate-response", as_type="generation", capture_input=False, capture_output=False)
    def generate(
        self,
        prompt: str,
        *,
        managed_prompt: Any | None = None,
        prompt_metadata: dict[str, Any] | None = None,
        cost_usd: float | None = None,
    ) -> FakeResponse:
        client = get_langfuse_client()
        time.sleep(0.15)
        input_tokens = max(20, len(prompt) // 4)
        output_tokens = random.randint(80, 180)
        cost_optimization_active = os.getenv("COST_OPTIMIZATION_ENABLED", "false").lower() == "true"
        if STATE["cost_spike"]:
            output_tokens *= 4
            if cost_optimization_active:
                output_tokens = min(output_tokens, 120)
        elif cost_optimization_active:
            output_tokens = min(output_tokens, 100)
        answer = (
            "Starter answer. Teams should improve this output logic and add better quality checks. "
            "Use retrieved context and keep responses concise."
        )
        response = FakeResponse(
            text=answer,
            usage=FakeUsage(input_tokens, output_tokens),
            model=self.model,
        )
        if cost_usd is None:
            cost_usd = round((input_tokens / 1_000_000) * 3 + (output_tokens / 1_000_000) * 15, 6)
        client.update_current_generation(
            model=self.model,
            input=[{"role": "user", "content": summarize_text(prompt, max_len=240)}],
            output=answer,
            usage_details={
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens,
            },
            cost_details={"total": cost_usd},
            prompt=managed_prompt,
            metadata={
                "cost_spike": STATE["cost_spike"],
                **(prompt_metadata or {}),
            },
        )
        return response
