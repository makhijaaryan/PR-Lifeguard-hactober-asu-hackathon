"""Offline checks on hand-made PRs, then a live run on real PRs (pass a repo, or skip with --offline)."""
import sys

from checks import WEIGHTS, run_checks
from contract import CHECK_NAMES

assert sum(WEIGHTS.values()) == 100 and tuple(WEIGHTS) == CHECK_NAMES

TEMPLATE = "## What\n<!-- describe -->\n\n## Checklist\n- [ ] Tests added\n- [ ] Docs updated\n"

GOOD = {
    "body": "Fixes #12. The cache lock was released before the write finished, so I moved the release "
            "into a finally block and added a regression test.",
    "links_issue": True, "filenames": ["src/cache.py", "tests/test_cache.py"], "additions": 40, "deletions": 5,
    "author_account_created_at": "2018-01-01T00:00:00Z", "created_at": "2026-10-01T00:00:00Z",
    "author_association": "CONTRIBUTOR",
}
LOW = {
    "body": "", "links_issue": False, "filenames": ["README.md"], "additions": 1, "deletions": 1,
    "author_account_created_at": "2026-09-25T00:00:00Z", "created_at": "2026-10-01T00:00:00Z",
    "author_association": "FIRST_TIME_CONTRIBUTOR",
}
HUGE = {**GOOD, "additions": 1500, "deletions": 200, "filenames": ["src/a.py"]}
BLANK_TEMPLATE = {**GOOD, "body": TEMPLATE}
FILLED_TEMPLATE = {**GOOD, "body": TEMPLATE.replace("- [ ] Tests added", "- [x] Tests added") + "\nAdds retry logic to the client."}


def passed(pr, template=""):
    return {k: v["passed"] for k, v in run_checks(pr, template)["rule_flags"].items()}


good = run_checks(GOOD, "")
assert good["rule_score"] == 100, good
assert tuple(good["rule_flags"]) == CHECK_NAMES

low = run_checks(LOW, "")
assert low["rule_score"] == 25 + 0, low  # only template_filled(10) + touches_tests(docs-only, 15) pass
assert not any(low["rule_flags"][k]["passed"] for k in ("links_issue", "has_description", "size_ok", "account_age_ok", "returning_contributor"))

assert not passed(HUGE)["size_ok"]
assert not passed(BLANK_TEMPLATE, TEMPLATE)["template_filled"]
assert passed(FILLED_TEMPLATE, TEMPLATE)["template_filled"]
assert passed(BLANK_TEMPLATE, "")["template_filled"]  # no template -> passes
assert passed({**GOOD, "author_account_created_at": None})["account_age_ok"]  # unknown -> not penalised
assert not passed({**GOOD, "filenames": ["src/a.py"]})["touches_tests"]
print("offline checks OK\n")
for label, pr in (("good", GOOD), ("low-effort", LOW)):
    r = run_checks(pr, "")
    print(f"{label}: rule_score={r['rule_score']}")
    for name, flag in r["rule_flags"].items():
        print(f"  {'PASS' if flag['passed'] else 'FAIL'} {name}: {flag['note']}")

if "--offline" not in sys.argv:
    from github_client import GitHubError, get_open_prs, get_pr_template, parse_repo
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    try:
        owner, repo = parse_repo(args[0] if args else "home-assistant/core")
        template = get_pr_template(owner, repo)
        print(f"\nLive: {owner}/{repo}")
        for pr in get_open_prs(owner, repo, limit=5):
            r = run_checks(pr, template)
            failed = [k for k, v in r["rule_flags"].items() if not v["passed"]]
            print(f"  #{pr['number']} score={r['rule_score']:3d} failed={failed or 'none'}  {pr['title'][:45]}")
    except GitHubError as e:
        print("Live run FAILED:", e)
        raise SystemExit(1)
