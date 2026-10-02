"""Rule-based effort signals for a PR. Pure functions, no network.

Input is a PR dict from github_client.get_open_prs. These are signals about effort,
not accusations, so every note is neutral and describes what was (or wasn't) found.
"""
import re
from datetime import datetime, timezone

# Points each passed check adds to rule_score. Keep the total at 100.
WEIGHTS = {
    "links_issue": 20,
    "has_description": 20,
    "template_filled": 10,
    "touches_tests": 15,
    "size_ok": 15,
    "account_age_ok": 5,
    "returning_contributor": 15,
}

MIN_DESCRIPTION_WORDS = 8
MIN_TEMPLATE_ADDED_CHARS = 40   # text added beyond the template's own wording
TICKED_BOX_CHARS = 10           # a ticked checkbox counts as this much "filled in" text
TINY_LINES = 3                  # total changed lines at or below this is "tiny"
TINY_DOCS_LINES = 6             # same, when only docs/README files changed
HUGE_LINES = 1000
MIN_ACCOUNT_AGE_DAYS = 30
RETURNING_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR", "CONTRIBUTOR"}

_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_TEST_RE = re.compile(r"(^|/)(tests?|__tests__|spec|specs)/|(^|/)test_[^/]*$|[_.-](test|tests|spec)\.[^/]*$", re.I)
_DOC_RE = re.compile(r"\.(md|rst|txt|adoc)$|(^|/)(docs?|documentation)/|(^|/)(readme|changelog|license)[^/]*$", re.I)


def _result(passed, note):
    return {"passed": bool(passed), "note": note}


def _strip_comments(text):
    return _COMMENT_RE.sub("", text or "")


def _norm_lines(text):
    """Non-empty stripped lines with comments removed and ticked boxes normalised to unticked."""
    lines = []
    for line in _strip_comments(text).splitlines():
        line = re.sub(r"\[[xX]\]", "[ ]", line.strip())
        if line:
            lines.append(line)
    return lines


def _is_docs(path):
    return bool(_DOC_RE.search(path))


def _check_links_issue(pr):
    if pr.get("links_issue"):
        return _result(True, "Links an issue.")
    return _result(False, "No linked issue found.")


def _check_has_description(pr):
    words = len(re.findall(r"\w+", _strip_comments(pr.get("body"))))
    if words >= MIN_DESCRIPTION_WORDS:
        return _result(True, "Description provided.")
    if words == 0:
        return _result(False, "Description is empty.")
    return _result(False, "Description is very short.")


def _check_template_filled(pr, pr_template):
    if not (pr_template or "").strip():
        return _result(True, "Repo has no PR template.")
    body = pr.get("body") or ""
    template_lines = set(_norm_lines(pr_template))
    added = sum(len(l) for l in _norm_lines(body) if l not in template_lines)
    added += TICKED_BOX_CHARS * len(re.findall(r"\[[xX]\]", _strip_comments(body)))
    if added >= MIN_TEMPLATE_ADDED_CHARS:
        return _result(True, "Template filled out.")
    return _result(False, "PR template left mostly blank.")


def _check_touches_tests(pr):
    files = pr.get("filenames") or []
    if any(_TEST_RE.search(f) for f in files):
        return _result(True, "Tests added or updated.")
    if files and all(_is_docs(f) for f in files):
        return _result(True, "Docs-only change, tests not expected.")
    return _result(False, "No test files changed.")


def _check_size_ok(pr):
    lines = (pr.get("additions") or 0) + (pr.get("deletions") or 0)
    files = pr.get("filenames") or []
    docs_only = bool(files) and all(_is_docs(f) for f in files)
    if lines > HUGE_LINES:
        return _result(False, f"Large diff ({lines} lines), which can be hard to review in one PR.")
    if lines <= TINY_LINES or (docs_only and lines <= TINY_DOCS_LINES):
        return _result(False, f"Very small change ({lines} lines), such as a typo or README tweak.")
    return _result(True, f"Reasonably sized diff ({lines} lines).")


def _parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _check_account_age(pr):
    created = _parse_time(pr.get("author_account_created_at"))
    if created is None:
        return _result(True, "Account age unavailable.")
    reference = _parse_time(pr.get("created_at")) or datetime.now(timezone.utc)
    days = (reference - created).days
    if days < MIN_ACCOUNT_AGE_DAYS:
        return _result(False, f"Account was under {MIN_ACCOUNT_AGE_DAYS} days old when the PR was opened.")
    return _result(True, "Established account.")


def _check_returning(pr):
    association = (pr.get("author_association") or "NONE").upper()
    if association in RETURNING_ASSOCIATIONS:
        return _result(True, "Has prior contributions to this repo.")
    return _result(False, "No earlier merged contributions found for this repo.")


def run_checks(pr, pr_template=""):
    """Return {"rule_flags": {name: {"passed", "note"}}, "rule_score": 0-100}."""
    rule_flags = {
        "links_issue": _check_links_issue(pr),
        "has_description": _check_has_description(pr),
        "template_filled": _check_template_filled(pr, pr_template),
        "touches_tests": _check_touches_tests(pr),
        "size_ok": _check_size_ok(pr),
        "account_age_ok": _check_account_age(pr),
        "returning_contributor": _check_returning(pr),
    }
    rule_score = sum(WEIGHTS[name] for name, flag in rule_flags.items() if flag["passed"])
    return {"rule_flags": rule_flags, "rule_score": rule_score}
