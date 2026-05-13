"""SQLite-backed cache for AFC verdict results.

DB lives at <project_root>/data/claims.db, schema created lazily on first call.
Claim hash uses sha256 of `claim.strip().lower()` so capitalisation / whitespace
don't fragment the cache.
"""

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from systems.base import Verdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_DIR = PROJECT_ROOT / "data"
DB_PATH = DB_DIR / "claims.db"

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS claim_results (
    claim_hash TEXT PRIMARY KEY,
    claim_text TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    hit_count INTEGER NOT NULL DEFAULT 1,
    results_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_last_seen ON claim_results(last_seen_at);
"""


@contextmanager
def _connect():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_DDL)
    conn.commit()


def _hash(claim: str) -> str:
    return hashlib.sha256(claim.strip().lower().encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_cached(claim: str) -> Optional[List[Verdict]]:
    """Return cached verdicts for `claim`, bumping hit_count + last_seen_at.
    Returns None on miss.
    """
    h = _hash(claim)
    with _connect() as conn:
        _init_schema(conn)
        row = conn.execute(
            "SELECT results_json FROM claim_results WHERE claim_hash = ?",
            (h,),
        ).fetchone()
        if not row:
            return None
        conn.execute(
            "UPDATE claim_results SET last_seen_at = ?, hit_count = hit_count + 1 WHERE claim_hash = ?",
            (_now(), h),
        )
        conn.commit()
    return [Verdict.from_dict(d) for d in json.loads(row[0])]


def get_cache_meta(claim: str) -> Optional[dict]:
    """Return {'first_seen_at', 'hit_count'} for a cached claim without bumping.
    Returns None on miss.
    """
    h = _hash(claim)
    with _connect() as conn:
        _init_schema(conn)
        row = conn.execute(
            "SELECT first_seen_at, hit_count FROM claim_results WHERE claim_hash = ?",
            (h,),
        ).fetchone()
    if not row:
        return None
    return {"first_seen_at": row[0], "hit_count": row[1]}


def save_results(claim: str, results: List[Verdict]) -> None:
    """Insert or replace results for `claim`.

    - First save → hit_count = 1, first_seen_at = last_seen_at = now
    - Subsequent save (e.g. force re-run) → hit_count += 1, update last_seen_at
      and results_json, keep original first_seen_at

    Defensive: if EVERY system verdict is ERROR (e.g. all API keys missing),
    skip caching so a broken environment can't poison the cache permanently.
    """
    system_results = [r for r in results if r.system_id != "CN"]
    if system_results and all(r.verdict == "ERROR" for r in system_results):
        return

    h = _hash(claim)
    now = _now()
    payload = json.dumps([r.to_dict() for r in results])
    with _connect() as conn:
        _init_schema(conn)
        existing = conn.execute(
            "SELECT hit_count FROM claim_results WHERE claim_hash = ?",
            (h,),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE claim_results SET claim_text = ?, last_seen_at = ?, "
                "hit_count = hit_count + 1, results_json = ? WHERE claim_hash = ?",
                (claim.strip(), now, payload, h),
            )
        else:
            conn.execute(
                "INSERT INTO claim_results (claim_hash, claim_text, first_seen_at, "
                "last_seen_at, hit_count, results_json) VALUES (?, ?, ?, ?, 1, ?)",
                (h, claim.strip(), now, now, payload),
            )
        conn.commit()
