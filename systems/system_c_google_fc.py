"""System C: Google Fact Check Tools API (professional FC database)."""

import os
import time

import requests

from .base import Verdict, SYSTEM_REGISTRY


# Map common Google FC textual ratings to our 4-way schema
_RATING_MAP = {
    "true": "TRUE",
    "mostly true": "TRUE",
    "correct": "TRUE",
    "accurate": "TRUE",
    "false": "MISLEADING",
    "mostly false": "MISLEADING",
    "pants on fire": "MISLEADING",
    "misleading": "MISLEADING",
    "incorrect": "MISLEADING",
    "inaccurate": "MISLEADING",
    "fake": "MISLEADING",
    "no evidence": "MISLEADING",
    "partly true": "MIXED",
    "partly false": "MIXED",
    "half true": "MIXED",
    "mixture": "MIXED",
    "mixed": "MIXED",
    "needs context": "MIXED",
}


def _normalise(rating: str) -> str:
    if not rating:
        return "NO_RESULT"
    lower = rating.lower().strip()
    for key, value in _RATING_MAP.items():
        if key in lower:
            return value
    return "NO_RESULT"


def run(claim: str) -> Verdict:
    info = SYSTEM_REGISTRY["C"]
    api_key = os.environ.get("GOOGLE_FACT_CHECK_API_KEY")
    if not api_key or api_key.startswith("replace"):
        return Verdict(
            system_id="C",
            system_name=info["name"],
            paradigm=info["paradigm"],
            verdict="ERROR",
            reasoning="GOOGLE_FACT_CHECK_API_KEY not configured",
            latency_ms=0,
            error="missing_api_key",
        )

    t0 = time.time()
    try:
        url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        params = {"query": claim, "key": api_key, "languageCode": "en", "pageSize": 5}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        latency = int((time.time() - t0) * 1000)
        claims_found = data.get("claims", [])

        if not claims_found:
            return Verdict(
                system_id="C",
                system_name=info["name"],
                paradigm=info["paradigm"],
                verdict="NO_RESULT",
                reasoning="No matching fact-check found in the Google ClaimReview database.",
                latency_ms=latency,
            )

        # Use first match's first review
        first = claims_found[0]
        reviews = first.get("claimReview", [])
        if not reviews:
            return Verdict(
                system_id="C",
                system_name=info["name"],
                paradigm=info["paradigm"],
                verdict="NO_RESULT",
                reasoning="Match found but no review attached.",
                latency_ms=latency,
            )
        rev = reviews[0]
        rating = rev.get("textualRating", "")
        publisher = rev.get("publisher", {}).get("name", "unknown source")
        title = rev.get("title", first.get("text", ""))[:200]
        review_url = rev.get("url", "")
        verdict = _normalise(rating)
        reasoning = f'{publisher} rated this "{rating}". {title}'
        return Verdict(
            system_id="C",
            system_name=info["name"],
            paradigm=info["paradigm"],
            verdict=verdict,
            reasoning=reasoning[:400],
            latency_ms=latency,
            sources=[review_url] if review_url else [],
        )
    except Exception as e:
        return Verdict(
            system_id="C",
            system_name=info["name"],
            paradigm=info["paradigm"],
            verdict="ERROR",
            reasoning=f"API call failed: {type(e).__name__}: {str(e)[:200]}",
            latency_ms=int((time.time() - t0) * 1000),
            error=str(e)[:300],
        )
