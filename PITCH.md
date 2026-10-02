# PR Lifeguard - Pitch (3 minutes)

Theme: open-source AI | Sponsor: Snowflake

## One-liner
PR Lifeguard rescues open-source maintainers from low-effort pull requests. It scores each PR for **effort** (not AI detection), ranks the queue, and drafts a kind reply.

## 1. The problem (30s)
- Maintainers are drowning in low-effort, often AI-generated pull requests.
- Hacktoberfest 2026 stopped counting PRs because of this.
- Today the maintainer must open every PR just to find out it is a one-line README edit with no description.
- Banning AI is the wrong fix. Plenty of good PRs use AI. The real signal is **effort**: did the author explain, link an issue, add tests, keep the change focused?

## 2. The solution (30s)
- Paste a GitHub repo. We fetch the open PRs, their diffs, the repo's CONTRIBUTING.md and PR template.
- Seven transparent rule checks: linked issue, description, template filled, tests touched, sensible size, account age, returning contributor.
- An open-weight LLM (gpt-oss-120b, falling back to Qwen) reads the description, the diff excerpt and the contributing guide: guideline fit, whether the description matches the code, and a polite draft reply.
- Score = 50% rule checks + 50% LLM effort score, so every number has visible reasons.
- Results are saved (Snowflake, or local SQLite if Snowflake is unreachable) and feed the Insights tab.

## 3. Live demo (90s)
Keep Demo mode on so nothing depends on conference wifi (cached repos replay instantly).
1. Click the **first-contributions** example and triage. This is exactly the Hacktoberfest traffic: "my first commit", "HI HI". Point at the stat tiles: zero to review first, several likely low-effort.
2. Open a card: red chips show what is missing (no linked issue), grey chips are context, not faults (first-timer). Open "Details and draft reply": the reply is kind and asks for the specific missing thing. Use the copy button.
3. Point at a grounded finding, e.g. a "add my name" PR that rewrites 900 lines of Contributors.md. The model saw the diff; it is not guessing.
4. Click **home-assistant** (a mature project) and triage: mostly "Review first". Same tool, very different queue. That is the point: it rewards effort, not who you are.
5. Insights tab: tier donut, the most common failed checks (what contributors keep forgetting), recent PRs.
6. (Optional) Demo mode off, paste any repo, run it live (~15-30s for 12 PRs).

## 4. Why it fits the theme and the sponsor (20s)
- Open-source AI used to protect open source, not flood it. Only open-weight models.
- Snowflake is the system of record: every scored PR lands in a `PR_SCORES` table that powers the trends view across runs and repos.
- Scores come from explainable checks plus an LLM, so maintainers can trust them and contributors can learn from them.

## 5. Close (10s)
"Maintainers keep their time. Good contributors get a faster review. Low-effort PRs get a kind, clear path to improve. PR Lifeguard."

## Likely questions
- **Isn't this just AI detection?** No. We never ask whether AI wrote it. A careful AI-assisted PR scores high; a careless human one scores low.
- **Can contributors game it?** Yes, by doing the things we check for: explaining the change, linking an issue and adding tests. That is the behavior maintainers want.
- **Will it auto-close PRs?** No. It only drafts replies. The maintainer stays in control.
- **What if the model is down or rate limited?** It switches to the second model, and if both fail it scores from the rule checks alone and says so in the reason. Storage falls back to SQLite. The sidebar shows which model and storage were used.
- **Does the model see the code?** Yes, a diff excerpt (first ~1500 chars). It is told never to claim anything it cannot see in the excerpt.
- **What next?** A GitHub Action that comments on new PRs automatically, per-repo rule tuning, and Snowflake Cortex once it is enabled on our account.

## Demo checklist
- [ ] `.venv/bin/streamlit run app.py` starts cleanly
- [ ] Demo mode toggle is on, and first-contributions + home-assistant are cached (sidebar shows "N repo(s) cached")
- [ ] Browser zoomed so the cards and Insights are readable from the back of the room
- [ ] Insights tab opened once so charts are warm
- [ ] Backup: screen recording of the full flow
