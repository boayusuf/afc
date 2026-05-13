"""Run all 5 AFC systems in parallel and collect results."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from systems import ALL_SYSTEMS, SYSTEM_REGISTRY
from systems.base import Verdict


PER_SYSTEM_TIMEOUT_S = 35


def run_all_systems(claim: str) -> List[Verdict]:
    """Dispatch all 5 systems concurrently. Returns verdicts in A..E order."""
    results = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        future_to_id = {pool.submit(fn, claim): sid for sid, fn in ALL_SYSTEMS.items()}
        for future in as_completed(future_to_id, timeout=PER_SYSTEM_TIMEOUT_S + 5):
            sid = future_to_id[future]
            try:
                results[sid] = future.result(timeout=2)
            except Exception as e:
                info = SYSTEM_REGISTRY[sid]
                results[sid] = Verdict(
                    system_id=sid,
                    system_name=info["name"],
                    paradigm=info["paradigm"],
                    verdict="ERROR",
                    reasoning=f"Timeout or worker error: {type(e).__name__}",
                    latency_ms=PER_SYSTEM_TIMEOUT_S * 1000,
                    error=str(e)[:200],
                )

    # Return in canonical order A..E
    return [results.get(sid) for sid in ["A", "B", "C", "D", "E"] if sid in results]
