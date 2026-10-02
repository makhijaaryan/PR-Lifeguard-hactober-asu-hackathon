import type { CheckName, Flag, Tier } from "@/lib/api";

export const TIERS: Tier[] = ["Review first", "Needs info", "Likely low-effort"];

export const TIER_COLOR: Record<Tier, string> = {
  "Review first": "var(--tier-review)",
  "Needs info": "var(--tier-info)",
  "Likely low-effort": "var(--tier-low)",
};

export const CHECK_ORDER: CheckName[] = [
  "links_issue",
  "has_description",
  "template_filled",
  "touches_tests",
  "size_ok",
  "account_age_ok",
  "returning_contributor",
];

/** [label when passed, label when failed] */
const CHECK_LABELS: Record<CheckName, [string, string]> = {
  links_issue: ["Linked issue", "No linked issue"],
  has_description: ["Has description", "No description"],
  template_filled: ["Template filled", "Template blank"],
  touches_tests: ["Has tests", "No tests"],
  size_ok: ["Focused size", "Unusual size"],
  account_age_ok: ["Established account", "New account"],
  returning_contributor: ["Returning contributor", "First-timer"],
};

/** Contributor-history checks are context about the person, never a fault. */
export const NEUTRAL_CHECKS = new Set<CheckName>(["account_age_ok", "returning_contributor"]);

export function checkLabel(name: CheckName, flag: Flag): string {
  const [ok, bad] = CHECK_LABELS[name] ?? [name, name];
  const note = flag.note.toLowerCase();
  if (flag.passed) return name === "touches_tests" && note.startsWith("docs-only") ? "Tests n/a (docs)" : ok;
  if (name === "size_ok") return note.startsWith("large") ? "Very large diff" : "Very small diff";
  return bad;
}

/** Friendly names for the "most common failed checks" chart. */
export const FAILED_CHECK_LABEL: Record<CheckName, string> = {
  links_issue: "No linked issue",
  has_description: "No description",
  template_filled: "Template not filled",
  touches_tests: "No tests",
  size_ok: "Very small or large diff",
  account_age_ok: "New account",
  returning_contributor: "First-time contributor",
};
