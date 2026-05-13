"""Shared prompts and JSON parsing for LLM-based systems (A, B, D, E)."""

import json
import re


VERIFIER_SYSTEM_PROMPT = """You are an automated fact-checker. You are given a single factual claim and asked to assess its veracity.

You MUST respond with ONLY a JSON object in this exact format, nothing else:

{
  "verdict": "TRUE" | "MISLEADING" | "MIXED" | "NO_RESULT",
  "reasoning": "<one to three sentences>"
}

Verdict definitions:
- TRUE: the claim is substantively accurate as stated
- MISLEADING: the claim is false, deceptive, or strongly misleads its reader
- MIXED: the claim contains both true and misleading elements, or critical context is missing
- NO_RESULT: you have insufficient information to assess; do not guess

Keep reasoning concise. Do not include markdown, do not include backticks, do not include any text outside the JSON object."""


VERIFIER_RAG_SYSTEM_PROMPT = """You are an automated fact-checker with access to web search results. You are given a claim and retrieved evidence snippets. Assess the claim against the evidence.

You MUST respond with ONLY a JSON object in this exact format, nothing else:

{
  "verdict": "TRUE" | "MISLEADING" | "MIXED" | "NO_RESULT",
  "reasoning": "<one to three sentences citing the evidence>"
}

Verdict definitions:
- TRUE: the evidence supports the claim
- MISLEADING: the evidence contradicts the claim
- MIXED: evidence partially supports and partially contradicts
- NO_RESULT: evidence is insufficient or off-topic

Do not include markdown, backticks, or text outside the JSON object."""


def parse_verdict_json(text: str) -> dict:
    """Extract verdict JSON from an LLM response, tolerating fences and noise."""
    # Strip markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)

    # Find the first {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {"verdict": "ERROR", "reasoning": f"No JSON object in response: {text[:200]}"}

    try:
        obj = json.loads(match.group())
    except json.JSONDecodeError as e:
        return {"verdict": "ERROR", "reasoning": f"JSON parse failed: {e}"}

    verdict = str(obj.get("verdict", "")).upper().strip()
    reasoning = str(obj.get("reasoning", "")).strip()

    if verdict not in {"TRUE", "MISLEADING", "MIXED", "NO_RESULT"}:
        return {"verdict": "ERROR", "reasoning": f"Invalid verdict value: {verdict}"}

    return {"verdict": verdict, "reasoning": reasoning}
