import sys
import time

from github_client import GitHubError, get_contributing_guide, get_open_prs, get_pr_template, parse_repo

target = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/home-assistant/core"

try:
    owner, repo = parse_repo(target)
    print(f"Repo: {owner}/{repo}")

    start = time.time()
    prs = get_open_prs(owner, repo, limit=5)
    print(f"Fetched {len(prs)} open PRs in {time.time() - start:.1f}s\n")
    for pr in prs:
        print(f"#{pr['number']} {pr['title'][:60]}")
        print(f"    by {pr['author']} ({pr['author_association']}), account created {pr['author_account_created_at']}")
        print(f"    +{pr['additions']}/-{pr['deletions']} in {pr['changed_files']} files, "
              f"body {len(pr['body'])} chars, links_issue={pr['links_issue']}")
        print(f"    files: {', '.join(pr['filenames'][:3])}")

    guide = get_contributing_guide(owner, repo)
    template = get_pr_template(owner, repo)
    print(f"\nContributing guide: {len(guide)} chars" + (f" -> {guide[:80]!r}..." if guide else " (none)"))
    print(f"PR template: {len(template)} chars" + (f" -> {template[:80]!r}..." if template else " (none)"))

    # URL parsing checks
    for s in ("pallets/flask", "https://github.com/pallets/flask/", "github.com/pallets/flask.git"):
        assert parse_repo(s) == ("pallets", "flask"), s
    print("\nparse_repo OK")
except GitHubError as e:
    print("FAILED:", e)
    raise SystemExit(1)
