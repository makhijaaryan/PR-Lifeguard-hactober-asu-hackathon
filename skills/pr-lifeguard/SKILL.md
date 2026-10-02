---
name: pr-lifeguard
description: Triage a GitHub repository's open pull requests by effort, not by whether AI was used. Scores each PR 0-100 from seven transparent rule checks plus an open-weight LLM review, sorts them into Review first / Needs info / Likely low-effort, and drafts a kind reply for each. Use when a maintainer asks which PRs to review first, wants to spot low-effort or drive-by PRs (for example during Hacktoberfest), or needs polite replies asking contributors for missing context.
license: MIT
---

# PR Lifeguard

Ranks a repo's open pull requests by how much care went into them, explains every score, and drafts a reply the maintainer can post. It is a **triage aid**: it never closes, labels or comments on a PR by itself.

## When to use

- "Which of these open PRs should I look at first?"
- "Flag the low-effort PRs in owner/repo."
- "Draft polite replies asking contributors for a linked issue, description or tests."

Do not use it to decide whether a PR was written with AI. It deliberately does not judge that.

## Inputs

| Input | Type | Notes |
|---|---|---|
| `repo_url` | string | `owner/repo` or `https://github.com/owner/repo` |
| `limit` | int | Max open PRs to score, newest first (5–25 is a good range) |
| `progress_callback` | optional `callable(message: str, fraction: float)` | Called as work progresses, e.g. `"Scoring 4/12…", 0.5` |

Configuration lives in `.streamlit/secrets.toml` (see `.streamlit/secrets.toml.example`):

- `[llm]` `base_url`, `api_key`, `model`, `fallback_model`: any OpenAI-compatible endpoint.
- `[github]` `token`: GitHub token (raises the rate limit from 60 to 5,000 requests/hour).
- `[snowflake]`: where results are stored. Falls back to local SQLite if unreachable.

## How to run

From the repository root, with the Python dependencies installed (`pip install -r requirements.txt`):

```python
from pipeline import triage, load_history

result = triage("firstcontributions/first-contributions", limit=12,
                progress_callback=lambda msg, frac: print(f"{frac:4.0%} {msg}"))

for pr in result["prs"]:                       # already sorted, highest score first
    print(pr["final_score"], pr["tier"], f"#{pr['number']}", pr["title"])
    print("  ", pr["reason"])

history = load_history()                       # pandas DataFrame of every saved run
```

Or use the apps: `./dev.sh` starts the web UI at http://localhost:3000 (FastAPI on :8000), and `.venv/bin/streamlit run app.py` starts the Streamlit backup.

`triage()` raises `github_client.GitHubError` with a user-friendly message for a bad URL, a missing repo, a bad token or a rate limit. Model and storage failures never raise.

## Output

`triage()` returns a dict (the exact shape is defined in `contract.py`):

```text
repo             "owner/name"
run_id           short id for this run
model_used       e.g. "openai/gpt-oss-120b", or "none (rule checks only)"
storage_backend  "Snowflake" or "Local (fallback)"
prs[]            sorted by final_score, highest first:
  number, title, author, url
  final_score            0-100, higher = more effort
  tier                   "Review first" (70+) | "Needs info" (40-69) | "Likely low-effort" (<40)
  reason                 one neutral sentence
  rule_flags             {check_name: {"passed": bool, "note": str}} for the 7 checks
  guideline_issues       CONTRIBUTING.md rules the PR seems to miss
  description_matches_code  {"value": bool, "note": str}
  draft_reply            polite reply for the maintainer to review and post
```

## How scoring works

1. **Fetch** open PRs with their diffs, plus the repo's `CONTRIBUTING.md` and PR template.
2. **Rule checks** (`checks.py`), weighted to 100: linked issue (20), has description (20), template filled (10), tests touched (15), focused size (15), account age (5), returning contributor (15). Account age and first-time contributor are context, never shown as faults.
3. **LLM review** (`scorer.py`): reads the description, a diff excerpt and the contributing guide, and returns an effort score, reason, guideline issues, a description-vs-code check and a draft reply.
4. **Final score** = 50% rules + 50% LLM.

## Limits

- **A human makes the final call.** Scores rank a queue; they are not verdicts. Always read a PR before acting on it, and review a draft reply before posting it.
- It judges visible effort and fit with the project's rules, never whether AI was used. A careful AI-assisted PR scores high.
- The model sees only the first ~1,500 characters of the diff, so `description_matches_code` is a best effort on large PRs.
- Free LLM tiers are rate limited. On a 429 it switches to the fallback model; if both fail, the PR is scored from rule checks alone and the reason says so.
- Tutorial repos (like first-contributions) expect tiny PRs, so their scores read differently than a mature project's. Compare PRs within one repo, not across repos.
