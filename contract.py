"""PR Lifeguard backend contract + fake data for building the UI in parallel.

The real engine will expose the same signatures as `triage`. Until it lands,
the UI can call `fake_triage` / `fake_history` and swap later.
"""
import random
import time
import uuid
from datetime import datetime, timedelta

import pandas as pd

TIERS = ("Review first", "Needs info", "Likely low-effort")
CHECK_NAMES = (
    "links_issue",
    "has_description",
    "template_filled",
    "touches_tests",
    "size_ok",
    "account_age_ok",
    "returning_contributor",
)


def triage(repo_url, limit, progress_callback=None):
    """Fetch open PRs for `repo_url`, score each for effort, and save results.

    Args:
        repo_url: GitHub repo URL, e.g. "https://github.com/owner/name".
        limit: max number of open PRs to score.
        progress_callback: optional callable(message: str, fraction: float 0-1),
            called repeatedly while work is in progress.

    Returns a dict:
        {
          "repo": str,                  # "owner/name"
          "run_id": str,
          "model_used": str,            # e.g. "llama3.1-70b" or the fallback
          "storage_backend": str,       # "Snowflake" or "Local (fallback)"
          "prs": [                      # sorted by final_score, highest first
            {
              "number": int,
              "title": str,
              "author": str,
              "url": str,
              "final_score": int,       # 0-100, higher = more effort
              "tier": str,              # "Review first" | "Needs info" | "Likely low-effort"
              "reason": str,            # one line
              "rule_flags": {           # keys = CHECK_NAMES
                  "<check_name>": {"passed": bool, "note": str},
              },
              "guideline_issues": [str],
              "description_matches_code": {"value": bool, "note": str},
              "draft_reply": str,       # polite reply for the maintainer to post
            },
          ],
        }

    Check names: links_issue, has_description, template_filled, touches_tests,
    size_ok, account_age_ok, returning_contributor.
    """
    raise NotImplementedError("Real engine not wired up yet; use fake_triage.")


# (title, author, score, tier, reason, failed checks, guideline issues, matches, match note, reply)
_FAKE_PRS = [
    ("Fix race condition in cache invalidation", "dana-k", 92, 0,
     "Links an issue, adds a regression test, and the description explains the root cause.",
     [], [], True, "Diff changes cache.py locking exactly as described.",
     "Thanks so much for this, Dana! The root-cause write-up and the regression test make this easy to review. We'll take a look shortly."),
    ("Add retry with backoff to HTTP client", "mlopez", 85, 0,
     "Well-scoped change with tests and a clear motivation tied to issue #212.",
     ["returning_contributor"], [], True, "Retry logic matches the description.",
     "Thank you for the contribution! This is clearly explained and tested. A maintainer will review soon."),
    ("Migrate config parsing to pydantic v2", "sam-oduya", 78, 0,
     "Large but coherent refactor with migration notes; tests updated.",
     ["size_ok"], [], True, "Changes match the described migration.",
     "Thanks Sam! This is a big change, so it may take us a bit longer to review. Would you be open to splitting it if we find it hard to land in one go?"),
    ("Update README", "newuser9921", 31, 2,
     "One-line edit with no description and no linked issue.",
     ["links_issue", "has_description", "template_filled", "account_age_ok"],
     ["Did not follow CONTRIBUTING.md PR template"], True, "Tiny README tweak, nothing described.",
     "Thanks for taking the time to contribute! Could you add a short description of what this changes and why? That helps us review quickly."),
    ("Improve performance", "bot-helper-77", 14, 2,
     "Vague title, empty description, and the diff reformats files without functional changes.",
     ["links_issue", "has_description", "template_filled", "touches_tests", "account_age_ok"],
     ["Unrelated whitespace changes", "No tests"], False, "Description is empty; diff only reformats code.",
     "Thank you for the PR! We couldn't find a description or a functional change here. If you intended a specific improvement, please tell us what it is and add a benchmark or test."),
    ("Fix typo in docs", "kiran-p", 55, 1,
     "Legit docs fix, but no description and not linked to an issue.",
     ["links_issue", "has_description"], [], True, "Typo fix matches title.",
     "Thanks Kiran, appreciate the fix! Could you add a quick sentence describing the change so we can merge it faster?"),
    ("Add dark mode toggle", "jwu", 63, 1,
     "Feature looks reasonable, but there are no tests and the template is partly filled.",
     ["touches_tests", "template_filled", "links_issue"], ["No tests for new UI logic"], True,
     "Toggle implemented as described.",
     "Thanks for the contribution, JWu! Could you add a test for the toggle state and link the related feature request if there is one?"),
    ("Refactor everything for clarity", "xX_coder_Xx", 9, 2,
     "Sweeping, unfocused changes across 60 files with no explanation or tests.",
     ["has_description", "template_filled", "touches_tests", "size_ok", "account_age_ok", "links_issue"],
     ["Too large", "Not discussed in an issue first"], False, "Description doesn't explain the broad changes.",
     "Thank you for your interest in the project! This PR is too broad for us to review as a single change. Could you open an issue to discuss the goals and break it into smaller pieces?"),
    ("Handle None in parse_headers", "prya-r", 81, 0,
     "Small, targeted bug fix with a failing test reproduced from issue #340.",
     [], [], True, "Null check matches the described bug.",
     "Great catch, Priya, and thanks for including the test. We'll get this reviewed soon."),
    ("Add CI badge and update contributing docs", "tobias-w", 47, 1,
     "Reasonable docs update but description is thin and it mixes two unrelated changes.",
     ["links_issue", "template_filled"], ["Mixes unrelated changes"], True,
     "Badge and docs both present.",
     "Thanks Tobias! Could you split the badge and the contributing-docs change into two PRs, or explain how they relate? Happy to review either way."),
]


def _check_flags(failed):
    notes_fail = {
        "links_issue": "No linked issue found.",
        "has_description": "Description is empty or very short.",
        "template_filled": "PR template left blank or mostly unchanged.",
        "touches_tests": "No test files changed.",
        "size_ok": "Diff is unusually large for one PR.",
        "account_age_ok": "Account is under 30 days old.",
        "returning_contributor": "First-time contributor to this repo.",
    }
    notes_pass = {
        "links_issue": "Links an issue.",
        "has_description": "Clear description provided.",
        "template_filled": "Template filled out.",
        "touches_tests": "Tests added or updated.",
        "size_ok": "Reasonably sized diff.",
        "account_age_ok": "Established account.",
        "returning_contributor": "Has prior merged PRs here.",
    }
    return {
        name: {
            "passed": name not in failed,
            "note": notes_fail[name] if name in failed else notes_pass[name],
        }
        for name in CHECK_NAMES
    }


def fake_triage(repo_url, limit, progress_callback=None):
    """Return realistic fake data in exactly the shape `triage` returns."""
    repo = "/".join(repo_url.rstrip("/").split("/")[-2:]) or "owner/name"

    def tick(msg, frac):
        if progress_callback:
            progress_callback(msg, frac)
        time.sleep(0.4)

    tick("Fetching open pull requests...", 0.1)
    tick("Running rule checks...", 0.35)
    tick("Asking the model to review PRs...", 0.65)
    tick("Saving results...", 0.9)

    prs = []
    for i, (title, author, score, tier, reason, failed, issues, matches, match_note, reply) in enumerate(_FAKE_PRS):
        number = 100 + i * 7
        prs.append({
            "number": number,
            "title": title,
            "author": author,
            "url": f"https://github.com/{repo}/pull/{number}",
            "final_score": score,
            "tier": TIERS[tier],
            "reason": reason,
            "rule_flags": _check_flags(failed),
            "guideline_issues": list(issues),
            "description_matches_code": {"value": matches, "note": match_note},
            "draft_reply": reply,
        })
    prs.sort(key=lambda p: p["final_score"], reverse=True)
    prs = prs[:limit] if limit else prs

    tick("Done.", 1.0)
    return {
        "repo": repo,
        "run_id": uuid.uuid4().hex[:12],
        "model_used": "llama3.1-70b",
        "storage_backend": "Local (fallback)",
        "prs": prs,
    }


def fake_history():
    """Return a DataFrame of 40 fake past results."""
    rng = random.Random(42)
    repos = ["pallets/flask", "psf/requests", "tiangolo/fastapi", "encode/httpx"]
    now = datetime.now()
    run_ids = [uuid.UUID(int=rng.getrandbits(128)).hex[:12] for _ in range(5)]
    rows = []
    for i in range(40):
        title, author, score, tier, reason, failed, *_ = rng.choice(_FAKE_PRS)
        score = max(0, min(100, score + rng.randint(-6, 6)))
        repo = rng.choice(repos)
        number = rng.randint(100, 900)
        rows.append({
            "run_id": run_ids[i % len(run_ids)],
            "scored_at": now - timedelta(hours=rng.randint(1, 240)),
            "repo": repo,
            "pr_number": number,
            "title": title,
            "author": author,
            "url": f"https://github.com/{repo}/pull/{number}",
            "final_score": score,
            "tier": TIERS[0] if score >= 70 else TIERS[1] if score >= 40 else TIERS[2],
            "reason": reason,
            "failed_checks": ",".join(failed),
        })
    return pd.DataFrame(rows).sort_values("scored_at", ascending=False).reset_index(drop=True)
