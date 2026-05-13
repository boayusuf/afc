"""System E: Llama 3.3 70B via Groq (open-source parametric LLM)."""

import os
import time

from groq import Groq

from .base import Verdict, SYSTEM_REGISTRY
from .prompts import VERIFIER_SYSTEM_PROMPT, parse_verdict_json


def run(claim: str) -> Verdict:
    info = SYSTEM_REGISTRY["E"]
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or api_key.startswith("gsk_replace"):
        return Verdict(
            system_id="E",
            system_name=info["name"],
            paradigm=info["paradigm"],
            verdict="ERROR",
            reasoning="GROQ_API_KEY not configured in .env",
            latency_ms=0,
            error="missing_api_key",
        )

    client = Groq(api_key=api_key)
    t0 = time.time()
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0,
            seed=42,
            messages=[
                {"role": "system", "content": VERIFIER_SYSTEM_PROMPT},
                {"role": "user", "content": f"Claim: {claim}"},
            ],
            timeout=30,
        )
        latency = int((time.time() - t0) * 1000)
        parsed = parse_verdict_json(resp.choices[0].message.content)
        return Verdict(
            system_id="E",
            system_name=info["name"],
            paradigm=info["paradigm"],
            verdict=parsed["verdict"],
            reasoning=parsed["reasoning"],
            latency_ms=latency,
            error=None if parsed["verdict"] != "ERROR" else parsed["reasoning"],
        )
    except Exception as e:
        return Verdict(
            system_id="E",
            system_name=info["name"],
            paradigm=info["paradigm"],
            verdict="ERROR",
            reasoning=f"API call failed: {type(e).__name__}: {str(e)[:200]}",
            latency_ms=int((time.time() - t0) * 1000),
            error=str(e)[:300],
        )
