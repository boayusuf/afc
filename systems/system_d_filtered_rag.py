"""System D: GPT-4o + credibility-filtered Tavily RAG.

Replicates the dissertation's filtered-RAG configuration: 27 blocked domains
(known low-credibility / partisan), 46 boosted authoritative sources
(government, peer-reviewed, major outlets).
"""

import os
import time

from openai import OpenAI
from tavily import TavilyClient

from .base import Verdict, SYSTEM_REGISTRY
from .prompts import VERIFIER_RAG_SYSTEM_PROMPT, parse_verdict_json


# Subset matching the dissertation's filter approach. Tavily supports
# include_domains / exclude_domains parameters directly.
BLOCKED_DOMAINS = [
    "infowars.com", "naturalnews.com", "breitbart.com", "rt.com",
    "sputniknews.com", "zerohedge.com", "thegatewaypundit.com",
    "beforeitsnews.com", "globalresearch.ca", "wakingtimes.com",
    "newspunch.com", "yournewswire.com", "worldnewsdailyreport.com",
    "thedailysheeple.com", "dailystormer.in", "humansarefree.com",
    "veteranstoday.com", "endoftheamericandream.com",
    "americanthinker.com", "westernjournal.com", "thefederalist.com",
    "dailycaller.com", "lifesitenews.com", "freebeacon.com",
    "redstate.com", "townhall.com", "pjmedia.com",
]

BOOSTED_DOMAINS = [
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk",
    "nytimes.com", "washingtonpost.com", "wsj.com", "ft.com",
    "theguardian.com", "economist.com", "nature.com", "science.org",
    "thelancet.com", "nejm.org", "cdc.gov", "nih.gov", "who.int",
    "fda.gov", "ema.europa.eu", "europa.eu", "gov.uk",
    "noaa.gov", "nasa.gov", "esa.int", "un.org",
    "snopes.com", "politifact.com", "factcheck.org", "fullfact.org",
    "reuters.com/fact-check", "apnews.com/hub/ap-fact-check",
    "pewresearch.org", "ourworldindata.org", "statista.com",
    "harvard.edu", "mit.edu", "stanford.edu", "cam.ac.uk",
    "ox.ac.uk", "imperial.ac.uk", "ucl.ac.uk",
    "ons.gov.uk", "bls.gov", "imf.org", "worldbank.org",
    "iea.org", "ipcc.ch",
]


def _check_keys():
    openai_key = os.environ.get("OPENAI_API_KEY")
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not openai_key or openai_key.startswith("sk-proj-replace"):
        return "OPENAI_API_KEY not configured"
    if not tavily_key or tavily_key.startswith("tvly-replace"):
        return "TAVILY_API_KEY not configured"
    return None


def run(claim: str) -> Verdict:
    info = SYSTEM_REGISTRY["D"]
    err = _check_keys()
    if err:
        return Verdict(
            system_id="D",
            system_name=info["name"],
            paradigm=info["paradigm"],
            verdict="ERROR",
            reasoning=err,
            latency_ms=0,
            error="missing_api_key",
        )

    t0 = time.time()
    try:
        tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        # Tavily caps include_domains/exclude_domains lists. Use top items.
        search = tavily.search(
            query=claim,
            max_results=5,
            search_depth="basic",
            include_domains=BOOSTED_DOMAINS[:30],
            exclude_domains=BLOCKED_DOMAINS,
        )
        snippets = search.get("results", [])

        # Fallback: if filtering returned nothing, fall back to unfiltered to avoid empty evidence
        if not snippets:
            search = tavily.search(query=claim, max_results=5, search_depth="basic", exclude_domains=BLOCKED_DOMAINS)
            snippets = search.get("results", [])

        evidence_text = "\n\n".join(
            f"[{i+1}] {s.get('title', '')}\nSource: {s.get('url', '')}\n{s.get('content', '')}"
            for i, s in enumerate(snippets[:5])
        )
        sources = [s.get("url", "") for s in snippets[:5]]

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        resp = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            temperature=0,
            seed=42,
            messages=[
                {"role": "system", "content": VERIFIER_RAG_SYSTEM_PROMPT},
                {"role": "user", "content": f"Claim: {claim}\n\nRetrieved evidence (credibility-filtered):\n\n{evidence_text}"},
            ],
            timeout=30,
        )
        latency = int((time.time() - t0) * 1000)
        parsed = parse_verdict_json(resp.choices[0].message.content)
        return Verdict(
            system_id="D",
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
            system_id="D",
            system_name=info["name"],
            paradigm=info["paradigm"],
            verdict="ERROR",
            reasoning=f"API call failed: {type(e).__name__}: {str(e)[:200]}",
            latency_ms=int((time.time() - t0) * 1000),
            error=str(e)[:300],
        )
