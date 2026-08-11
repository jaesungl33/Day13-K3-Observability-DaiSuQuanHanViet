#!/usr/bin/env python3
"""Create day13-chat prompt versions/labels used by the lab."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio

PROMPT_NAME = os.getenv("LANGFUSE_PROMPT_NAME", "day13-chat")
PROMPT_V1 = (
    "You are a concise support assistant.\n"
    "Feature={{feature}}\n"
    "Docs={{docs}}\n"
    "Question={{message}}\n"
    "Answer in 2-3 short sentences."
)
PROMPT_V2 = (
    "You are a concise support assistant.\n"
    "Feature={{feature}}\n"
    "Docs={{docs}}\n"
    "Question={{message}}\n"
    "Answer in one short paragraph with a clear next action."
)


def main() -> int:
    configure_utf8_stdio()
    load_dotenv(REPO_ROOT / ".env")
    if os.getenv("LANGFUSE_BASE_URL") and not os.getenv("LANGFUSE_HOST"):
        os.environ["LANGFUSE_HOST"] = os.environ["LANGFUSE_BASE_URL"]
    if os.getenv("LANGFUSE_HOST") and not os.getenv("LANGFUSE_BASE_URL"):
        os.environ["LANGFUSE_BASE_URL"] = os.environ["LANGFUSE_HOST"]

    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        print("Missing LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY")
        return 1

    from langfuse import get_client

    client = get_client()
    v1 = client.create_prompt(
        name=PROMPT_NAME,
        type="text",
        prompt=PROMPT_V1,
        labels=["baseline", "production"],
    )
    v2 = client.create_prompt(
        name=PROMPT_NAME,
        type="text",
        prompt=PROMPT_V2,
        labels=["candidate"],
    )
    client.flush()
    print(f"Created {PROMPT_NAME} v{v1.version} labels={getattr(v1, 'labels', [])}")
    print(f"Created {PROMPT_NAME} v{v2.version} labels={getattr(v2, 'labels', [])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
