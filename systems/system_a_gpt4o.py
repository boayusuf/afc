"""System A: GPT-4o parametric LLM (closed-source, no retrieval)."""

import os
import time

from openai import OpenAI

from .base import Verdict, SYSTEM_REGISTRY
from .prompts import VERIFIER_SYSTEM_PROMPT, parse_verdict_json


def run(claim: str) -> Verdict:
    info = SYSTEM_REGISTRY["A"]
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-proj-replace"):
        return Verdict(
            system_id="A",
            system_name=info["name"],
            paradigm=info["paradigm"],
            verdict="ERROR",
            reasoning="OPENAI_API_KEY not configured in .env",
            latency_ms=0,
            error="missing_api_key",
        )

    client = OpenAI(api_key=api_key)
    t0 = time.time()
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            temperature=0,
            seed=42,
            messages=[
                {"role": "system", "content": VERIFIER_SYSTEM_PROMPT},
                {"role": "user", "content": f"Claim: {claim}"},
            ],
            timeout=30,
        )
        latency = int((time.time() - t0) * 1000)
        raw = resp.choices[0].message.content
        parsed = parse_verdict_json(raw)
        return Verdict(
            system_id="A",
            system_name=info["name"],
            paradigm=info["paradigm"],
            verdict=parsed["verdict"],
            reasoning=parsed["reasoning"],
            latency_ms=latency,
            error=None if parsed["verdict"] != "ERROR" else parsed["reasoning"],
        )
    except Exception as e:
        return Verdict(
            system_id="A",
            system_name=info["name"],
            paradigm=info["paradigm"],
            verdict="ERROR",
            reasoning=f"API call failed: {type(e).__name__}: {str(e)[:200]}",
            latency_ms=int((time.time() - t0) * 1000),
            error=str(e)[:300],
        )
