# Contributing to PR Lifeguard

Thanks for helping. PR Lifeguard scores pull requests on effort, so we try to practise what it checks for.

## Before you open a PR

- **Open or link an issue** for anything bigger than a typo, so we can agree on the approach first.
- **Describe the change**: what it does, why, and how you tested it. The PR template walks you through this.
- **Add or update tests** when you change behaviour.
- **Keep it focused**: one change per PR is much easier to review.

Using AI tools is fine. We care that you understand and have tested what you submit.

## Development setup

You need Python 3.11+ and Node.js 20+.

```bash
./dev.sh    # creates .venv, installs deps, starts the API on :8000 and the web app on :3000
```

The app starts in **Offline demo** mode, which replays `demo_cache.json` and needs no API keys. To run live, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill it in. Never commit that file.

## Project layout

| Path | What lives there |
|---|---|
| `pipeline.py`, `checks.py`, `scorer.py`, `llm.py`, `github_client.py`, `storage.py`, `contract.py` | The Python scoring engine |
| `engine/config.py` | Loads settings from `.streamlit/secrets.toml` and environment variables |
| `api/server.py` | FastAPI wrapper around the engine (no scoring logic) |
| `web/` | Next.js frontend (landing page and the Triage and Insights tabs) |
| `app.py` | The original Streamlit UI, kept as a backup |
| `tests/` | Test scripts |
| `skills/pr-lifeguard/` | The scoring logic packaged as an Agent Skill |
| `docs/` | Screenshots and the hackathon pitch |

## Running checks

Run these from the repo root before opening a PR. CI runs the same offline checks.

```bash
.venv/bin/python -m tests.test_checks --offline
.venv/bin/python -m tests.test_scorer --offline
.venv/bin/python -m tests.test_storage
cd web && npm run lint && npm run build
```

The live tests (`tests.test_github`, `tests.test_llm`, `tests.test_pipeline`) call GitHub and the LLM, so they need network access and secrets.

## Code style

- Python: follow the style of the surrounding code, and keep scoring logic out of `api/` and `web/`.
- TypeScript: `npm run lint` must pass.

## Reporting security issues

Please don't open a public issue. See [SECURITY.md](SECURITY.md).

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE) and that you will follow our [Code of Conduct](CODE_OF_CONDUCT.md).
