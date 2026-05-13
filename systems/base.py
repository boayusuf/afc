"""Shared schema for AFC system verdicts."""

from dataclasses import dataclass, field
from typing import Optional


VERDICT_VALUES = {"TRUE", "MISLEADING", "MIXED", "NO_RESULT", "ERROR"}


@dataclass
class Verdict:
    """A single system's response to a claim."""

    system_id: str           # "A".."E"
    system_name: str         # human-readable
    paradigm: str            # "Parametric LLM (closed)" etc
    verdict: str             # one of VERDICT_VALUES
    reasoning: str           # 1-3 sentence justification
    latency_ms: int          # wall-clock from request to response
    sources: list = field(default_factory=list)   # retrieved URLs if any
    error: Optional[str] = None  # populated if verdict == "ERROR"

    def __post_init__(self):
        if self.verdict not in VERDICT_VALUES:
            self.verdict = "ERROR"
            self.error = f"Invalid verdict: {self.verdict}"

    def to_dict(self) -> dict:
        return {
            "system_id": self.system_id,
            "system_name": self.system_name,
            "paradigm": self.paradigm,
            "verdict": self.verdict,
            "reasoning": self.reasoning,
            "latency_ms": self.latency_ms,
            "sources": list(self.sources or []),
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Verdict":
        return cls(
            system_id=d["system_id"],
            system_name=d["system_name"],
            paradigm=d["paradigm"],
            verdict=d["verdict"],
            reasoning=d.get("reasoning", ""),
            latency_ms=int(d.get("latency_ms", 0) or 0),
            sources=list(d.get("sources") or []),
            error=d.get("error"),
        )


SYSTEM_REGISTRY = {
    "A": {"name": "GPT-4o", "paradigm": "Parametric LLM (closed-source)"},
    "B": {"name": "GPT-4o + Tavily RAG", "paradigm": "Naive RAG"},
    "C": {"name": "Google Fact Check API", "paradigm": "Professional FC database"},
    "D": {"name": "GPT-4o + Filtered RAG", "paradigm": "Credibility-filtered RAG"},
    "E": {"name": "Llama 3.3 70B", "paradigm": "Parametric LLM (open-source)"},
}
