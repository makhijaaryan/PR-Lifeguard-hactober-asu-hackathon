# Security Policy

## Reporting a vulnerability

Please **do not** report security issues in public issues or pull requests.

Use GitHub's private reporting instead: go to the **Security** tab of this repository and click **Report a vulnerability**. Include steps to reproduce and the impact you expect. We aim to reply within 7 days.

## Supported versions

Only the latest commit on `main` gets security fixes.

## Handling secrets

PR Lifeguard reads API keys (LLM, GitHub, Snowflake) only from `.streamlit/secrets.toml` or environment variables. That file is gitignored. If you think you have committed a key by mistake, rotate it straight away; removing it from git history is not enough.
