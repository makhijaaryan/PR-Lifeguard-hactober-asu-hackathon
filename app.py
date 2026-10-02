"""PR Lifeguard - Streamlit frontend.

Backend switch: set LIVE_BACKEND below to the module exposing triage() and history()
(the real pipeline). If it can't be imported, the app falls back to the fake data in contract.py.

Demo mode: every successful real triage is saved to demo_cache.json (keyed by repo). With demo mode
on, a cached repo loads instantly (with a short fake progress animation); otherwise it runs normally.
"""
import html
import importlib
import json
import re
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import contract

LIVE_BACKEND = "pipeline"  # <- the one-line switch to the real backend

try:
    live = importlib.import_module(LIVE_BACKEND)
except Exception:  # not written yet, or missing credentials
    live = None

REPO_RE = re.compile(r"^https?://github\.com/[\w.-]+/[\w.-]+/?$")
DEMO_REPO = "https://github.com/pallets/flask"
CACHE_PATH = Path(__file__).resolve().parent / "demo_cache.json"


def get_backend():
    """Return (triage, history): the live pipeline if importable, else the fake contract data."""
    if live is None:
        return contract.fake_triage, contract.fake_history
    return live.triage, live.history


def repo_key(url):
    """'https://github.com/Owner/Name/' -> 'owner/name'"""
    return "/".join(url.strip().rstrip("/").split("/")[-2:]).lower()


def read_cache():
    try:
        return json.loads(CACHE_PATH.read_text())
    except Exception:  # missing or corrupt file: treat as empty
        return {}


def save_to_cache(url, result):
    """Best-effort save; a cache failure must never break the demo."""
    try:
        cache = read_cache()
        cache[repo_key(url)] = result
        tmp = CACHE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(cache, indent=2))
        tmp.replace(CACHE_PATH)
    except Exception:
        pass


def replay_cached(result, limit, bar):
    """Short fake progress so a cached result still looks live."""
    steps = [("Fetching open pull requests...", 0.25), ("Running rule checks...", 0.55),
             ("Reviewing PRs with the model...", 0.85), ("Saving results...", 1.0)]
    for msg, frac in steps:
        bar.progress(frac, text=msg)
        time.sleep(0.35)
    return {**result, "prs": result["prs"][:limit]}


st.set_page_config(page_title="PR Lifeguard", layout="wide", initial_sidebar_state="expanded")

TIER_STYLE = {
    "Review first": ("#34d399", "rgba(52,211,153,.14)"),
    "Needs info": ("#fbbf24", "rgba(251,191,36,.14)"),
    "Likely low-effort": ("#f87171", "rgba(248,113,113,.14)"),
}

CSS = """
<style>
html {font-size: 18px;}
#MainMenu, footer, header[data-testid="stHeader"] {visibility: hidden; height: 0;}
.block-container {padding-top: 2rem; max-width: 1200px;}
.hero {padding: 1.6rem 1.8rem; border-radius: 18px; margin-bottom: 1.2rem;
  background: radial-gradient(circle at 0% 0%, rgba(56,189,248,.22), transparent 55%),
              linear-gradient(135deg, #111a2e, #0b1220);
  border: 1px solid rgba(148,163,184,.18);}
.hero h1 {margin: 0; font-size: 2.6rem; letter-spacing: -.02em;}
.hero p {margin: .35rem 0 0; color: #c3cfe0; font-size: 1.1rem;}
.stat {padding: 1rem 1.2rem; border-radius: 14px; background: #111a2e;
  border: 1px solid rgba(148,163,184,.16);}
.stat .n {font-size: 2.4rem; font-weight: 700; line-height: 1.1;}
.stat .l {color: #c3cfe0; font-size: .85rem; text-transform: uppercase; letter-spacing: .08em;}
.card {padding: 1rem 1.2rem; border-radius: 14px; background: #111a2e; margin-bottom: .2rem;
  border: 1px solid rgba(148,163,184,.16); display: flex; gap: 1rem; align-items: center;}
.score {min-width: 66px; height: 66px; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; font-weight: 800; font-size: 1.5rem;}
.card .t {font-weight: 700; font-size: 1.2rem;}
.card .t a {color: inherit; text-decoration: none;}
.card .t a:hover {text-decoration: underline;}
.card .m {color: #c3cfe0; font-size: .95rem; margin-top: .15rem;}
.card .r {color: #e6edf7; font-size: 1.02rem; margin-top: .35rem;}
.pill {display: inline-block; padding: .1rem .6rem; border-radius: 999px; font-size: .8rem;
  font-weight: 700; margin-left: .5rem; vertical-align: middle;}
.chips {margin-top: .55rem; display: flex; flex-wrap: wrap; gap: .35rem;}
.chip {padding: .12rem .6rem; border-radius: 999px; font-size: .8rem; font-weight: 600; cursor: help;}
.chip.ok {color: #34d399; background: rgba(52,211,153,.14); border: 1px solid rgba(52,211,153,.35);}
.chip.off {color: #b8c4d6; background: rgba(148,163,184,.10); border: 1px solid rgba(148,163,184,.25);}
.sbox {padding: .9rem 1rem; border-radius: 12px; background: #0b1220; border: 1px solid rgba(148,163,184,.18);
  font-size: .95rem; color: #e6edf7; line-height: 1.5;}
.sbox b {color: #e6edf7;}
.sval {font-weight: 600; word-break: break-word;}
.badge {display: inline-block; min-width: 3.1rem; text-align: center; padding: .05rem .5rem;
  border-radius: 6px; font-size: .75rem; font-weight: 700; letter-spacing: .05em; margin-right: .6rem;}
.ok {color: #34d399; background: rgba(52,211,153,.14);}
.bad {color: #f87171; background: rgba(248,113,113,.14);}
.warn {color: #fbbf24; background: rgba(251,191,36,.14);}
div[data-testid="stExpander"] {border: none; margin-bottom: .9rem;}
div[data-testid="stExpander"] details {border: 1px solid rgba(148,163,184,.12); border-radius: 12px;}
.step {padding: 1.3rem 1.4rem; border-radius: 14px; background: #111a2e; height: 100%;
  border: 1px solid rgba(148,163,184,.2);}
.step svg {width: 38px; height: 38px; stroke: #38bdf8; fill: none; stroke-width: 1.8;
  stroke-linecap: round; stroke-linejoin: round;}
.step .k {color: #38bdf8; font-weight: 700; font-size: .85rem; letter-spacing: .08em; margin-top: .6rem;}
.step .h {font-weight: 700; font-size: 1.2rem; margin: .1rem 0 .3rem;}
.step .d {color: #c3cfe0; font-size: 1rem; line-height: 1.45;}
.stButton>button[kind="primary"] {border-radius: 10px; font-weight: 700; height: 3.2rem; font-size: 1.1rem;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def esc(s):
    return html.escape(str(s))


def stat(col, number, label, color="#e6edf7"):
    col.markdown(
        f'<div class="stat"><div class="n" style="color:{color}">{number}</div>'
        f'<div class="l">{label}</div></div>',
        unsafe_allow_html=True,
    )


def badge(passed):
    return f'<span class="badge {"ok" if passed else "bad"}">{"PASS" if passed else "FAIL"}</span>'


def chip(name, flag):
    flag = flag if isinstance(flag, dict) else {}
    cls = "ok" if flag.get("passed") else "off"
    label = str(name).replace("_", " ")
    return f'<span class="chip {cls}" title="{esc(flag.get("note", ""))}">{esc(label)}</span>'


def pr_card(pr):
    tier = pr.get("tier", "")
    color, bg = TIER_STYLE.get(tier, ("#b8c4d6", "rgba(148,163,184,.14)"))
    chips = "".join(chip(n, f) for n, f in (pr.get("rule_flags") or {}).items())
    url = pr.get("url") or "#"
    st.markdown(
        f"""<div class="card">
          <div class="score" style="color:{color};background:{bg};border:2px solid {color}">{esc(pr.get("final_score", "-"))}</div>
          <div style="flex:1">
            <div class="t"><a href="{esc(url)}" target="_blank">{esc(pr.get("title", "(untitled)"))}</a>
              <span class="pill" style="color:{color};background:{bg}">{esc(tier)}</span></div>
            <div class="m">#{esc(pr.get("number", "?"))} by @{esc(pr.get("author", "unknown"))}</div>
            <div class="r">{esc(pr.get("reason", ""))}</div>
            <div class="chips">{chips}</div>
          </div></div>""",
        unsafe_allow_html=True,
    )
    with st.expander("Details and draft reply"):
        st.markdown("**Guideline issues**")
        issues = pr.get("guideline_issues") or []
        if issues:
            for issue in issues:
                st.markdown(f'<span class="badge warn">NOTE</span>{esc(issue)}', unsafe_allow_html=True)
        else:
            st.markdown('<span class="badge ok">PASS</span>No guideline issues found.', unsafe_allow_html=True)
        m = pr.get("description_matches_code") or {}
        st.markdown("**Description matches code**")
        st.markdown(badge(m.get("value")) + esc(m.get("note", "")), unsafe_allow_html=True)
        st.markdown("**Draft reply**")
        st.code(pr.get("draft_reply") or "", language=None, wrap_lines=True)


STEPS = [
    ("STEP 1", "Paste a repo", "Drop in any public GitHub repository URL.",
     '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>'),
    ("STEP 2", "We score effort", "Seven rule checks plus an LLM review rank every open PR. Effort, not AI detection.",
     '<path d="M4 20V10"/><path d="M10 20V4"/><path d="M16 20v-8"/><path d="M22 20H2"/>'),
    ("STEP 3", "Reply with kindness", "Review the best first and send a polite, specific draft reply to the rest.",
     '<path d="M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>'),
]


def how_it_works():
    cols = st.columns(3)
    for col, (k, h, d, icon) in zip(cols, STEPS):
        col.markdown(
            f'<div class="step"><svg viewBox="0 0 24 24">{icon}</svg>'
            f'<div class="k">{k}</div><div class="h">{h}</div><div class="d">{d}</div></div>',
            unsafe_allow_html=True,
        )


def render_results(result):
    prs = [p for p in (result.get("prs") or []) if isinstance(p, dict)]
    if not prs:
        st.success(f'No open pull requests found for {result.get("repo", "this repo")}.')
        return
    prs.sort(key=lambda p: p.get("final_score") or 0, reverse=True)
    count = lambda t: sum(p.get("tier") == t for p in prs)
    s1, s2, s3, s4 = st.columns(4)
    stat(s1, len(prs), "Total PRs")
    stat(s2, count("Review first"), "Review first", "#34d399")
    stat(s3, count("Needs info"), "Needs info", "#fbbf24")
    stat(s4, count("Likely low-effort"), "Likely low-effort", "#f87171")
    st.caption(f'Repo: {result.get("repo", "")}')
    tiers = list(TIER_STYLE)
    if hasattr(st, "pills"):
        picked = st.pills("Filter by tier", tiers, selection_mode="multi", default=tiers)
    else:  # older Streamlit
        picked = st.multiselect("Filter by tier", tiers, default=tiers)
    shown = [p for p in prs if p.get("tier") not in tiers or p.get("tier") in (picked or [])]
    if not shown:
        st.info("No PRs match the selected tiers.")
    for pr in shown:
        pr_card(pr)


# ---------- header ----------
st.markdown(
    '<div class="hero"><h1>PR Lifeguard</h1>'
    "<p>Rescue maintainers from low-effort pull requests. We score <b>effort</b>, not AI usage, "
    "and draft a kind reply for every PR.</p></div>",
    unsafe_allow_html=True,
)

cache = read_cache()
with st.sidebar:
    demo = st.toggle(
        "Demo mode", value=bool(cache),
        help="Loads cached results instantly for repos triaged before, so the demo survives bad Wi-Fi "
             "and API rate limits. Repos not in the cache run normally.",
    )
    st.caption(f"{len(cache)} repo(s) cached" + ("" if live else " | live pipeline not available, using sample data"))
triage, load_history = get_backend()

tab_triage, tab_insights = st.tabs(["Triage", "Insights"])

with tab_triage:
    c1, c2 = st.columns([4, 1])
    repo_url = c1.text_input(
        "GitHub repo URL", value=DEMO_REPO,
        placeholder="https://github.com/owner/name", label_visibility="collapsed",
    )
    limit = c2.number_input("Max PRs", 1, 50, 10, label_visibility="collapsed")
    go = st.button("Triage open PRs", type="primary", width="stretch")

    if go:
        repo_url = repo_url.strip()
        if not REPO_RE.match(repo_url):
            st.error("Enter a GitHub repo URL like https://github.com/owner/name")
        else:
            bar = st.progress(0.0, text="Starting...")
            try:
                key = repo_key(repo_url)
                if demo and key in cache:
                    st.session_state["result"] = replay_cached(cache[key], int(limit), bar)
                else:
                    result = triage(
                        repo_url, int(limit), lambda msg, frac: bar.progress(min(max(frac, 0.0), 1.0), text=msg)
                    )
                    st.session_state["result"] = result
                    if live is not None and result.get("prs"):  # cache only real, non-empty results
                        save_to_cache(repo_url, result)
                        cache[key] = result
            except Exception as e:
                st.error(
                    f"Triage didn't complete: {e}. This is often a network problem or a GitHub rate limit. "
                    "Try again, or turn on Demo mode in the sidebar to use a cached repo."
                )
            finally:
                bar.empty()

    result = st.session_state.get("result")
    if not result:
        st.write("")
        how_it_works()
    else:
        try:
            render_results(result)
        except Exception as e:
            st.error(f"Could not display these results: {e}")

TIER_ORDER = list(TIER_STYLE)
TIER_COLORS = {t: c for t, (c, _) in TIER_STYLE.items()}


CHECK_LABELS = {
    "links_issue": "No linked issue",
    "has_description": "No description",
    "template_filled": "Template not filled",
    "touches_tests": "No tests",
    "size_ok": "Oversized diff",
    "account_age_ok": "New account",
    "returning_contributor": "First-time contributor",
}
ACCENT = "#38bdf8"
FONT = "Source Sans Pro, sans-serif"


def style_fig(fig, height=300):
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e6edf7", family=FONT, size=14), legend_title_text="", bargap=0.15,
    )
    fig.update_xaxes(gridcolor="rgba(148,163,184,.22)", title=None)
    fig.update_yaxes(gridcolor="rgba(148,163,184,.22)", title=None)
    return fig


def section(title):
    st.markdown(f'<h4 style="margin:1.4rem 0 .3rem">{title}</h4>', unsafe_allow_html=True)


with tab_insights:
    try:
        df = load_history()
        df["scored_at"] = pd.to_datetime(df["scored_at"])
        df["failed_checks"] = df["failed_checks"].fillna("").astype(str)
        df["final_score"] = pd.to_numeric(df["final_score"], errors="coerce")
        df = df.dropna(subset=["final_score"])
    except Exception as e:
        st.error(f"Could not load history ({e}). Showing nothing here; the Triage tab still works.")
        df = pd.DataFrame()

    try:
        if not df.empty:
            f1, f2 = st.columns(2)
            repos = f1.multiselect("Repos", sorted(df["repo"].unique()), default=sorted(df["repo"].unique()))
            tiers = f2.multiselect("Tiers", TIER_ORDER, default=TIER_ORDER)
            d = df[df["repo"].isin(repos) & df["tier"].isin(tiers)]

        if df.empty:
            st.info("No history yet. Run a triage and results will appear here.")
        elif d.empty:
            st.warning("No results match these filters.")
        else:
            low = (d["tier"] == "Likely low-effort").mean() * 100
            k1, k2, k3, k4 = st.columns(4)
            stat(k1, len(d), "PRs scored")
            stat(k2, d["run_id"].nunique(), "Runs")
            stat(k3, f'{d["final_score"].mean():.0f}', "Average effort score")
            stat(k4, f"{low:.0f}%", "Likely low-effort", "#f87171")

            left, right = st.columns(2)
            with left:
                section("Tier breakdown")
                counts = d["tier"].value_counts().reindex(TIER_ORDER).dropna().reset_index()
                counts.columns = ["tier", "count"]
                fig = px.pie(counts, names="tier", values="count", hole=0.62,
                             color="tier", color_discrete_map=TIER_COLORS)
                fig.update_traces(textinfo="value", sort=False)
                st.plotly_chart(style_fig(fig), use_container_width=True)
            with right:
                section("Effort score distribution")
                fig = px.histogram(d, x="final_score", nbins=10, color="tier",
                                   category_orders={"tier": TIER_ORDER}, color_discrete_map=TIER_COLORS)
                st.plotly_chart(style_fig(fig), use_container_width=True)

            section("Most common failed checks")
            fails = d["failed_checks"].str.split(",").explode()
            fails = fails[fails.notna() & (fails != "")].map(lambda c: CHECK_LABELS.get(c, c))
            fails = fails.value_counts().sort_values().reset_index()
            fails.columns = ["check", "count"]
            fig = px.bar(fails, x="count", y="check", orientation="h", color_discrete_sequence=[ACCENT])
            st.plotly_chart(style_fig(fig), use_container_width=True)

            section("20 most recent scored PRs")
            st.dataframe(
                d.sort_values("scored_at", ascending=False).head(20)[
                    ["scored_at", "repo", "pr_number", "title", "author", "final_score", "tier", "url"]
                ],
                width="stretch", hide_index=True,
                column_config={
                    "scored_at": st.column_config.DatetimeColumn("Scored", format="MMM D, HH:mm"),
                    "pr_number": st.column_config.NumberColumn("PR", format="#%d"),
                    "final_score": st.column_config.ProgressColumn("Effort", min_value=0, max_value=100, format="%d"),
                    "url": st.column_config.LinkColumn("Link", display_text="Open"),
                },
            )

        cur = st.session_state.get("result")
        st.caption(f'Storage backend: {cur.get("storage_backend", "unknown") if cur else "demo data (no storage used)"}')
    except Exception as e:
        st.error(f"Could not draw the insights charts: {e}")


# sidebar is rendered last so it reflects the result from this run
with st.sidebar:
    st.write("")
    cur = st.session_state.get("result")
    model = esc(cur.get("model_used", "-")) if cur else "-"
    store = esc(cur.get("storage_backend", "-")) if cur else "-"
    st.markdown(
        f'<div class="sbox">Model<div class="sval">{model}</div><br>'
        f'Storage<div class="sval">{store}</div></div>',
        unsafe_allow_html=True,
    )
    st.write("")
    st.markdown(
        '<div class="sbox"><b>How we score</b><br>We score effort, not AI use. Signals: linked issue, '
        "filled template, tests, sensible size, follows CONTRIBUTING.md. "
        "A human always makes the final call.</div>",
        unsafe_allow_html=True,
    )
