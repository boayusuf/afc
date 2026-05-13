"""System B: GPT-4o + naive Tavily RAG (no source filtering)."""

import os
import time

from openai import OpenAI
from tavily import TavilyClient

from .base import Verdict, SYSTEM_REGISTRY
from .prompts import VERIFIER_RAG_SYSTEM_PROMPT, parse_verdict_json


def _check_keys():
    openai_key = os.environ.get("OPENAI_API_KEY")
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not openai_key or openai_key.startswith("sk-proj-replace"):
        return "OPENAI_API_KEY not configured"
    if not tavily_key or tavily_key.startswith("tvly-replace"):
        return "TAVILY_API_KEY not configured"
    return None


def run(claim: str) -> Verdict:
    info = SYSTEM_REGISTRY["B"]
    err = _check_keys()
    if err:
        return Verdict(
            system_id="B",
            system_name=info["name"],
            paradigm=info["paradigm"],
            verdict="ERROR",
            reasoning=err,
            latency_ms=0,
            error="missing_api_key",
        )

    t0 = time.time()
    try:
        # Retrieve via Tavily — top 5 snippets, no domain filter
        tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        search = tavily.search(query=claim, max_results=5, search_depth="basic")
        snippets = search.get("results", [])
        evidence_text = "\n\n".join(
            f"[{i+1}] {s.get('title', '')}\nSource: {s.get('url', '')}\n{s.get('content', '')}"
            for i, s in enumerate(snippets[:5])
        )
        sources = [s.get("url", "") for s in snippets[:5]]

        # Verify with GPT-4o given evidence
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        resp = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            temperature=0,
            seed=42,
            messages=[
                {"role": "system", "content": VERIFIER_RAG_SYSTEM_PROMPT},
                {"role": "user", "content": f"Claim: {claim}\n\nRetrieved evidence:\n\n{evidence_text}"},
            ],
            timeout=30,
        )
        latency = int((time.time() - t0) * 1000)
        parsed = parse_verdict_json(resp.choices[0].message.content)
        return Verdict(
            system_id="B",
            system_name=info["name"],
            paradigm=info["paradigm"],
            verdict=parsed["verdict"],
            reasoning=parsed["reasoning"],
            latency_ms=latency,
            sources=sources,
            error=None if parsed["verdict"] != "ERROR" else parsed["reasoning"],
        )
    except Exception as e:
        return Verdict(
            system_id="B",
            system_name=info["name"],
            paradigm=info["paradigm"],
            verdict="ERROR",
            reasoning=f"API call failed: {type(e).__name__}: {str(e)[:200]}",
            latency_ms=int((time.time() - t0) * 1000),
            error=str(e)[:300],
        )
