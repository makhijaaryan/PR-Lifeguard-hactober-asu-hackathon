"""PR Lifeguard - Streamlit frontend.

Backend switch: set LIVE_BACKEND below to the module exposing triage() and history()
(the real pipeline). Demo mode always uses the fake data in contract.py.
"""
import html
import importlib
import re

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


def get_backend(demo):
    """Return (triage, history) for the chosen mode."""
    if demo or live is None:
        return contract.fake_triage, contract.fake_history
    return live.triage, live.history


@st.cache_data(show_spinner=False)
def demo_result():
    return contract.fake_triage(DEMO_REPO, 10)

st.set_page_config(page_title="PR Lifeguard", layout="wide", initial_sidebar_state="expanded")

TIER_STYLE = {
    "Review first": ("#34d399", "rgba(52,211,153,.14)"),
    "Needs info": ("#fbbf24", "rgba(251,191,36,.14)"),
    "Likely low-effort": ("#f87171", "rgba(248,113,113,.14)"),
}

CSS = """
<style>
#MainMenu, footer, header[data-testid="stHeader"] {visibility: hidden; height: 0;}
.block-container {padding-top: 2rem; max-width: 1100px;}
.hero {padding: 1.6rem 1.8rem; border-radius: 18px; margin-bottom: 1.2rem;
  background: radial-gradient(circle at 0% 0%, rgba(56,189,248,.22), transparent 55%),
              linear-gradient(135deg, #111a2e, #0b1220);
  border: 1px solid rgba(148,163,184,.18);}
.hero h1 {margin: 0; font-size: 2.2rem; letter-spacing: -.02em;}
.hero p {margin: .35rem 0 0; color: #94a3b8; font-size: 1.02rem;}
.stat {padding: 1rem 1.2rem; border-radius: 14px; background: #111a2e;
  border: 1px solid rgba(148,163,184,.16);}
.stat .n {font-size: 1.9rem; font-weight: 700; line-height: 1.1;}
.stat .l {color: #94a3b8; font-size: .8rem; text-transform: uppercase; letter-spacing: .08em;}
.card {padding: 1rem 1.2rem; border-radius: 14px; background: #111a2e; margin-bottom: .2rem;
  border: 1px solid rgba(148,163,184,.16); display: flex; gap: 1rem; align-items: center;}
.score {min-width: 66px; height: 66px; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; font-weight: 800; font-size: 1.5rem;}
.card .t {font-weight: 600; font-size: 1.02rem;}
.card .t a {color: inherit; text-decoration: none;}
.card .t a:hover {text-decoration: underline;}
.card .m {color: #94a3b8; font-size: .85rem; margin-top: .15rem;}
.card .r {color: #cbd5e1; font-size: .92rem; margin-top: .35rem;}
.pill {display: inline-block; padding: .1rem .6rem; border-radius: 999px; font-size: .72rem;
  font-weight: 600; margin-left: .5rem; vertical-align: middle;}
.chips {margin-top: .55rem; display: flex; flex-wrap: wrap; gap: .35rem;}
.chip {padding: .1rem .55rem; border-radius: 999px; font-size: .72rem; font-weight: 600; cursor: help;}
.chip.ok {color: #34d399; background: rgba(52,211,153,.14); border: 1px solid rgba(52,211,153,.35);}
.chip.off {color: #94a3b8; background: rgba(148,163,184,.10); border: 1px solid rgba(148,163,184,.25);}
.sbox {padding: .9rem 1rem; border-radius: 12px; background: #0b1220; border: 1px solid rgba(148,163,184,.18);
  font-size: .88rem; color: #cbd5e1; line-height: 1.5;}
.sbox b {color: #e6edf7;}
.sval {font-weight: 600; word-break: break-word;}
.badge {display: inline-block; min-width: 3.1rem; text-align: center; padding: .05rem .5rem;
  border-radius: 6px; font-size: .68rem; font-weight: 700; letter-spacing: .05em; margin-right: .6rem;}
.ok {color: #34d399; background: rgba(52,211,153,.14);}
.bad {color: #f87171; background: rgba(248,113,113,.14);}
.warn {color: #fbbf24; background: rgba(251,191,36,.14);}
div[data-testid="stExpander"] {border: none; margin-bottom: .9rem;}
div[data-testid="stExpander"] details {border: 1px solid rgba(148,163,184,.12); border-radius: 12px;}
.stButton>button[kind="primary"] {border-radius: 10px; font-weight: 600; height: 2.9rem;}
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
    cls = "ok" if flag["passed"] else "off"
    label = name.replace("_", " ")
    return f'<span class="chip {cls}" title="{esc(flag["note"])}">{esc(label)}</span>'


def pr_card(pr):
    color, bg = TIER_STYLE.get(pr["tier"], ("#94a3b8", "rgba(148,163,184,.14)"))
    chips = "".join(chip(n, f) for n, f in pr["rule_flags"].items())
    st.markdown(
        f"""<div class="card">
          <div class="score" style="color:{color};background:{bg};border:2px solid {color}">{pr["final_score"]}</div>
          <div style="flex:1">
            <div class="t"><a href="{esc(pr["url"])}" target="_blank">{esc(pr["title"])}</a>
              <span class="pill" style="color:{color};background:{bg}">{esc(pr["tier"])}</span></div>
            <div class="m">#{pr["number"]} by @{esc(pr["author"])}</div>
            <div class="r">{esc(pr["reason"])}</div>
            <div class="chips">{chips}</div>
          </div></div>""",
        unsafe_allow_html=True,
    )
    with st.expander("Details and draft reply"):
        st.markdown("**Guideline issues**")
        if pr["guideline_issues"]:
            for issue in pr["guideline_issues"]:
                st.markdown(f'<span class="badge warn">NOTE</span>{esc(issue)}', unsafe_allow_html=True)
        else:
            st.markdown('<span class="badge ok">PASS</span>No guideline issues found.', unsafe_allow_html=True)
        m = pr["description_matches_code"]
        st.markdown("**Description matches code**")
        st.markdown(badge(m["value"]) + esc(m["note"]), unsafe_allow_html=True)
        st.markdown("**Draft reply**")
        st.code(pr["draft_reply"], language=None, wrap_lines=True)


# ---------- header ----------
st.markdown(
    '<div class="hero"><h1>PR Lifeguard</h1>'
    "<p>Rescue maintainers from low-effort pull requests. We score <b>effort</b>, not AI usage, "
    "and draft a kind reply for every PR.</p></div>",
    unsafe_allow_html=True,
)

t1, t2 = st.columns([3, 2])
demo = t1.toggle(
    "Demo mode (no network, sample data)", value=live is None, disabled=live is None,
    help="Uses built-in sample data so the demo never depends on GitHub or Snowflake.",
)
t2.markdown(
    f'<div style="text-align:right;color:#94a3b8;font-size:.85rem;padding-top:.4rem">'
    f'Backend: {"demo data" if demo or live is None else "live pipeline"}</div>',
    unsafe_allow_html=True,
)
if live is None:
    st.caption("Live pipeline not available yet; running on demo data.")
triage, history = get_backend(demo)

# drop results from the other mode so demo and live data never mix
if st.session_state.get("mode") != demo:
    st.session_state["mode"] = demo
    st.session_state.pop("result", None)

tab_triage, tab_dash = st.tabs(["Triage a repo", "Dashboard"])

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
                st.session_state["result"] = triage(
                    repo_url, int(limit), lambda msg, frac: bar.progress(min(max(frac, 0.0), 1.0), text=msg)
                )
            except Exception as e:
                st.error(f"Triage failed: {e}")
            finally:
                bar.empty()
    elif demo and "result" not in st.session_state:
        with st.spinner("Loading sample results..."):
            st.session_state["result"] = demo_result()

    result = st.session_state.get("result")
    if not result:
        st.info("Paste a repo URL and click Triage to rank its open pull requests by effort.")
    elif not result["prs"]:
        st.success(f'No open pull requests found for {result["repo"]}.')
    else:
        prs = sorted(result["prs"], key=lambda p: p["final_score"], reverse=True)
        count = lambda t: sum(p["tier"] == t for p in prs)
        s1, s2, s3, s4 = st.columns(4)
        stat(s1, len(prs), "Total PRs")
        stat(s2, count("Review first"), "Review first", "#34d399")
        stat(s3, count("Needs info"), "Needs info", "#fbbf24")
        stat(s4, count("Likely low-effort"), "Likely low-effort", "#f87171")
        st.caption(f'Repo: {result["repo"]}')
        picked = st.pills("Filter by tier", list(TIER_STYLE), selection_mode="multi", default=list(TIER_STYLE))
        shown = [p for p in prs if p["tier"] in (picked or [])]
        if not shown:
            st.info("No PRs match the selected tiers.")
        for pr in shown:
            pr_card(pr)

TIER_ORDER = list(TIER_STYLE)
TIER_COLORS = {t: c for t, (c, _) in TIER_STYLE.items()}


def style_fig(fig, height=300):
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1"), legend_title_text="", bargap=0.15,
    )
    fig.update_xaxes(gridcolor="rgba(148,163,184,.12)", title=None)
    fig.update_yaxes(gridcolor="rgba(148,163,184,.12)", title=None)
    return fig


def section(title):
    st.markdown(f'<h4 style="margin:1.4rem 0 .3rem">{title}</h4>', unsafe_allow_html=True)


with tab_dash:
    try:
        df = history()
        df["scored_at"] = pd.to_datetime(df["scored_at"])
    except Exception as e:
        st.error(f"Could not load history: {e}")
        df = pd.DataFrame()

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

        left, right = st.columns(2)
        with left:
            section("Most common failed checks")
            fails = d["failed_checks"].str.split(",").explode()
            fails = fails[fails.notna() & (fails != "")].value_counts().sort_values().reset_index()
            fails.columns = ["check", "count"]
            fig = px.bar(fails, x="count", y="check", orientation="h", color_discrete_sequence=["#38bdf8"])
            st.plotly_chart(style_fig(fig), use_container_width=True)
        with right:
            section("Average score by repo")
            by_repo = d.groupby("repo")["final_score"].mean().round(1).sort_values().reset_index()
            fig = px.bar(by_repo, x="final_score", y="repo", orientation="h", color_discrete_sequence=["#38bdf8"])
            st.plotly_chart(style_fig(fig), use_container_width=True)

        section("All scored PRs")
        st.dataframe(
            d[["scored_at", "repo", "pr_number", "title", "author", "final_score", "tier", "url"]]
            .sort_values("scored_at", ascending=False),
            width="stretch", hide_index=True,
            column_config={
                "scored_at": st.column_config.DatetimeColumn("Scored", format="MMM D, HH:mm"),
                "pr_number": st.column_config.NumberColumn("PR", format="#%d"),
                "final_score": st.column_config.ProgressColumn("Effort", min_value=0, max_value=100, format="%d"),
                "url": st.column_config.LinkColumn("Link", display_text="Open"),
            },
        )


# sidebar is rendered last so it reflects the result from this run
with st.sidebar:
    st.markdown("### PR Lifeguard")
    cur = st.session_state.get("result")
    model = esc(cur["model_used"]) if cur else "-"
    store = esc(cur["storage_backend"]) if cur else "-"
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
