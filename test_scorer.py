"""Offline parser/fallback checks, then scores 3 real PRs (pass a repo, or --offline to skip)."""
import sys
import time

import scorer
from checks import run_checks

PR = {
    "number": 1, "title": "Fix cache bug", "body": "", "author": "newbie", "author_association": "NONE",
    "links_issue": False, "filenames": ["src/cache.py"], "additions": 5, "deletions": 1, "changed_files": 1,
    "author_account_created_at": None, "created_at": "2026-10-01T00:00:00Z",
}
RULES = run_checks(PR, "")
GOOD_JSON = ('{"effort_score": 72, "reason": "Clear fix.", "guideline_issues": [], '
             '"description_matches_code": {"value": true, "note": "ok"}, "draft_reply": "Thanks!"}')

# --- parser ---
assert scorer._parse_json("```json\n" + GOOD_JSON + "\n```")["effort_score"] == 72
assert scorer._parse_json("<think>hmm {x}</think>Here you go: " + GOOD_JSON + " Done.")["reason"] == "Clear fix."
assert scorer._parse_json(GOOD_JSON.replace("72", "250"))["effort_score"] == 100          # clamped
for bad in ("not json", "{}", '{"effort_score": "high"}'):
    try:
        scorer._parse_json(bad)
        raise SystemExit(f"parser accepted: {bad}")
    except scorer.ParseError:
        pass
assert [scorer.tier_for(s) for s in (100, 70, 69, 40, 39, 0)] == ["Review first"] * 2 + ["Needs info"] * 2 + ["Likely low-effort"] * 2

# --- fallback paths (monkeypatched model) ---
replies = iter(["garbage", GOOD_JSON])
scorer.ask_llm = lambda s, u: (next(replies), "fake-model")
r = scorer.score_pr(PR, RULES)
assert r["used_llm"] and r["effort_score"] == 72, r          # first reply bad, retry succeeded
assert r["final_score"] == round(0.5 * RULES["rule_score"] + 0.5 * 72)

scorer.ask_llm = lambda s, u: ("still garbage", "fake-model")
r = scorer.score_pr(PR, RULES)
assert not r["used_llm"] and r["effort_score"] == RULES["rule_score"], r   # fell back to rules
print("offline OK. Fallback reply:", r["draft_reply"], "\n")

def boom(s, u):
    raise scorer.LLMError("down")
scorer.ask_llm = boom
assert not scorer.score_pr(PR, RULES)["used_llm"]

if "--offline" not in sys.argv:
    import importlib
    importlib.reload(scorer)  # restore the real ask_llm
    from github_client import GitHubError, get_contributing_guide, get_open_prs, get_pr_template, parse_repo
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    try:
        owner, repo = parse_repo(args[0] if args else "home-assistant/core")
        prs = get_open_prs(owner, repo, limit=3)
        guide, template = get_contributing_guide(owner, repo), get_pr_template(owner, repo)
    except GitHubError as e:
        raise SystemExit(f"GitHub FAILED: {e}")
    start = time.time()
    results = scorer.score_all(prs, guide, template, lambda d, t, pr: print(f"  scored {d}/{t}: #{pr['number']}"))
    print(f"\nScored {len(prs)} PRs in {time.time() - start:.1f}s")
    for pr, r in zip(prs, results):
        print(f"\n#{pr['number']} {pr['title'][:60]}")
        print(f"  final={r['final_score']} ({r['tier']})  rule={r['rule_score']} effort={r['effort_score']}  llm={r['used_llm']} model={r['model_used']}")
        print(f"  reason: {r['reason']}")
        print(f"  guideline_issues: {r['guideline_issues']}")
        print(f"  matches_code: {r['description_matches_code']}")
        print(f"  reply: {r['draft_reply']}")
        if not r["used_llm"]:
            print(f"  LLM ERROR: {r['llm_error']}")
