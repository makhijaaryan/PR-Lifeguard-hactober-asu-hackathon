"""PR Lifeguard - Streamlit frontend.

Backend switch: USE_FAKE_DATA below. False uses pipeline.triage / pipeline.load_history (the real
pipeline); True uses the fake data in contract.py. If the pipeline can't be imported, the app falls
back to fake data and says so under the top bar.

Demo mode: every successful real triage is saved to demo_cache.json (keyed by repo). With demo mode
on, a cached repo loads instantly (with a short fake progress animation); otherwise it runs normally.

Theme: light by default, with a dark mode toggle in the top bar. Streamlit's own widgets are
re-themed through its config (applied on the next rerun); our HTML uses the CSS tokens below.
"""
import html
import inspect
import json
import re
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit import config as st_config

import contract

USE_FAKE_DATA = False  # <- the one-line switch: True = sample data from contract.py, False = real pipeline

live, LIVE_ERROR = None, None
if not USE_FAKE_DATA:
    try:
        import pipeline as live
    except Exception as e:  # missing dependency or credentials: say so instead of hiding it
        live, LIVE_ERROR = None, str(e)

try:  # show the real thresholds on the home page; fall back to the contract's values
    from scorer import RULE_WEIGHT, TIER_NEEDS_INFO, TIER_REVIEW_FIRST
except Exception:
    RULE_WEIGHT, TIER_REVIEW_FIRST, TIER_NEEDS_INFO = 0.5, 70, 40

REPO_RE = re.compile(r"^(?:(?:https?://)?(?:www\.)?github\.com/)?[\w.-]+/[\w.-]+?(?:\.git)?/?$")
DEMO_REPO = "https://github.com/firstcontributions/first-contributions"
EXAMPLE_REPOS = {  # one-click examples under the input: Hacktoberfest-style traffic vs a mature project
    "first-contributions": "https://github.com/firstcontributions/first-contributions",
    "freeCodeCamp": "https://github.com/freeCodeCamp/freeCodeCamp",
    "home-assistant": "https://github.com/home-assistant/core",
}
CACHE_PATH = Path(__file__).resolve().parent / "demo_cache.json"


def get_backend():
    """Return (triage, history): the live pipeline if importable, else the fake contract data."""
    if live is None:
        return contract.fake_triage, contract.fake_history
    return live.triage, live.load_history


def repo_key(url):
    """'https://github.com/Owner/Name/' -> 'owner/name'"""
    return "/".join(url.strip().rstrip("/").split("/")[-2:]).lower()


def read_cache():
    try:
        return json.loads(CACHE_PATH.read_text())
    except Exception:  # missing or corrupt file: treat as empty
        return {}


def cache_covers(entry, limit):
    """True if a cached result can answer a request for `limit` PRs.

    The entry remembers the limit it was fetched with. If it came back full (as many PRs as the
    limit), the repo may have more, so a bigger request must hit the live backend.
    """
    n = len(entry.get("prs", []))
    fetched_with = entry.get("_limit", n)
    return limit <= n or n < fetched_with


def save_to_cache(url, result, limit):
    """Best-effort save; a cache failure must never break the demo."""
    try:
        cache = read_cache()
        cache[repo_key(url)] = {**result, "_limit": limit}
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


# ---------- theme ----------
PALETTES = {
    "light": {
        "bg": "#ffffff", "surface": "#ffffff", "subtle": "#f4f4f5", "border": "#e4e4e7",
        "fg": "#09090b", "muted": "#52525b", "primary": "#4f46e5", "primary-fg": "#ffffff",
        "primary-soft": "#eef2ff", "green": "#15803d", "green-bg": "#dcfce7", "amber": "#b45309",
        "amber-bg": "#fef3c7", "red": "#b91c1c", "red-bg": "#fee2e2",
        "shadow": "0 1px 2px rgba(16,24,40,.05), 0 8px 24px rgba(16,24,40,.06)",
        "grid": "rgba(9,9,11,.08)", "glow": "rgba(79,70,229,.10)", "glow2": "rgba(192,38,211,.07)",
        "gridline": "rgba(9,9,11,.05)", "accent2": "#c026d3", "primary-line": "rgba(79,70,229,.35)",
        "shadow-lg": "0 2px 4px rgba(16,24,40,.04), 0 18px 40px rgba(16,24,40,.10)",
        "cta1": "#4f46e5", "cta2": "#9333ea",
    },
    "dark": {
        "bg": "#09090b", "surface": "#111114", "subtle": "#18181b", "border": "#27272a",
        "fg": "#fafafa", "muted": "#a1a1aa", "primary": "#818cf8", "primary-fg": "#09090b",
        "primary-soft": "rgba(129,140,248,.14)", "green": "#4ade80", "green-bg": "rgba(74,222,128,.12)",
        "amber": "#fbbf24", "amber-bg": "rgba(251,191,36,.12)", "red": "#f87171",
        "red-bg": "rgba(248,113,113,.12)", "shadow": "0 1px 2px rgba(0,0,0,.4)",
        "grid": "rgba(250,250,250,.10)", "glow": "rgba(129,140,248,.16)", "glow2": "rgba(217,70,239,.10)",
        "gridline": "rgba(250,250,250,.05)", "accent2": "#e879f9", "primary-line": "rgba(129,140,248,.45)",
        "shadow-lg": "0 18px 40px rgba(0,0,0,.55)", "cta1": "#4338ca", "cta2": "#7e22ce",
    },
}


def streamlit_theme(mode):
    p = PALETTES[mode]
    return {
        "base": mode, "primaryColor": p["primary"], "backgroundColor": p["bg"],
        "secondaryBackgroundColor": p["subtle"], "textColor": p["fg"], "borderColor": p["border"],
        "baseRadius": "0.6rem", "font": "Inter, sans-serif",
    }


st.session_state.setdefault("dark", False)
MODE = "dark" if st.session_state["dark"] else "light"
P = PALETTES[MODE]

st.set_page_config(page_title="PR Lifeguard", layout="wide", initial_sidebar_state="collapsed")

TIERS = ["Review first", "Needs info", "Likely low-effort"]
TIER_TOKEN = {"Review first": "green", "Needs info": "amber", "Likely low-effort": "red"}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html {font-size: 17px;}
.stApp, .stApp p, .stApp label, .stApp input, .stApp button, .stApp textarea {font-family: Inter, sans-serif;}
#MainMenu, footer, header[data-testid="stHeader"] {visibility: hidden; height: 0;}
[data-testid="stHeaderActionElements"] {display: none !important;}  /* heading anchor-link icons */
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {display: none !important;}
.stApp {background:
  radial-gradient(900px 480px at 85% -10%, var(--glow), transparent 60%),
  radial-gradient(700px 420px at 0% 10%, var(--glow2), transparent 60%), var(--bg);}
[data-testid="stMain"], [data-testid="stAppViewContainer"] {background: transparent;}
.block-container {padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1180px;}
a {color: var(--primary);}

/* top bar */
.nav {display: flex; align-items: center; gap: .6rem; font-weight: 700; font-size: 1.15rem; color: var(--fg);}
.logo {width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center;
  background: var(--primary); color: var(--primary-fg);}
.logo svg {width: 20px; height: 20px;}
.nav .tag {font-weight: 500; font-size: .8rem; color: var(--muted); border: 1px solid var(--border);
  padding: .1rem .55rem; border-radius: 999px; margin-left: .3rem;}

/* icons */
.ico {fill: none; stroke: currentColor; stroke-width: 1.9; stroke-linecap: round; stroke-linejoin: round;}

/* hero */
.hero {position: relative; text-align: center; padding: 3.4rem 1rem 1.8rem; margin: .2rem 0 1rem;}
.hero::before {content: ""; position: absolute; inset: 0; z-index: 0; pointer-events: none;
  background-image: linear-gradient(var(--gridline) 1px, transparent 1px),
                    linear-gradient(90deg, var(--gridline) 1px, transparent 1px);
  background-size: 44px 44px;
  -webkit-mask-image: radial-gradient(ellipse 70% 80% at 50% 30%, #000 30%, transparent 75%);
          mask-image: radial-gradient(ellipse 70% 80% at 50% 30%, #000 30%, transparent 75%);}
.hero > * {position: relative; z-index: 1;}
.eyebrow {display: inline-flex; align-items: center; gap: .45rem; font-size: .82rem; font-weight: 600;
  color: var(--primary); background: var(--primary-soft); padding: .3rem .8rem; border-radius: 999px;}
.eyebrow .dot {width: 7px; height: 7px; border-radius: 50%; background: var(--primary);}
.hero h1 {font-size: 3.6rem; line-height: 1.08; letter-spacing: -.035em; font-weight: 800;
  margin: .9rem auto .7rem; max-width: 820px; color: var(--fg); padding: 0;}
.hero h1 span {background: linear-gradient(90deg, var(--primary), var(--accent2)); -webkit-background-clip: text;
  background-clip: text; color: transparent;}
.hero p.sub {font-size: 1.15rem; color: var(--muted); max-width: 680px; margin: 0 auto; line-height: 1.55;}

/* section headings */
.sec {text-align: center; margin: 3.4rem 0 1.4rem;}
.sec .k {font-size: .8rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--primary);}
.sec h2 {font-size: 2rem; letter-spacing: -.025em; font-weight: 800; margin: .3rem 0 .4rem; color: var(--fg); padding: 0;}
.sec p {color: var(--muted); font-size: 1.05rem; max-width: 640px; margin: 0 auto;}

/* generic grid + cards */
.grid {display: grid; gap: 1rem;}
.g3 {grid-template-columns: repeat(3, minmax(0, 1fr));}
.g4 {grid-template-columns: repeat(4, minmax(0, 1fr));}
@media (max-width: 900px) {.g3, .g4 {grid-template-columns: repeat(2, minmax(0, 1fr));}}
@media (max-width: 560px) {.g3, .g4 {grid-template-columns: 1fr;} .hero h1 {font-size: 2.2rem;}}
.box {background: var(--surface); border: 1px solid var(--border); border-radius: 18px;
  padding: 1.4rem 1.4rem; box-shadow: var(--shadow); color: var(--fg); transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;}
.box:hover {transform: translateY(-3px); box-shadow: var(--shadow-lg); border-color: var(--primary-line);}
.box .ib {width: 40px; height: 40px; border-radius: 10px; display: grid; place-items: center;
  background: var(--primary-soft); color: var(--primary); margin-bottom: .85rem;}
.box .ib svg {width: 21px; height: 21px;}
.box h3 {font-size: 1.08rem; font-weight: 700; margin: 0 0 .3rem; padding: 0; color: var(--fg);}
.box p {color: var(--muted); font-size: .97rem; line-height: 1.5; margin: 0;}
.box .num {font-size: .8rem; font-weight: 700; color: var(--muted); letter-spacing: .08em; margin-bottom: .4rem;}
.box.ai {background: linear-gradient(135deg, var(--primary-soft), var(--surface));}

/* tier explainer */
.tier {border-top: 4px solid var(--c);}
.tier .range {display: inline-block; font-weight: 700; font-size: .85rem; color: var(--c); background: var(--cbg);
  padding: .15rem .6rem; border-radius: 999px; margin-bottom: .6rem;}

/* stats */
.stat {background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 1.1rem 1.25rem;
  box-shadow: var(--shadow);}
.stat .l {display: flex; align-items: center; gap: .45rem; color: var(--muted); font-size: .9rem; font-weight: 600;}
.stat .l i {width: 9px; height: 9px; border-radius: 50%; background: var(--c);}
.stat .n {font-size: 2.3rem; font-weight: 800; letter-spacing: -.03em; color: var(--fg); line-height: 1.2;}

/* results */
.rhead {display: flex; justify-content: space-between; align-items: end; flex-wrap: wrap; gap: .5rem;
  margin: 2rem 0 .9rem;}
.rhead h2 {font-size: 1.6rem; font-weight: 800; letter-spacing: -.02em; margin: 0; padding: 0; color: var(--fg);}
.rhead .meta {color: var(--muted); font-size: .9rem;}
.rhead .meta b {color: var(--fg); font-weight: 600;}
.pr {display: flex; gap: 1.1rem; align-items: flex-start; background: var(--surface); border: 1px solid var(--border);
  border-left: 4px solid var(--c); border-radius: 14px; padding: 1.05rem 1.2rem; box-shadow: var(--shadow);
  margin-bottom: .35rem; transition: box-shadow .18s ease;}
.pr:hover {box-shadow: var(--shadow-lg);}
.pr .score {min-width: 64px; text-align: center; border-radius: 12px; background: var(--cbg); color: var(--c);
  padding: .45rem .3rem;}
.pr .score b {display: block; font-size: 1.7rem; font-weight: 800; line-height: 1.1;}
.pr .score span {font-size: .7rem; font-weight: 600; letter-spacing: .05em; text-transform: uppercase;}
.pr .t {font-weight: 700; font-size: 1.12rem; line-height: 1.35;}
.pr .t a {color: var(--fg); text-decoration: none;}
.pr .t a:hover {color: var(--primary); text-decoration: underline;}
.pr .m {color: var(--muted); font-size: .9rem; margin-top: .15rem;}
.pr .r {color: var(--fg); font-size: 1rem; margin-top: .45rem; line-height: 1.45;}
.pill {display: inline-block; padding: .12rem .6rem; border-radius: 999px; font-size: .78rem; font-weight: 700;
  margin-left: .45rem; vertical-align: middle; color: var(--c); background: var(--cbg);}
.chips {margin-top: .65rem; display: flex; flex-wrap: wrap; gap: .4rem;}
.chip {display: inline-flex; align-items: center; gap: .35rem; padding: .16rem .62rem; border-radius: 999px;
  font-size: .8rem; font-weight: 600; cursor: help; border: 1px solid var(--border); color: var(--muted);
  background: var(--subtle);}
.chip i {width: 7px; height: 7px; border-radius: 50%; background: var(--muted);}
.chip.ok {color: var(--green); background: var(--green-bg); border-color: transparent;}
.chip.ok i {background: var(--green);}
.chip.no {color: var(--red); background: var(--red-bg); border-color: transparent;}
.chip.no i {background: var(--red);}
.badge {display: inline-block; min-width: 3.1rem; text-align: center; padding: .08rem .5rem; border-radius: 6px;
  font-size: .72rem; font-weight: 700; letter-spacing: .05em; margin-right: .6rem;}
.badge.ok {color: var(--green); background: var(--green-bg);}
.badge.bad {color: var(--red); background: var(--red-bg);}
.badge.warn {color: var(--amber); background: var(--amber-bg);}

/* native widgets */
div[data-testid="stExpander"] {margin-bottom: 1rem;}
div[data-testid="stExpander"] details {border-radius: 12px;}
.stButton>button[kind="primary"] {height: 3rem; font-size: 1.05rem; font-weight: 700; border-radius: 10px;}
.stButton>button[kind="primary"] p {font-weight: 700;}
.stButton>button[kind="secondary"] {border-radius: 999px; font-size: .88rem; white-space: nowrap;
  min-height: 2.1rem; padding: .2rem .9rem;}
div[data-testid="stTabs"] button p {font-size: 1.02rem; font-weight: 600;}
/* search card + trust strip */
.st-key-search {background: var(--surface); border: 1px solid var(--border) !important; border-radius: 20px !important;
  box-shadow: var(--shadow-lg); padding: 1.1rem 1.2rem !important;}
.trust {display: flex; justify-content: center; flex-wrap: wrap; gap: .5rem 1.6rem; margin: 1.1rem 0 .4rem;
  color: var(--muted); font-size: .9rem; font-weight: 500;}
.trust span {display: inline-flex; align-items: center; gap: .45rem;}
.trust svg {width: 16px; height: 16px; color: var(--green);}
/* tabs as a segmented control */
div[data-testid="stTabs"] [role="tablist"] {gap: .25rem; background: var(--subtle); padding: .3rem; border-radius: 999px;
  width: fit-content; border: 1px solid var(--border);}
div[data-testid="stTabs"] button[role="tab"] {border-radius: 999px; padding: .35rem 1.1rem; height: auto;}
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {background: var(--surface); box-shadow: var(--shadow);}
div[data-testid="stTabs"] [data-baseweb="tab-highlight"], div[data-testid="stTabs"] [data-baseweb="tab-border"] {display: none;}
/* closing call to action */
.cta {text-align: center; margin: 4rem 0 0; padding: 3rem 1.5rem; border-radius: 24px; color: #fff;
  background: linear-gradient(135deg, var(--cta1), var(--cta2)); box-shadow: var(--shadow-lg);}
.cta h2 {color: #fff; font-size: 2.1rem; font-weight: 800; letter-spacing: -.025em; margin: 0 0 .5rem; padding: 0;}
.cta p {color: rgba(255,255,255,.85); font-size: 1.08rem; margin: 0 auto 1.4rem; max-width: 560px;}
.cta a {display: inline-block; background: #fff; color: #312e81 !important; font-weight: 700; text-decoration: none;
  padding: .75rem 1.5rem; border-radius: 999px;}
.cta a:hover {transform: translateY(-1px);}
.foot {text-align: center; color: var(--muted); font-size: .9rem; margin-top: 3.5rem; padding-top: 1.4rem;
  border-top: 1px solid var(--border);}
</style>
"""
tokens = ";".join(f"--{k}:{v}" for k, v in P.items())
st.markdown(f"<style>:root{{{tokens}}}</style>" + CSS, unsafe_allow_html=True)


def esc(s):
    return html.escape(str(s))


def icon(paths, cls="ico"):
    return f'<svg viewBox="0 0 24 24" class="{cls}">{paths}</svg>'


ICONS = {
    "buoy": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/><path d="m4.93 4.93 4.24 4.24"/>'
            '<path d="m14.83 9.17 4.24-4.24"/><path d="m14.83 14.83 4.24 4.24"/><path d="m9.17 14.83-4.24 4.24"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/>'
            '<path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
    "chart": '<path d="M4 20V10"/><path d="M10 20V4"/><path d="M16 20v-8"/><path d="M22 20H2"/>',
    "reply": '<path d="M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    "doc": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>'
           '<path d="M16 13H8"/><path d="M16 17H8"/>',
    "clip": '<rect x="8" y="2" width="8" height="4" rx="1"/>'
            '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="m9 14 2 2 4-4"/>',
    "flask": '<path d="M9 3h6"/><path d="M10 3v6L4.5 19a1.5 1.5 0 0 0 1.3 2h12.4a1.5 1.5 0 0 0 1.3-2L14 9V3"/>',
    "size": '<path d="M3 6h18"/><path d="M3 12h18"/><path d="M3 18h11"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    "repeat": '<path d="m17 2 4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14"/><path d="m7 22-4-4 4-4"/>'
              '<path d="M21 13v1a4 4 0 0 1-4 4H3"/>',
    "spark": '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 17v4"/><path d="M17 19h4"/>',
}


def tier_vars(tier):
    t = TIER_TOKEN.get(tier)
    return f"--c:var(--{t});--cbg:var(--{t}-bg)" if t else "--c:var(--muted);--cbg:var(--subtle)"


def section(kicker, title, sub=""):
    st.markdown(
        f'<div class="sec"><div class="k">{kicker}</div><h2>{title}</h2>' + (f"<p>{sub}</p>" if sub else "") + "</div>",
        unsafe_allow_html=True,
    )


def stats_row(items):
    """items: [(label, value, css color var)]"""
    cells = "".join(
        f'<div class="stat" style="--c:var(--{c})"><div class="l"><i></i>{esc(l)}</div><div class="n">{esc(v)}</div></div>'
        for l, v, c in items
    )
    st.markdown(f'<div class="grid g4">{cells}</div>', unsafe_allow_html=True)


def badge(passed):
    return f'<span class="badge {"ok" if passed else "bad"}">{"PASS" if passed else "FAIL"}</span>'


# (label when passed, label when failed). Contributor-history checks are context, not faults,
# so they fail in neutral grey instead of red.
CHIP_LABELS = {
    "links_issue": ("Linked issue", "No linked issue"),
    "has_description": ("Has description", "No description"),
    "template_filled": ("Template filled", "Template blank"),
    "touches_tests": ("Has tests", "No tests"),
    "size_ok": ("Focused size", "Unusual size"),
    "account_age_ok": ("Established account", "New account"),
    "returning_contributor": ("Returning contributor", "First-timer"),
}
NEUTRAL_CHECKS = {"account_age_ok", "returning_contributor"}


def chip(name, flag):
    flag = flag if isinstance(flag, dict) else {}
    passed, note = bool(flag.get("passed")), str(flag.get("note", ""))
    ok_label, bad_label = CHIP_LABELS.get(name, (str(name).replace("_", " "),) * 2)
    if passed:
        label, cls = ok_label, "ok"
        if name == "touches_tests" and note.lower().startswith("docs-only"):
            label = "Tests n/a (docs)"
    else:
        label, cls = bad_label, ("off" if name in NEUTRAL_CHECKS else "no")
        if name == "size_ok":
            label = "Very large diff" if note.lower().startswith("large") else "Very small diff"
    return f'<span class="chip {cls}" title="{esc(note)}"><i></i>{esc(label)}</span>'


def pr_card(pr):
    tier = pr.get("tier", "")
    chips = "".join(chip(n, f) for n, f in (pr.get("rule_flags") or {}).items())
    url = pr.get("url") or "#"
    st.markdown(
        f"""<div class="pr" style="{tier_vars(tier)}">
          <div class="score"><b>{esc(pr.get("final_score", "-"))}</b><span>effort</span></div>
          <div style="flex:1;min-width:0">
            <div class="t"><a href="{esc(url)}" target="_blank">{esc(pr.get("title", "(untitled)"))}</a>
              <span class="pill">{esc(tier)}</span></div>
            <div class="m">#{esc(pr.get("number", "?"))} opened by @{esc(pr.get("author", "unknown"))}</div>
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
        st.markdown("**Draft reply** (use the copy button)")
        st.code(pr.get("draft_reply") or "", language=None, wrap_lines=True)


def render_results(result):
    prs = [p for p in (result.get("prs") or []) if isinstance(p, dict)]
    repo = esc(result.get("repo", ""))
    if not prs:
        st.success(f"No open pull requests found for {repo or 'this repo'}.")
        return
    prs.sort(key=lambda p: p.get("final_score") or 0, reverse=True)
    st.markdown(
        f'<div class="rhead"><h2>Results for {repo}</h2><div class="meta">Model <b>{esc(result.get("model_used", "-"))}</b>'
        f' &nbsp;|&nbsp; Saved to <b>{esc(result.get("storage_backend", "-"))}</b></div></div>',
        unsafe_allow_html=True,
    )
    count = lambda t: sum(p.get("tier") == t for p in prs)
    stats_row([("Total PRs", len(prs), "primary"), ("Review first", count("Review first"), "green"),
               ("Needs info", count("Needs info"), "amber"), ("Likely low-effort", count("Likely low-effort"), "red")])
    st.write("")
    if hasattr(st, "pills"):
        picked = st.pills("Filter by tier", TIERS, selection_mode="multi", default=TIERS)
    else:  # older Streamlit
        picked = st.multiselect("Filter by tier", TIERS, default=TIERS)
    shown = [p for p in prs if p.get("tier") not in TIERS or p.get("tier") in (picked or [])]
    if not shown:
        st.info("No PRs match the selected tiers.")
    for pr in shown:
        pr_card(pr)


# ---------- home page sections ----------
def how_it_works():
    steps = [
        ("link", "01", "Paste a repo", "Any public GitHub repository, as a URL or owner/name. Or pick an example."),
        ("chart", "02", "We score effort", "Rule checks and an AI review rate every open PR from 0 to 100."),
        ("reply", "03", "Review and reply", "Start with the best PRs. Copy a kind, specific draft reply for the rest."),
    ]
    cells = "".join(
        f'<div class="box"><div class="ib">{icon(ICONS[i])}</div><div class="num">STEP {n}</div><h3>{h}</h3><p>{d}</p></div>'
        for i, n, h, d in steps
    )
    section("How it works", "From a noisy queue to a ranked list", "Three steps, about 30 seconds.")
    st.markdown(f'<div class="grid g3">{cells}</div>', unsafe_allow_html=True)


def what_we_check():
    checks = [
        ("link", "Linked issue", "Does the PR reference the issue it fixes?"),
        ("doc", "Clear description", "Is there an explanation of what changed and why?"),
        ("clip", "Template filled", "Did the author fill in the repo's PR template?"),
        ("flask", "Tests", "Are tests added or updated? Docs-only PRs are exempt."),
        ("size", "Sensible size", "Not a one-character tweak, not a 60-file sweep."),
        ("user", "Account age", "Context only: very new accounts are shown, never penalized alone."),
        ("repeat", "Returning contributor", "Context only: first-timers are welcome, and we say so."),
    ]
    cells = "".join(
        f'<div class="box"><div class="ib">{icon(ICONS[i])}</div><h3>{h}</h3><p>{d}</p></div>' for i, h, d in checks
    )
    cells += (
        f'<div class="box ai"><div class="ib">{icon(ICONS["spark"])}</div><h3>AI effort review</h3>'
        "<p>An open-weight model reads the description, diff and CONTRIBUTING.md, then drafts the reply.</p></div>"
    )
    section("What we check", "Transparent signals, not a black box",
            "Every score comes with the reasons behind it. Hover a chip on any PR to see the detail.")
    st.markdown(f'<div class="grid g4">{cells}</div>', unsafe_allow_html=True)


def score_tiers():
    rule_pct = round(RULE_WEIGHT * 100)
    tiers = [
        ("Review first", f"{TIER_REVIEW_FIRST}-100", "Complete, focused and explained. Look at these first."),
        ("Needs info", f"{TIER_NEEDS_INFO}-{TIER_REVIEW_FIRST - 1}",
         "Promising but missing something. The draft reply asks for it."),
        ("Likely low-effort", f"0-{TIER_NEEDS_INFO - 1}",
         "Little context or unrelated changes. A polite reply explains what is needed."),
    ]
    cells = "".join(
        f'<div class="box tier" style="{tier_vars(t)}"><span class="range">Score {r}</span><h3>{t}</h3><p>{d}</p></div>'
        for t, r, d in tiers
    )
    section("Score tiers", "One number, three clear buckets",
            f"Effort score = {rule_pct}% rule checks + {100 - rule_pct}% AI review.")
    st.markdown(f'<div class="grid g3">{cells}</div>', unsafe_allow_html=True)


FAQ = [
    ("Is this AI detection?",
     "No. We never ask whether AI wrote a PR. A careful AI-assisted PR scores high; a careless human one scores low."),
    ("Will it close or label PRs automatically?",
     "No. PR Lifeguard only ranks and drafts replies. A maintainer always makes the final call."),
    ("Can contributors game the score?",
     "Only by doing what maintainers want: explaining the change, linking an issue and adding tests."),
    ("Does the model see the code?",
     "Yes, an excerpt of the diff plus the repo's CONTRIBUTING.md. It is told not to claim anything it cannot see."),
    ("What if the model or Snowflake is down?",
     "Scoring falls back to a second model, then to rule checks only. Saving falls back to local storage. "
     "The results header shows what was used."),
]


def faq():
    section("FAQ", "Questions maintainers ask")
    _, mid, _ = st.columns([1, 6, 1])
    with mid:
        for q, a in FAQ:
            with st.expander(q):
                st.write(a)


# ---------- top bar ----------
cache = read_cache()
nav_l, nav_r = st.columns([3, 2], vertical_alignment="center")
nav_l.markdown(
    f'<div id="top" class="nav"><div class="logo">{icon(ICONS["buoy"])}</div>PR Lifeguard'
    '<span class="tag">Hacktoberfest 2026</span></div>',
    unsafe_allow_html=True,
)
with nav_r, st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center", gap="medium"):
    demo = st.toggle(
        "Demo mode", value=bool(cache), width="content",
        help=f"{len(cache)} repo(s) cached. Cached repos load instantly, so the demo survives bad Wi-Fi "
             "and API rate limits. Repos not in the cache run normally.",
    )
    st.toggle(
        "Dark mode", value=st.session_state["dark"], key="dark_toggle", width="content",
        on_change=lambda: st.session_state.update(dark=st.session_state["dark_toggle"]),
    )
if USE_FAKE_DATA:
    st.caption("Sample data mode (USE_FAKE_DATA = True)")
elif live is None:
    st.warning(f"Real pipeline failed to load, using sample data: {LIVE_ERROR}")
triage, load_history = get_backend()

tab_home, tab_insights = st.tabs(["Home", "Insights"])

with tab_home:
    st.markdown(
        '<div class="hero"><span class="eyebrow"><span class="dot"></span>Open-source AI for maintainers</span>'
        "<h1>Triage pull requests by <span>effort</span>, not guesswork</h1>"
        '<p class="sub">Paste a GitHub repo. PR Lifeguard ranks every open pull request, explains each score '
        "and drafts a kind reply, so you spend time on the PRs that deserve it.</p></div>",
        unsafe_allow_html=True,
    )

    st.session_state.setdefault("repo_url", DEMO_REPO)
    _, mid, _ = st.columns([0.6, 6, 0.6])
    with mid, st.container(border=True, key="search"):
        c1, c2 = st.columns([4, 1.1])
        repo_url = c1.text_input("GitHub repository", key="repo_url",
                                 placeholder="https://github.com/owner/name or owner/name")
        limit = c2.number_input("PRs to scan", 1, 50, 12, help="More PRs take longer: about 1-2 seconds each.")
        with st.container(horizontal=True, vertical_alignment="center", gap="small"):
            st.caption("Try an example:", width="content")
            for label, url in EXAMPLE_REPOS.items():
                st.button(label, key=f"ex_{label}", width="content",
                          on_click=lambda u=url: st.session_state.update(repo_url=u))
        go = st.button("Triage open PRs", type="primary", width="stretch")
    check = icon('<path d="M20 6 9 17l-5-5"/>')
    st.markdown(
        '<div class="trust">' + "".join(f"<span>{check}{t}</span>" for t in (
            "7 transparent checks", "Effort score from 0 to 100", "Open-weight AI", "A human makes the call")) + "</div>",
        unsafe_allow_html=True,
    )

    if go:
        repo_url = repo_url.strip()
        if not REPO_RE.match(repo_url):
            st.error("Enter a GitHub repo like https://github.com/owner/name or owner/name")
        else:
            bar = st.progress(0.0, text="Starting...")
            try:
                key = repo_key(repo_url)
                if demo and key in cache and cache_covers(cache[key], int(limit)):
                    st.session_state["result"] = replay_cached(cache[key], int(limit), bar)
                else:
                    result = triage(
                        repo_url, int(limit), lambda msg, frac: bar.progress(min(max(frac, 0.0), 1.0), text=msg)
                    )
                    st.session_state["result"] = result
                    if live is not None and result.get("prs"):  # cache only real, non-empty results
                        save_to_cache(repo_url, result, int(limit))
                        cache[key] = {**result, "_limit": int(limit)}
            except Exception as e:
                st.error(
                    f"Triage didn't complete: {e}. This is often a network problem or a GitHub rate limit. "
                    "Try again, or turn on Demo mode (top right) to use a cached repo."
                )
            finally:
                bar.empty()

    result = st.session_state.get("result")
    if result:
        try:
            render_results(result)
        except Exception as e:
            st.error(f"Could not display these results: {e}")

    how_it_works()
    what_we_check()
    score_tiers()
    faq()
    st.markdown(
        '<div class="cta"><h2>Ready to clear your PR queue?</h2>'
        "<p>Paste any public repo and get a ranked, explained list with kind replies in about 30 seconds.</p>"
        '<a href="#top">Triage a repo</a></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="foot">PR Lifeguard &middot; Built at Hacktoberfest Hack Day 2026 &middot; '
        "Effort, not AI detection. A human always makes the final call.</div>",
        unsafe_allow_html=True,
    )


# ---------- insights ----------
CHECK_LABELS = {
    "links_issue": "No linked issue",
    "has_description": "No description",
    "template_filled": "Template not filled",
    "touches_tests": "No tests",
    "size_ok": "Very small or very large diff",
    "account_age_ok": "New account",
    "returning_contributor": "First-time contributor",
}
TIER_COLORS = {t: P[TIER_TOKEN[t]] for t in TIERS}


def style_fig(fig, height=320):
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=P["fg"], family="Inter, sans-serif", size=14), legend_title_text="", bargap=0.2,
    )
    fig.update_xaxes(gridcolor=P["grid"], zerolinecolor=P["grid"], title=None)
    fig.update_yaxes(gridcolor=P["grid"], zerolinecolor=P["grid"], title=None)
    return fig


def show_chart(fig):
    """Full-width, themed Plotly chart. Streamlit renamed the sizing argument between versions."""
    if "width" in inspect.signature(st.plotly_chart).parameters:
        st.plotly_chart(style_fig(fig), width="stretch")
    else:
        st.plotly_chart(style_fig(fig), use_container_width=True)


def chart_title(title):
    st.markdown(f'<h3 style="font-size:1.15rem;font-weight:700;margin:1.2rem 0 .2rem">{title}</h3>',
                unsafe_allow_html=True)


with tab_insights:
    section("Insights", "Trends across every run", "Everything PR Lifeguard has scored, saved in storage.")
    try:
        df = load_history()
        df["scored_at"] = pd.to_datetime(df["scored_at"])
        df["failed_checks"] = df["failed_checks"].fillna("").astype(str)
        df["final_score"] = pd.to_numeric(df["final_score"], errors="coerce")
        df = df.dropna(subset=["final_score"])
    except Exception as e:
        st.error(f"Could not load history ({e}). Showing nothing here; the Home tab still works.")
        df = pd.DataFrame()

    try:
        if not df.empty:
            f1, f2 = st.columns(2)
            repos = f1.multiselect("Repos", sorted(df["repo"].unique()), default=sorted(df["repo"].unique()))
            tiers = f2.multiselect("Tiers", TIERS, default=TIERS)
            d = df[df["repo"].isin(repos) & df["tier"].isin(tiers)]

        if df.empty:
            st.info("No history yet. Run a triage and results will appear here.")
        elif d.empty:
            st.warning("No results match these filters.")
        else:
            low = (d["tier"] == "Likely low-effort").mean() * 100
            stats_row([("PRs scored", len(d), "primary"), ("Runs", d["run_id"].nunique(), "primary"),
                       ("Average effort score", f'{d["final_score"].mean():.0f}', "green"),
                       ("Likely low-effort", f"{low:.0f}%", "red")])

            left, right = st.columns(2)
            with left:
                chart_title("Tier breakdown")
                counts = d["tier"].value_counts().reindex(TIERS).dropna().reset_index()
                counts.columns = ["tier", "count"]
                fig = px.pie(counts, names="tier", values="count", hole=0.62,
                             color="tier", color_discrete_map=TIER_COLORS)
                fig.update_traces(textinfo="value", sort=False, marker=dict(line=dict(color=P["bg"], width=2)))
                show_chart(fig)
            with right:
                chart_title("Effort score distribution")
                fig = px.histogram(d, x="final_score", nbins=10, color="tier",
                                   category_orders={"tier": TIERS}, color_discrete_map=TIER_COLORS)
                show_chart(fig)

            chart_title("Most common failed checks")
            fails = d["failed_checks"].str.split(",").explode()
            fails = fails[fails.notna() & (fails != "")].map(lambda c: CHECK_LABELS.get(c, c))
            fails = fails.value_counts().sort_values().reset_index()
            fails.columns = ["check", "count"]
            fig = px.bar(fails, x="count", y="check", orientation="h", color_discrete_sequence=[P["primary"]])
            show_chart(fig)

            chart_title("20 most recent scored PRs")
            st.dataframe(
                d.sort_values("scored_at", ascending=False).head(20)[
                    ["scored_at", "repo", "pr_number", "title", "author", "final_score", "tier", "url"]
                ],
                width="stretch", hide_index=True,
                column_config={
                    "scored_at": st.column_config.DatetimeColumn("Scored", format="MMM D, HH:mm"),
                    "repo": "Repo", "title": "Title", "author": "Author", "tier": "Tier",
                    "pr_number": st.column_config.NumberColumn("PR", format="#%d"),
                    "final_score": st.column_config.ProgressColumn("Effort", min_value=0, max_value=100, format="%d"),
                    "url": st.column_config.LinkColumn("Link", display_text="Open"),
                },
            )

        cur = st.session_state.get("result")
        st.caption(f'Storage backend: {cur.get("storage_backend", "unknown") if cur else "shown after your first triage"}')
    except Exception as e:
        st.error(f"Could not draw the insights charts: {e}")


# Streamlit's own widgets read the theme from config at the start of a run. Switch it at the very
# end, after every widget has rendered, so the extra rerun keeps all widget values.
if st_config.get_option("theme.base") != MODE:
    for k, v in streamlit_theme(MODE).items():
        st_config.set_option(f"theme.{k}", v)
    st.rerun()
