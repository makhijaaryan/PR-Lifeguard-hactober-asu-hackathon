"""The real engine: the same triage() / load_history() the UI gets from contract.py's fakes."""
import logging
import uuid
from collections import Counter

import storage
from github_client import get_contributing_guide, get_open_prs, get_pr_template, parse_repo
from scorer import score_all

log = logging.getLogger("pr_lifeguard.pipeline")

NO_MODEL = "none (rule checks only)"


def triage(repo_url, limit=12, progress_callback=None):
    """Fetch open PRs for `repo_url`, score each for effort, save, and return the contract dict.

    Raises github_client.GitHubError (with a user-friendly message) for bad URLs, 404s,
    bad tokens and rate limits. Model or storage failures never raise: scoring falls back to
    the rule checks and saving falls back to local SQLite.
    """
    def tick(message, fraction):
        if progress_callback:
            progress_callback(message, fraction)

    owner, repo = parse_repo(repo_url)
    full_name = f"{owner}/{repo}"

    tick("Fetching PRs…", 0.05)
    prs = get_open_prs(owner, repo, limit=limit)
    tick(f"Fetched {len(prs)} open PRs", 0.2)

    tick("Reading CONTRIBUTING.md…", 0.22)
    guide = get_contributing_guide(owner, repo)
    tick("Reading PR template…", 0.26)
    template = get_pr_template(owner, repo)

    total = len(prs)
    if total:
        tick(f"Scoring 0/{total}…", 0.3)

    def on_scored(done, total, pr):
        tick(f"Scoring {done}/{total}…", 0.3 + 0.6 * done / total)

    scored = score_all(prs, guide, template, on_scored) if prs else []

    out = []
    for pr, s in zip(prs, scored):
        out.append({
            "number": int(pr["number"]),
            "title": pr["title"],
            "author": pr["author"],
            "url": pr["html_url"],
            "final_score": int(s["final_score"]),
            "tier": s["tier"],
            "reason": s["reason"],
            "rule_flags": s["rule_flags"],
            "guideline_issues": list(s["guideline_issues"]),
            "description_matches_code": s["description_matches_code"],
            "draft_reply": s["draft_reply"],
        })
    out.sort(key=lambda p: p["final_score"], reverse=True)

    models = Counter(s["model_used"] for s in scored if s["used_llm"])
    model_used = models.most_common(1)[0][0] if models else NO_MODEL

    run_id = uuid.uuid4().hex[:12]
    tick("Saving results…", 0.93)
    if out:
        try:
            storage.save_results(run_id, full_name, out, model_used)
        except Exception as e:  # saving must never lose the results the user is waiting for
            log.warning("Could not save results: %s", e)

    tick("Done.", 1.0)
    return {
        "repo": full_name,
        "run_id": run_id,
        "model_used": model_used,
        "storage_backend": storage.storage_backend(),
        "prs": out,
    }


def load_history():
    """DataFrame of past results, same columns as contract.fake_history()."""
    return storage.load_history()
