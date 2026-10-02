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
- Paste a GitHub repo URL. We fetch the open PRs.
- Seven transparent rule checks: linked issue, description, template filled, tests touched, sensible size, account age, returning contributor.
- A Snowflake Cortex LLM reviews guideline fit and whether the description matches the code.
- Every PR gets a 0-100 effort score, a tier (Review first / Needs info / Likely low-effort), a one-line reason and a polite draft reply.
- Results are saved in Snowflake and feed a dashboard.

## 3. Live demo (90s)
Run in demo mode so nothing depends on conference wifi.
1. Open the app. The ranked sample queue is already loaded. Point at the stat tiles: how many to review first, how many to push back on.
2. Top card: "Fix race condition in cache invalidation", score 92. Reason: links an issue, adds a regression test. Open details, show the PASS checks.
3. Bottom card: "Refactor everything for clarity", score 9. Open details: five FAIL checks, "description doesn't match code". Show the draft reply: polite, specific, asks for an issue and smaller pieces. Use the copy button on the code block.
4. Switch to the Dashboard tab. Show the tier donut, the most common failed checks (the thing contributors keep forgetting) and the per-repo averages. Say: this is the data from Snowflake, so a project can see trends across runs.
5. (If live backend is ready) toggle Demo mode off, paste a real repo and run it.

## 4. Why it fits the theme and the sponsor (20s)
- Open-source AI used to protect open source, not flood it.
- Built on Snowflake: Cortex for the model calls and Snowflake tables for storage and the dashboard.
- Scores come from explainable checks plus an LLM, so every score has a visible reason. Maintainers can trust it and contributors can learn from it.

## 5. Close (10s)
"Maintainers keep their time. Good contributors get a faster review. Low-effort PRs get a kind, clear path to improve. PR Lifeguard."

## Likely questions
- **Isn't this just AI detection?** No. We never ask whether AI wrote it. A careful AI-assisted PR scores high; a careless human one scores low.
- **Can contributors game it?** Yes, by doing the things we check for: explaining the change, linking an issue and adding tests. That is the behavior maintainers want.
- **Will it auto-close PRs?** No. It only drafts replies. The maintainer stays in control.
- **What if the model is down?** The pipeline falls back to a second model and then to rule checks alone. The UI shows which model and storage backend were used.
- **What next?** A GitHub Action that comments on new PRs automatically, per-repo rule tuning, and CONTRIBUTING.md-aware checks.

## Demo checklist
- [ ] `.venv/bin/streamlit run app.py` starts cleanly
- [ ] Demo mode toggle is on
- [ ] Browser zoomed so the cards and dashboard are readable from the back of the room
- [ ] Dashboard tab opened once so charts are warm
- [ ] Backup: screen recording of the full flow
