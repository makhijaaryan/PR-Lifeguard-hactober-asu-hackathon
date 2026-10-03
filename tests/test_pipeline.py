"""Runs the real triage() and checks its output has exactly the shape contract.py promises.

Usage: python3 test_pipeline.py [repo] [limit]
"""
import logging
import sys

import pandas as pd

from contract import CHECK_NAMES, TIERS, fake_history, fake_triage
import pipeline
import storage
from github_client import GitHubError

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

repo_arg = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/home-assistant/core"
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 6


def shape(value):
    """Reduce a value to its keys/types so real and fake output can be compared structurally."""
    if isinstance(value, dict):
        return {k: shape(v) for k, v in value.items()}
    if isinstance(value, list):
        return [shape(value[0])] if value else []
    return type(value).__name__


def diff(a, b, path=""):
    """Yield differences between two shapes (a = real, b = fake). Empty lists are skipped."""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a.keys() | b.keys():
            if k not in a:
                yield f"{path}.{k}: missing from real output"
            elif k not in b:
                yield f"{path}.{k}: extra in real output"
            else:
                yield from diff(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list) and isinstance(b, list):
        if a and b:
            yield from diff(a[0], b[0], path + "[]")
    elif a != b:
        yield f"{path}: real is {a}, contract expects {b}"


messages = []
try:
    result = pipeline.triage(repo_arg, limit, lambda msg, frac: messages.append((msg, frac)))
except GitHubError as e:
    raise SystemExit(f"GitHub FAILED: {e}")

print("Progress:", " | ".join(f"{m} ({f:.0%})" for m, f in messages))
print(f"\nrepo={result['repo']} run_id={result['run_id']} model={result['model_used']} storage={result['storage_backend']}")

problems = []
fake = fake_triage("https://github.com/owner/name", 3)
problems += list(diff(shape(result), shape(fake)))                         # keys + types vs contract's own fake
if result["prs"]:
    for i, pr in enumerate(result["prs"]):
        if set(pr["rule_flags"]) != set(CHECK_NAMES):
            problems.append(f"prs[{i}].rule_flags keys {sorted(pr['rule_flags'])}")
        if pr["tier"] not in TIERS:
            problems.append(f"prs[{i}].tier {pr['tier']!r}")
        if not 0 <= pr["final_score"] <= 100 or isinstance(pr["final_score"], bool):
            problems.append(f"prs[{i}].final_score {pr['final_score']!r}")
        for name, flag in pr["rule_flags"].items():
            if set(flag) != {"passed", "note"} or not isinstance(flag["passed"], bool):
                problems.append(f"prs[{i}].rule_flags.{name} {flag!r}")
        if set(pr["description_matches_code"]) != {"value", "note"} or not isinstance(pr["description_matches_code"]["value"], bool):
            problems.append(f"prs[{i}].description_matches_code {pr['description_matches_code']!r}")
        if not all(isinstance(g, str) for g in pr["guideline_issues"]):
            problems.append(f"prs[{i}].guideline_issues not list[str]")
        if not pr["url"].startswith("https://github.com/"):
            problems.append(f"prs[{i}].url {pr['url']!r}")
    scores = [p["final_score"] for p in result["prs"]]
    if scores != sorted(scores, reverse=True):
        problems.append(f"prs not sorted by final_score desc: {scores}")
    if len(result["prs"]) > limit:
        problems.append(f"returned {len(result['prs'])} PRs, limit was {limit}")
if result["storage_backend"] not in ("Snowflake", "Local (fallback)"):
    problems.append(f"storage_backend {result['storage_backend']!r}")
if not messages or messages[-1][1] != 1.0 or [f for _, f in messages] != sorted(f for _, f in messages):
    problems.append("progress fractions should rise to 1.0")

hist = pipeline.load_history()
if list(hist.columns) != list(fake_history().columns):
    problems.append(f"history columns {list(hist.columns)}")
if not isinstance(hist, pd.DataFrame) or not (hist["run_id"] == result["run_id"]).any():
    problems.append("this run is missing from load_history()")

if problems:
    print("\nCONTRACT MISMATCHES:")
    for p in problems:
        print("  -", p)
    raise SystemExit(1)

print(f"\nContract shape OK ({len(result['prs'])} PRs, history has {len(hist)} rows). Top results:")
for pr in result["prs"][:5]:
    failed = [k for k, v in pr["rule_flags"].items() if not v["passed"]]
    print(f"  {pr['final_score']:3d} {pr['tier']:17s} #{pr['number']} {pr['title'][:45]}  failed={failed or 'none'}")
storage.delete_run(result["run_id"])
print("(test run removed from history)")
