"""GitHub REST helpers: open PRs with the data the rule checks need, plus repo guidelines."""
import re
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from engine.config import load_config  # reads .streamlit/secrets.toml

API = "https://api.github.com"
TIMEOUT = 20
MAX_WORKERS = 8  # GitHub calls are I/O bound and cheap; the LLM stays at 4 in scorer.py
GUIDE_LIMIT = 3000
FILES_LIMIT = 100  # filenames fetched per PR (one page)
PATCH_LIMIT = 1500  # chars of diff kept per PR for the model

_ISSUE_KEYWORDS = (
    r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?|ref(?:s|erences?)?|related\s+to|part\s+of|see)"
    r"\s*:?\s+(?:[\w.-]+/[\w.-]+)?#\d+"
)
_ISSUE_URL = r"github\.com/[\w.-]+/[\w.-]+/issues/\d+"
_LINKS_ISSUE_RE = re.compile(f"{_ISSUE_KEYWORDS}|{_ISSUE_URL}", re.IGNORECASE)


class GitHubError(RuntimeError):
    """Raised with a human-readable message the UI can show directly."""


def parse_repo(url):
    """Accept 'owner/repo' or a GitHub URL; return (owner, repo)."""
    text = (url or "").strip()
    text = re.sub(r"^(?:https?://)?(?:www\.)?github\.com/", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^git@github\.com:", "", text)
    parts = [p for p in text.split("/") if p]
    if len(parts) < 2:
        raise GitHubError(f"Could not read a repo from '{url}'. Use 'owner/repo' or https://github.com/owner/repo")
    owner, repo = parts[0], parts[1]
    repo = re.sub(r"\.git$", "", repo)
    if not re.fullmatch(r"[\w.-]+", owner) or not re.fullmatch(r"[\w.-]+", repo):
        raise GitHubError(f"'{owner}/{repo}' doesn't look like a valid GitHub repo")
    return owner, repo


def _headers(accept="application/vnd.github+json"):
    headers = {"Accept": accept, "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "pr-lifeguard"}
    token = load_config()["github"].get("token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get(path, params=None, accept="application/vnd.github+json", allow_404=False):
    """GET a GitHub API path. Returns the Response (or None for an allowed 404)."""
    try:
        resp = requests.get(API + path, headers=_headers(accept), params=params, timeout=TIMEOUT)
    except requests.Timeout as e:
        raise GitHubError(f"GitHub timed out after {TIMEOUT}s. Try again.") from e
    except requests.RequestException as e:
        raise GitHubError(f"Could not reach GitHub: {e}") from e

    if resp.status_code == 200:
        return resp
    if resp.status_code == 404:
        if allow_404:
            return None
        raise GitHubError("Repo not found. Check the URL (private repos need a token with access).")
    if resp.status_code == 401:
        raise GitHubError("GitHub rejected the token (401). Check github.token in .streamlit/secrets.toml.")
    if resp.status_code in (403, 429):
        if resp.headers.get("X-RateLimit-Remaining") == "0":
            reset = resp.headers.get("X-RateLimit-Reset")
            mins = max(1, int((int(reset) - time.time()) / 60) + 1) if reset and reset.isdigit() else None
            when = f" Resets in about {mins} min." if mins else ""
            raise GitHubError(f"GitHub rate limit reached.{when} Use a token, or try again later.")
        raise GitHubError(f"GitHub refused the request ({resp.status_code}): {resp.json().get('message', '') if resp.content else ''}".strip())
    raise GitHubError(f"GitHub returned HTTP {resp.status_code}: {resp.text[:200]}")


def _links_issue(body):
    return bool(_LINKS_ISSUE_RE.search(body or ""))


def _patch_excerpt(files, limit=PATCH_LIMIT):
    """First `limit` chars of the unified diff, file by file, so the model can see real changes."""
    parts, used = [], 0
    for f in files:
        patch = f.get("patch")
        if not patch:
            continue
        chunk = f"--- {f['filename']}\n{patch}\n"
        parts.append(chunk[: max(0, limit - used)])
        used += len(chunk)
        if used >= limit:
            break
    return "".join(parts)


def _account_created_at(login, cache):
    """Account creation time for a user (None if unavailable). `cache` is shared per call."""
    if not login:
        return None
    if login not in cache:
        try:
            resp = _get(f"/users/{login}", allow_404=True)
            cache[login] = resp.json().get("created_at") if resp else None
        except GitHubError:
            cache[login] = None
    return cache[login]


def _build_pr(owner, repo, summary, user_cache):
    number = summary["number"]
    detail = _get(f"/repos/{owner}/{repo}/pulls/{number}").json()
    files = _get(f"/repos/{owner}/{repo}/pulls/{number}/files", params={"per_page": FILES_LIMIT}).json()
    login = (detail.get("user") or {}).get("login")
    body = detail.get("body") or ""
    return {
        "number": number,
        "title": detail.get("title") or "",
        "body": body,
        "author": login or "ghost",
        "author_account_created_at": _account_created_at(login, user_cache),
        "author_association": detail.get("author_association") or "NONE",
        "created_at": detail.get("created_at"),
        "html_url": detail.get("html_url") or summary.get("html_url"),
        "additions": detail.get("additions", 0),
        "deletions": detail.get("deletions", 0),
        "changed_files": detail.get("changed_files", len(files)),
        "filenames": [f["filename"] for f in files],
        "patch_excerpt": _patch_excerpt(files),
        "links_issue": _links_issue(f"{detail.get('title') or ''}\n{body}"),
    }


def get_open_prs(owner, repo, limit=15):
    """Return up to `limit` open PRs (newest first) as dicts with everything the checks need.

    Costs 1 list call + 2 calls per PR (detail, files) + 1 per unique author, run 4 at a time.
    """
    limit = max(1, min(int(limit or 15), 100))
    listing = _get(
        f"/repos/{owner}/{repo}/pulls",
        params={"state": "open", "sort": "created", "direction": "desc", "per_page": limit},
    ).json()
    user_cache = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        return list(pool.map(lambda s: _build_pr(owner, repo, s, user_cache), listing[:limit]))


def _find_file(owner, repo, dirs, matches):
    """Return the text of the first file in `dirs` ('' = repo root) whose lowercase name satisfies `matches`."""
    for d in dirs:
        resp = _get(f"/repos/{owner}/{repo}/contents/{d}".rstrip("/"), allow_404=True)
        if resp is None:
            continue
        entries = resp.json()
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if entry.get("type") == "file" and matches(entry["name"].lower()):
                raw = _get(entry["url"].replace(API, ""), accept="application/vnd.github.raw", allow_404=True)
                if raw is not None:
                    return raw.text
    return ""


def get_contributing_guide(owner, repo):
    """CONTRIBUTING file from root, .github/ or docs/, trimmed to 3000 chars ('' if missing)."""
    text = _find_file(owner, repo, ["", ".github", "docs"], lambda n: n.startswith("contributing"))
    return text[:GUIDE_LIMIT]


def get_pr_template(owner, repo):
    """Pull request template ('' if missing). Checks .github/, root and docs/ (any case)."""
    return _find_file(owner, repo, [".github", "", "docs"], lambda n: n.startswith("pull_request_template"))
