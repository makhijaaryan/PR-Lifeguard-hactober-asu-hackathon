"""OpenAI-compatible chat client: ask_llm(system_prompt, user_prompt) -> (text, model_used).

Works with Groq, OpenRouter, Together, etc. Settings come from [llm] in
.streamlit/secrets.toml. Stateless, so it is safe to call from several threads.
"""
import time

import requests

from engine.config import load_config  # reads .streamlit/secrets.toml (tomllib, toml fallback)

TIMEOUT = 60
RATE_LIMIT_WAIT = 4  # seconds to wait before the single 429 retry
MAX_RATE_LIMIT_WAIT = 15


class LLMError(RuntimeError):
    pass


def _post(url, headers, body, model):
    try:
        return requests.post(url, headers=headers, json=body, timeout=TIMEOUT)
    except requests.Timeout as e:
        raise LLMError(f"Timed out after {TIMEOUT}s calling model '{model}'") from e
    except requests.RequestException as e:
        raise LLMError(f"Network error calling LLM API: {e}") from e


def _call(cfg, model, system_prompt, user_prompt):
    url = cfg["base_url"].strip().rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"}
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
    }
    resp = _post(url, headers, body, model)
    if resp.status_code == 429:  # rate limited: wait once, then retry
        try:
            wait = float(resp.headers.get("Retry-After", RATE_LIMIT_WAIT))
        except ValueError:
            wait = RATE_LIMIT_WAIT
        time.sleep(min(max(wait, 1), MAX_RATE_LIMIT_WAIT))
        resp = _post(url, headers, body, model)
    if resp.status_code != 200:
        hint = {400: " (bad request / unknown model?)", 401: " (bad or expired API key?)",
                403: " (key lacks access to this model?)", 404: " (check base_url or model name)",
                429: " (rate limited, even after retry)"}.get(resp.status_code, "")
        raise LLMError(f"LLM HTTP {resp.status_code} for model '{model}'{hint}: {resp.text[:300]}")
    try:
        text = (resp.json()["choices"][0]["message"]["content"] or "").strip()
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise LLMError(f"Unexpected response shape from '{model}': {resp.text[:300]}") from e
    if not text:
        raise LLMError(f"Model '{model}' returned an empty response")
    return text


def ask_llm(system_prompt, user_prompt):
    """Call the main model; on failure retry once with the fallback. Returns (text, model_used)."""
    cfg = load_config()["llm"]
    for key in ("base_url", "api_key", "model"):
        if not cfg.get(key):
            raise LLMError(f"Missing llm.{key} in .streamlit/secrets.toml")
    main, fallback = cfg["model"], cfg.get("fallback_model")
    try:
        return _call(cfg, main, system_prompt, user_prompt), main
    except LLMError as first:
        if not fallback or fallback == main:
            raise
        try:
            return _call(cfg, fallback, system_prompt, user_prompt), fallback
        except LLMError as second:
            raise LLMError(f"Main model failed: {first} | Fallback failed: {second}") from second
