"""
AFC × Community Notes — Live Demonstrator
Yusuf Shakir, UWL Computer Science 2026
"""

import os
from pathlib import Path
from dotenv import load_dotenv

import streamlit as st

# Load .env from project root regardless of cwd, and override any stale
# values already in the shell environment.
load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

from utils.parallel import run_all_systems
from utils.cache import get_cached, get_cache_meta, save_results
from systems.base import Verdict, SYSTEM_REGISTRY

SESSION_RUN_CAP = 20

CN_ACCENT = "#fbbf24"  # gold for Community Notes reference card

# Per-system accent colors (used in legend + card edge)
SYSTEM_COLORS = {
    "A": "#a78bfa",  # violet — closed parametric
    "B": "#60a5fa",  # blue — naive RAG
    "C": "#34d399",  # emerald — pro DB
    "D": "#22d3ee",  # cyan — filtered RAG
    "E": "#fb923c",  # orange — open parametric
}


# ──────────────────────────────────────────────────────────────────────
# Page config + CSS
# ──────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AFC × Community Notes",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* Reset Streamlit chrome */
#MainMenu, footer, header,
[data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"] { display: none !important; }

html, body, .stApp {
    background:
        radial-gradient(ellipse 80% 60% at 50% -10%, rgba(99,102,241,0.12), transparent 60%),
        radial-gradient(ellipse 60% 40% at 90% 90%, rgba(168,85,247,0.06), transparent 50%),
        #09090b !important;
    color: #fafafa;
    font-family: "Inter", -apple-system, system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
}

.block-container {
    padding-top: 4rem !important;
    padding-bottom: 6rem !important;
    max-width: 1180px !important;
}

* { font-family: "Inter", -apple-system, system-ui, sans-serif; }

/* ─────────── HERO ─────────── */
.hero { margin-bottom: 3.5rem; }
.hero-tag {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: rgba(99,102,241,0.1);
    border: 1px solid rgba(99,102,241,0.25);
    color: #a5b4fc;
    padding: 0.35rem 0.85rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 500;
    margin-bottom: 1.5rem;
    letter-spacing: 0.2px;
}
.hero-tag .dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #818cf8;
    box-shadow: 0 0 8px #818cf8;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}
.hero h1 {
    font-size: 3.4rem;
    font-weight: 700;
    line-height: 1.05;
    letter-spacing: -2px;
    margin: 0 0 1.2rem 0;
    background: linear-gradient(180deg, #ffffff 0%, #a1a1aa 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    max-width: 900px;
}
.hero h1 .accent {
    background: linear-gradient(135deg, #818cf8 0%, #c084fc 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.hero p {
    font-size: 1.15rem;
    color: #a1a1aa;
    line-height: 1.6;
    max-width: 720px;
    margin: 0 0 1.8rem 0;
    font-weight: 400;
}
.hero .byline {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    color: #71717a;
    font-size: 0.85rem;
    font-weight: 500;
}
.hero .byline .pip { color: #3f3f46; }
.hero .byline strong { color: #d4d4d8; font-weight: 600; }

/* ─────────── Section heading ─────────── */
.section-head {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    margin: 3rem 0 1.4rem 0;
}
.section-head .num {
    width: 24px; height: 24px;
    border-radius: 6px;
    background: rgba(99,102,241,0.12);
    border: 1px solid rgba(99,102,241,0.25);
    color: #a5b4fc;
    font-size: 0.72rem;
    font-weight: 600;
    display: flex; align-items: center; justify-content: center;
    font-family: "JetBrains Mono", monospace;
}
.section-head .title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #fafafa;
    letter-spacing: -0.3px;
}
.section-head .hint {
    color: #71717a;
    font-size: 0.85rem;
    font-weight: 400;
    margin-left: 0.4rem;
}

/* ─────────── System legend ─────────── */
.legend-card {
    background: linear-gradient(180deg, rgba(255,255,255,0.025) 0%, transparent 100%), #131316;
    border: 1px solid #232328;
    border-radius: 10px;
    padding: 1.1rem 1.2rem;
    height: 100%;
    position: relative;
    overflow: hidden;
    transition: all 0.2s ease;
}
.legend-card::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: var(--accent);
}
.legend-card:hover {
    transform: translateY(-2px);
    border-color: #34343c;
}
.legend-id {
    display: inline-block;
    font-family: "JetBrains Mono", monospace;
    font-size: 0.62rem;
    font-weight: 600;
    color: var(--accent);
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 0.6rem;
    padding: 0.2rem 0.5rem;
    background: var(--accent-bg);
    border-radius: 4px;
}
.legend-name {
    font-size: 0.98rem;
    color: #fafafa;
    font-weight: 600;
    line-height: 1.25;
    margin-bottom: 0.3rem;
    letter-spacing: -0.2px;
}
.legend-paradigm {
    font-size: 0.78rem;
    color: #a1a1aa;
    line-height: 1.4;
    font-weight: 400;
}

/* ─────────── Form ─────────── */
.stTextArea label { display: none !important; }
.stTextArea > div { border-radius: 12px !important; }
.stTextArea textarea {
    background-color: #131316 !important;
    border: 1px solid #27272a !important;
    color: #fafafa !important;
    font-family: "Inter", sans-serif !important;
    font-size: 1rem !important;
    border-radius: 12px !important;
    padding: 1.1rem 1.2rem !important;
    line-height: 1.5 !important;
    transition: all 0.15s ease !important;
}
.stTextArea textarea:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
    outline: none !important;
}
.stTextArea textarea::placeholder { color: #52525b !important; }

/* Submit button (inside form) */
.stForm .stButton > button, .stForm button[type="submit"] {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
    color: #ffffff !important;
    border: 0 !important;
    padding: 0.75rem 1.6rem !important;
    font-family: "Inter", sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
    border-radius: 10px !important;
    box-shadow: 0 4px 16px -4px rgba(99,102,241,0.4), 0 0 0 1px rgba(255,255,255,0.05) inset !important;
    transition: all 0.15s ease !important;
    letter-spacing: -0.1px !important;
}
.stForm button:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px -4px rgba(99,102,241,0.55), 0 0 0 1px rgba(255,255,255,0.08) inset !important;
}
.stForm button:active { transform: translateY(0); }

/* Example chip buttons (outside form, in horizontal block) */
div[data-testid="stHorizontalBlock"] .stButton > button {
    background: #131316 !important;
    color: #d4d4d8 !important;
    border: 1px solid #27272a !important;
    padding: 0.85rem 1rem !important;
    font-family: "Inter", sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 400 !important;
    border-radius: 10px !important;
    text-align: left !important;
    line-height: 1.45 !important;
    transition: all 0.15s ease !important;
    white-space: normal !important;
    height: auto !important;
    min-height: 3.5rem !important;
    letter-spacing: -0.1px !important;
}
div[data-testid="stHorizontalBlock"] .stButton > button:hover {
    border-color: #4f46e5 !important;
    background: #18181c !important;
    color: #fafafa !important;
    transform: translateY(-1px);
}

.runs-indicator {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    font-family: "JetBrains Mono", monospace;
    font-size: 0.75rem;
    color: #71717a;
    padding-top: 1rem;
}
.runs-indicator .bar {
    width: 60px;
    height: 4px;
    background: #27272a;
    border-radius: 2px;
    overflow: hidden;
    position: relative;
}
.runs-indicator .bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    border-radius: 2px;
}

.try-label {
    color: #71717a;
    font-size: 0.8rem;
    font-weight: 500;
    margin: 1.8rem 0 0.8rem 0;
    letter-spacing: -0.1px;
}

/* ─────────── Summary strip ─────────── */
.summary-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 0.7rem;
    margin-bottom: 1.8rem;
}
.summary-card {
    background: linear-gradient(180deg, rgba(255,255,255,0.02) 0%, transparent 100%), #131316;
    border: 1px solid #232328;
    border-radius: 10px;
    padding: 1.1rem 1.2rem;
    transition: border-color 0.15s ease;
}
.summary-card .lbl {
    font-size: 0.72rem;
    color: #71717a;
    font-weight: 500;
    margin-bottom: 0.5rem;
    letter-spacing: 0.1px;
}
.summary-card .val {
    font-size: 1.8rem;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -1.5px;
    color: #fafafa;
}
.summary-card .val.dim { color: #3f3f46; }
.summary-card.t-TRUE .val        { color: #34d399; }
.summary-card.t-MISLEADING .val  { color: #f87171; }
.summary-card.t-MIXED .val       { color: #fbbf24; }
.summary-card.t-NORES .val       { color: #71717a; }
.summary-card.t-LAT  .val        { color: #a78bfa; font-size: 1.5rem; }

/* ─────────── Verdict cards ─────────── */
.verdict-card {
    background:
        linear-gradient(180deg, rgba(255,255,255,0.02) 0%, transparent 100%),
        #131316;
    border: 1px solid #232328;
    border-radius: 14px;
    padding: 1.5rem 1.7rem;
    margin-bottom: 1rem;
    position: relative;
    overflow: hidden;
    transition: all 0.2s ease;
}
.verdict-card::before {
    content: "";
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: var(--accent);
}
.verdict-card:hover {
    border-color: #34343c;
    background:
        linear-gradient(180deg, rgba(255,255,255,0.03) 0%, transparent 100%),
        #15151a;
}

.verdict-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1.5rem;
    margin-bottom: 1rem;
}
.system-meta { flex: 1; min-width: 0; }
.system-id-tag {
    display: inline-block;
    font-family: "JetBrains Mono", monospace;
    font-size: 0.65rem;
    font-weight: 600;
    color: var(--accent);
    letter-spacing: 1.5px;
    text-transform: uppercase;
    padding: 0.25rem 0.55rem;
    background: var(--accent-bg);
    border-radius: 4px;
    margin-bottom: 0.6rem;
}
.system-name {
    font-size: 1.25rem;
    font-weight: 600;
    color: #fafafa;
    line-height: 1.2;
    margin-bottom: 0.25rem;
    letter-spacing: -0.3px;
}
.system-paradigm {
    font-size: 0.85rem;
    color: #a1a1aa;
    font-weight: 400;
}

.verdict-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.3px;
    padding: 0.45rem 0.85rem;
    border-radius: 8px;
    white-space: nowrap;
    border: 1px solid;
    flex-shrink: 0;
}
.verdict-badge::before {
    content: "";
    width: 6px; height: 6px; border-radius: 50%;
    background: currentColor;
    box-shadow: 0 0 8px currentColor;
}
.badge-TRUE       { color: #34d399; border-color: rgba(52,211,153,0.3); background: rgba(52,211,153,0.1); }
.badge-MISLEADING { color: #f87171; border-color: rgba(248,113,113,0.3); background: rgba(248,113,113,0.1); }
.badge-MIXED      { color: #fbbf24; border-color: rgba(251,191,36,0.3); background: rgba(251,191,36,0.1); }
.badge-NO_RESULT  { color: #a1a1aa; border-color: rgba(161,161,170,0.25); background: rgba(161,161,170,0.08); }
.badge-ERROR      { color: #f87171; border-color: rgba(248,113,113,0.2); background: rgba(248,113,113,0.06); }

.reasoning {
    color: #d4d4d8;
    font-size: 0.97rem;
    line-height: 1.6;
    margin: 0;
    font-weight: 400;
}

.meta-row {
    font-family: "JetBrains Mono", monospace;
    font-size: 0.72rem;
    color: #71717a;
    margin-top: 1.2rem;
    padding-top: 1rem;
    border-top: 1px solid #232328;
    display: flex;
    gap: 1.5rem;
    flex-wrap: wrap;
    align-items: center;
}
.meta-row .meta-key { color: #52525b; margin-right: 0.45rem; }
.meta-row a {
    color: #818cf8;
    text-decoration: none;
    transition: color 0.15s;
}
.meta-row a:hover { color: #a5b4fc; }

/* Footer */
.app-footer {
    margin-top: 5rem;
    padding-top: 2rem;
    border-top: 1px solid #1f1f23;
    color: #52525b;
    font-size: 0.8rem;
    text-align: center;
    line-height: 1.7;
    font-weight: 400;
}
.app-footer .sep { color: #27272a; margin: 0 0.7rem; }

/* Spinner */
.stSpinner > div > div { border-top-color: #8b5cf6 !important; }

/* Alerts */
.stAlert {
    background: #131316 !important;
    border: 1px solid #27272a !important;
    border-radius: 10px !important;
    color: #fafafa !important;
}

/* Spacing tweaks */
.element-container { margin-bottom: 0 !important; }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────
# Session state
# ──────────────────────────────────────────────────────────────────────
if "runs_used" not in st.session_state:
    st.session_state.runs_used = 0
if "last_results" not in st.session_state:
    st.session_state.last_results = None
if "last_claim" not in st.session_state:
    st.session_state.last_claim = ""
if "last_cache_meta" not in st.session_state:
    st.session_state.last_cache_meta = None  # {'first_seen_at', 'hit_count'} or None


# ──────────────────────────────────────────────────────────────────────
# Hero
# ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-tag"><span class="dot"></span> Live demonstrator · BSc Dissertation 2026</div>
  <h1>Five fact-checkers,<br>one claim, <span class="accent">side-by-side</span>.</h1>
  <p>Two parametric LLMs, two retrieval-augmented variants, and one professional fact-check database — running in parallel against any claim you give them. Watch where they agree, where they disagree, and what that disagreement reveals.</p>
  <div class="byline">
    <strong>Yusuf Shakir</strong>
    <span class="pip">/</span>
    BSc Computer Science
    <span class="pip">/</span>
    University of West London
  </div>
</div>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────
# System legend
# ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="section-head">
  <div class="num">01</div>
  <div class="title">The systems</div>
  <div class="hint">— five different paradigms</div>
</div>
""", unsafe_allow_html=True)

legend_cols = st.columns(5, gap="small")
for i, sid in enumerate(["A", "B", "C", "D", "E"]):
    info = SYSTEM_REGISTRY[sid]
    color = SYSTEM_COLORS[sid]
    with legend_cols[i]:
        st.markdown(f"""
        <div class="legend-card" style="--accent:{color};--accent-bg:{color}1f;">
          <div class="legend-id">System {sid}</div>
          <div class="legend-name">{info['name']}</div>
          <div class="legend-paradigm">{info['paradigm']}</div>
        </div>
        """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────
# Claim input
# ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="section-head">
  <div class="num">02</div>
  <div class="title">Submit a claim</div>
  <div class="hint">— or pick an example below</div>
</div>
""", unsafe_allow_html=True)

EXAMPLE_CLAIMS = [
    "The Great Wall of China is visible from space with the naked eye.",
    "Drinking 8 glasses of water per day is required for good health.",
    "The COVID-19 mRNA vaccines alter human DNA.",
    "Brandon Herrera was born in Texas.",
]

with st.form("claim_form", clear_on_submit=False):
    claim = st.text_area(
        label="claim_input",
        value=st.session_state.last_claim,
        height=120,
        placeholder='e.g. "The Great Wall of China is visible from space with the naked eye."',
        label_visibility="collapsed",
        max_chars=600,
    )
    force_rerun = st.checkbox(
        "Force re-run (skip cache)",
        value=False,
        help="Bypass the SQLite cache and query all five systems fresh. Counts against the 20-run session cap.",
    )
    col_a, col_b = st.columns([1, 3])
    with col_a:
        submitted = st.form_submit_button("Run benchmark →", use_container_width=True)
    with col_b:
        runs_left = SESSION_RUN_CAP - st.session_state.runs_used
        fill_pct = int(100 * st.session_state.runs_used / SESSION_RUN_CAP)
        st.markdown(f"""
        <div class="runs-indicator">
          <div class="bar"><div class="bar-fill" style="width:{fill_pct}%;"></div></div>
          {runs_left}/{SESSION_RUN_CAP} fresh runs left
        </div>
        """, unsafe_allow_html=True)

st.markdown('<div class="try-label">Try one of these</div>', unsafe_allow_html=True)
ex_cols = st.columns(len(EXAMPLE_CLAIMS), gap="small")
for i, ex in enumerate(EXAMPLE_CLAIMS):
    with ex_cols[i]:
        if st.button(ex, key=f"ex_{i}", use_container_width=True):
            st.session_state.last_claim = ex
            st.rerun()


# ──────────────────────────────────────────────────────────────────────
# Run
# ──────────────────────────────────────────────────────────────────────
if submitted and claim.strip():
    claim_clean = claim.strip()

    cached_results = None
    if not force_rerun:
        cached_results = get_cached(claim_clean)

    if cached_results is not None:
        # Cache hit — do NOT decrement the session cap
        st.session_state.last_claim = claim
        st.session_state.last_results = cached_results
        st.session_state.last_cache_meta = get_cache_meta(claim_clean)
    else:
        # Fresh run (miss OR force re-run) — counts against the cap
        if st.session_state.runs_used >= SESSION_RUN_CAP:
            st.error(f"Session cap of {SESSION_RUN_CAP} fresh runs reached. Refresh the page to reset.")
        else:
            st.session_state.runs_used += 1
            st.session_state.last_claim = claim
            with st.spinner("Querying five systems in parallel…"):
                results = run_all_systems(claim_clean)
            save_results(claim_clean, results)
            st.session_state.last_results = results
            st.session_state.last_cache_meta = None


# ──────────────────────────────────────────────────────────────────────
# Results
# ──────────────────────────────────────────────────────────────────────
results = st.session_state.last_results
if results:
    # Split off CN gold-reference entry (if present) from the five system verdicts
    cn_entry = next((r for r in results if r.system_id == "CN"), None)
    system_results = [r for r in results if r.system_id != "CN"]

    st.markdown("""
    <div class="section-head">
      <div class="num">03</div>
      <div class="title">Verdicts</div>
      <div class="hint">— five systems, one claim</div>
    </div>
    """, unsafe_allow_html=True)

    # Cache-hit badge (inline-styled to match existing card aesthetic; no CSS edits)
    meta = st.session_state.last_cache_meta
    if meta:
        first_seen_date = (meta["first_seen_at"] or "")[:10]
        st.markdown(f"""
        <div style="display:inline-flex;align-items:center;gap:0.55rem;
                    background:rgba(99,102,241,0.10);
                    border:1px solid rgba(99,102,241,0.28);
                    color:#a5b4fc;
                    padding:0.45rem 0.95rem;
                    border-radius:8px;
                    font-family:'JetBrains Mono',monospace;
                    font-size:0.74rem;
                    font-weight:500;
                    letter-spacing:0.2px;
                    margin-bottom:1.2rem;">
          <span style="width:6px;height:6px;border-radius:50%;background:#818cf8;box-shadow:0 0 8px #818cf8;"></span>
          cached · first seen {first_seen_date} · run {meta["hit_count"]} times
        </div>
        """, unsafe_allow_html=True)

    # Summary strip — counts EXCLUDE the CN gold-reference entry
    verdicts = [r.verdict for r in system_results]
    counts = {v: verdicts.count(v) for v in ["TRUE", "MISLEADING", "MIXED", "NO_RESULT", "ERROR"]}
    avg_latency = int(sum(r.latency_ms for r in system_results) / max(len(system_results), 1))

    summary_cells = [
        ("True",        counts["TRUE"],                              "TRUE"),
        ("Misleading",  counts["MISLEADING"],                        "MISLEADING"),
        ("Mixed",       counts["MIXED"],                             "MIXED"),
        ("No result",   counts["NO_RESULT"] + counts["ERROR"],       "NORES"),
        ("Avg latency", f"{avg_latency}ms",                          "LAT"),
    ]
    summary_html = '<div class="summary-grid">'
    for label, val, kind in summary_cells:
        dim_class = " dim" if (isinstance(val, int) and val == 0) else ""
        summary_html += f"""
        <div class="summary-card t-{kind}">
          <div class="lbl">{label}</div>
          <div class="val{dim_class}">{val}</div>
        </div>"""
    summary_html += '</div>'
    st.markdown(summary_html, unsafe_allow_html=True)

    # CN gold-reference row (rendered above the five system cards, when present)
    if cn_entry is not None:
        st.markdown(f"""
        <div style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;color:#71717a;
                    letter-spacing:1.5px;text-transform:uppercase;margin:0.6rem 0 0.7rem 0;">
          Community Notes verdict — gold reference
        </div>
        <div class="verdict-card" style="--accent:{CN_ACCENT};--accent-bg:{CN_ACCENT}1f;">
          <div class="verdict-header">
            <div class="system-meta">
              <div class="system-id-tag">CN · Gold reference</div>
              <div class="system-name">{cn_entry.system_name}</div>
              <div class="system-paradigm">{cn_entry.paradigm}</div>
            </div>
            <span class="verdict-badge badge-{cn_entry.verdict}">{cn_entry.verdict}</span>
          </div>
          <p class="reasoning">{cn_entry.reasoning}</p>
        </div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;color:#71717a;
                    letter-spacing:1.5px;text-transform:uppercase;margin:1.6rem 0 0.7rem 0;">
          System verdicts
        </div>
        """, unsafe_allow_html=True)

    # Five system cards
    for r in system_results:
        color = SYSTEM_COLORS.get(r.system_id, "#a1a1aa")
        sources_html = ""
        if r.sources:
            valid_sources = [s for s in r.sources if s]
            if valid_sources:
                source_links = " · ".join(
                    f'<a href="{s}" target="_blank">{s.split("//")[-1].split("/")[0][:32]}</a>'
                    for s in valid_sources[:3]
                )
                sources_html = f'<span><span class="meta-key">sources</span>{source_links}</span>'

        st.markdown(f"""
        <div class="verdict-card" style="--accent:{color};--accent-bg:{color}1f;">
          <div class="verdict-header">
            <div class="system-meta">
              <div class="system-id-tag">System {r.system_id}</div>
              <div class="system-name">{r.system_name}</div>
              <div class="system-paradigm">{r.paradigm}</div>
            </div>
            <span class="verdict-badge badge-{r.verdict}">{r.verdict}</span>
          </div>
          <p class="reasoning">{r.reasoning}</p>
          <div class="meta-row">
            <span><span class="meta-key">latency</span>{r.latency_ms} ms</span>
            {sources_html}
          </div>
        </div>
        """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-footer">
  Companion artefact to the dissertation<span class="sep">·</span>offline benchmark: 5,469 claims<span class="sep">·</span>built with Streamlit<br>
  Yusuf Shakir<span class="sep">·</span>University of West London<span class="sep">·</span>2026
</div>
""", unsafe_allow_html=True)
