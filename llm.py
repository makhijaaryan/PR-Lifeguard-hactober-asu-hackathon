"""OpenAI-compatible chat client: ask_llm(system_prompt, user_prompt) -> (text, model_used).

Works with Groq, OpenRouter, Together, etc. Settings come from [llm] in
.streamlit/secrets.toml. Stateless, so it is safe to call from several threads.

Free tiers have small per-minute token budgets per model, so on a 429 we switch to the
other model straight away (it has its own budget) and only wait when both are limited.
"""
import time

import requests

from engine.config import load_config  # reads .streamlit/secrets.toml (tomllib, toml fallback)

TIMEOUT = 60
RATE_LIMIT_ROUNDS = 4        # tries per model when the API keeps answering 429
RATE_LIMIT_WAIT = 5          # seconds to wait when no Retry-After header is given
MAX_RATE_LIMIT_WAIT = 20
MAX_TOKENS = 700


class LLMError(RuntimeError):
    pass


class _RateLimited(LLMError):
    def __init__(self, message, wait):
        super().__init__(message)
        self.wait = wait


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
        "max_tokens": MAX_TOKENS,
        "stream": False,
    }
    if "gpt-oss" in model:
        body["reasoning_effort"] = "low"  # fewer hidden reasoning tokens: faster and cheaper on rate limits
    resp = _post(url, headers, body, model)
    if resp.status_code == 429:
        try:
            wait = float(resp.headers.get("Retry-After", RATE_LIMIT_WAIT))
        except ValueError:
            wait = RATE_LIMIT_WAIT
        raise _RateLimited(f"LLM HTTP 429 for model '{model}' (rate limited)", wait)
    if resp.status_code != 200:
        hint = {400: " (bad request / unknown model?)", 401: " (bad or expired API key?)",
                403: " (key lacks access to this model?)", 404: " (check base_url or model name)"}.get(resp.status_code, "")
        raise LLMError(f"LLM HTTP {resp.status_code} for model '{model}'{hint}: {resp.text[:300]}")
    try:
        text = (resp.json()["choices"][0]["message"]["content"] or "").strip()
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise LLMError(f"Unexpected response shape from '{model}': {resp.text[:300]}") from e
    if not text:
        raise LLMError(f"Model '{model}' returned an empty response")
    return text


def ask_llm(system_prompt, user_prompt):
    """Call the main model, falling back to fallback_model. Returns (text, model_used).

    A non-429 error rules a model out for this call. A 429 moves on to the other model;
    when every remaining model is rate limited, wait (Retry-After, capped) and go round again.
    """
    cfg = load_config()["llm"]
    for key in ("base_url", "api_key", "model"):
        if not cfg.get(key):
            raise LLMError(f"Missing llm.{key} in .streamlit/secrets.toml")
    models = [cfg["model"]]
    if cfg.get("fallback_model") and cfg["fallback_model"] != cfg["model"]:
        models.append(cfg["fallback_model"])

    errors = {}
    for attempt in range(RATE_LIMIT_ROUNDS):
        waits = []
        for model in list(models):
            try:
                return _call(cfg, model, system_prompt, user_prompt), model
            except _RateLimited as e:
                errors[model] = str(e)
                waits.append(e.wait)
            except LLMError as e:
                errors[model] = str(e)
                models.remove(model)
        if not models or attempt == RATE_LIMIT_ROUNDS - 1:
            break
        time.sleep(min(max(min(waits), 1), MAX_RATE_LIMIT_WAIT))
    raise LLMError(" | ".join(f"{m}: {err}" for m, err in errors.items()))
