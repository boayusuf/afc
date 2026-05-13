"""One-shot loader: import an offline AFC benchmark CSV into the cache DB.

Accepts either:
  (a) the original spec schema with columns:
      claim_text, system_a_verdict, system_a_reasoning, ..., system_e_*, cn_verdict
  (b) the dissertation master_results.csv schema with columns:
      extracted_claim, gpt4o_verdict, gpt4o_reasoning,
      tavily_gpt4o_verdict, tavily_gpt4o_reasoning,
      google_verdict, google_source/google_raw_rating,
      filtered_rag_verdict, filtered_rag_reasoning,
      llama_verdict, llama_reasoning,
      cn_verdict

Run from project root:
    python scripts/load_dataset.py                       # uses data/cn_dataset_5469.csv
    python scripts/load_dataset.py path/to/some.csv      # explicit path
Idempotent — existing rows (matched by claim_hash) are skipped.
"""

import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from systems.base import Verdict, SYSTEM_REGISTRY, VERDICT_VALUES
from utils.cache import _connect, _init_schema, _hash

DEFAULT_CSV = PROJECT_ROOT / "data" / "cn_dataset_5469.csv"
SEED_TIMESTAMP = "2026-04-15T00:00:00"
SEED_HIT_COUNT = 1   # the offline benchmark run itself

# Column-name aliases per system. First key found in the row wins.
# Each system_id maps to a list of (verdict_col_candidates, reasoning_col_candidates).
SCHEMA_MAP = {
    "A": (
        ["system_a_verdict", "gpt4o_verdict"],
        ["system_a_reasoning", "gpt4o_reasoning"],
    ),
    "B": (
        ["system_b_verdict", "tavily_gpt4o_verdict"],
        ["system_b_reasoning", "tavily_gpt4o_reasoning", "tavily_evidence_summary"],
    ),
    "C": (
        ["system_c_verdict", "google_verdict"],
        ["system_c_reasoning", "google_raw_rating", "google_source"],
    ),
    "D": (
        ["system_d_verdict", "filtered_rag_verdict"],
        ["system_d_reasoning", "filtered_rag_reasoning"],
    ),
    "E": (
        ["system_e_verdict", "llama_verdict"],
        ["system_e_reasoning", "llama_reasoning"],
    ),
}
CLAIM_COL_CANDIDATES = ["claim_text", "extracted_claim", "claim", "summary"]
CN_COL = "cn_verdict"


def _pick(row: dict, candidates: list) -> str:
    for col in candidates:
        if col in row and (row[col] or "").strip():
            return row[col]
    return ""


def _norm_verdict(raw: str) -> str:
    v = (raw or "").strip().upper().replace(" ", "_").replace("-", "_")
    # Common alt spellings seen in benchmark outputs
    if v in {"FALSE", "MISLEADING_FALSE", "INACCURATE"}:
        return "MISLEADING"
    if v in {"PARTLY_TRUE", "PARTLY_FALSE", "HALF_TRUE", "MIXTURE", "MIXED"}:
        return "MIXED"
    if v in {"TRUE", "ACCURATE", "CORRECT", "MOSTLY_TRUE"}:
        return "TRUE"
    if v in VERDICT_VALUES and v != "ERROR":
        return v
    return "NO_RESULT"


def _build_verdicts(row: dict) -> list:
    out = []
    for sid, (v_cols, r_cols) in SCHEMA_MAP.items():
        info = SYSTEM_REGISTRY[sid]
        v = _norm_verdict(_pick(row, v_cols))
        r = (_pick(row, r_cols) or "").strip()
        reasoning = f"{r}  · (from offline benchmark)" if r else "(from offline benchmark — no reasoning recorded)"
        out.append(Verdict(
            system_id=sid,
            system_name=info["name"],
            paradigm=info["paradigm"],
            verdict=v,
            reasoning=reasoning,
            latency_ms=0,
            sources=[],
        ))

    cn_raw = (row.get(CN_COL) or "").strip()
    if cn_raw:
        out.append(Verdict(
            system_id="CN",
            system_name="Community Notes",
            paradigm="Gold-standard reference",
            verdict=_norm_verdict(cn_raw),
            reasoning="Community Notes consensus rating (offline benchmark dataset).",
            latency_ms=0,
            sources=[],
        ))
    return out


def main(argv: list) -> int:
    csv_path = Path(argv[1]).resolve() if len(argv) > 1 else DEFAULT_CSV
    if not csv_path.exists():
        print(f"ERROR: dataset CSV not found at {csv_path}", file=sys.stderr)
        print("Pass an explicit path:  python scripts/load_dataset.py PATH_TO_CSV", file=sys.stderr)
        return 1

    print(f"Loading from: {csv_path}")
    inserted = 0
    skipped = 0
    total_in_db = 0

    with _connect() as conn:
        _init_schema(conn)
        with open(csv_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                claim = _pick(row, CLAIM_COL_CANDIDATES).strip()
                if not claim:
                    continue
                h = _hash(claim)
                exists = conn.execute(
                    "SELECT 1 FROM claim_results WHERE claim_hash = ?", (h,)
                ).fetchone()
                if exists:
                    skipped += 1
                    continue
                verdicts = _build_verdicts(row)
                payload = json.dumps([v.to_dict() for v in verdicts])
                conn.execute(
                    "INSERT INTO claim_results (claim_hash, claim_text, first_seen_at, "
                    "last_seen_at, hit_count, results_json) VALUES (?, ?, ?, ?, ?, ?)",
                    (h, claim, SEED_TIMESTAMP, SEED_TIMESTAMP, SEED_HIT_COUNT, payload),
                )
                inserted += 1
        conn.commit()
        total_in_db = conn.execute("SELECT COUNT(*) FROM claim_results").fetchone()[0]

    print(f"Loader complete:")
    print(f"  inserted: {inserted}")
    print(f"  skipped (already present): {skipped}")
    print(f"  total rows in DB: {total_in_db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
