"""Snowflake Cortex REST client: ask_llm(system_prompt, user_prompt) -> (text, model_used)."""
import json

import requests

from engine.config import load_config  # reads .streamlit/secrets.toml (tomllib, toml fallback)

TIMEOUT = 60


class LLMError(RuntimeError):
    pass


def _parse_response(resp):
    """Return text from either a normal JSON body or an SSE stream."""
    ctype = resp.headers.get("Content-Type", "")
    if "text/event-stream" in ctype:
        parts = []
        for raw in resp.iter_lines(decode_unicode=True):
            if not raw or not raw.startswith("data:"):
                continue
            payload = raw[5:].strip()
            if payload == "[DONE]":
                break
            try:
                choice = json.loads(payload)["choices"][0]
            except (ValueError, KeyError, IndexError):
                continue
            piece = (choice.get("delta") or choice.get("message") or {}).get("content")
            if piece:
                parts.append(piece)
        return "".join(parts)
    try:
        return resp.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError) as e:
        raise LLMError(f"Unexpected response shape: {resp.text[:300]}") from e


def _call(cfg, model, system_prompt, user_prompt):
    host = cfg["host"].strip().rstrip("/")
    if not host.startswith("http"):
        host = "https://" + host
    url = f"{host}/api/v2/cortex/inference:complete"
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "X-Snowflake-Authorization-Token-Type": "PROGRAMMATIC_ACCESS_TOKEN",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
    }
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=TIMEOUT, stream=True)
    except requests.Timeout as e:
        raise LLMError(f"Timed out after {TIMEOUT}s calling model '{model}'") from e
    except requests.RequestException as e:
        raise LLMError(f"Network error calling Cortex: {e}") from e
    if resp.status_code != 200:
        hint = {401: " (bad/expired PAT?)", 403: " (role lacks Cortex access?)",
                404: " (check host or model name)", 429: " (rate limited)"}.get(resp.status_code, "")
        if "Network policy is required" in resp.text:
            hint = " (Snowflake needs a network policy on this user before a PAT works; see README/admin fix)"
        raise LLMError(f"Cortex HTTP {resp.status_code} for model '{model}'{hint}: {resp.text[:300]}")
    text = _parse_response(resp).strip()
    if not text:
        raise LLMError(f"Model '{model}' returned an empty response")
    return text


def ask_llm(system_prompt, user_prompt):
    """Call the main model; on failure retry once with the fallback. Returns (text, model_used)."""
    cfg = load_config()["snowflake"]
    for key in ("host", "api_key", "model"):
        if not cfg.get(key):
            raise LLMError(f"Missing snowflake.{key} in .streamlit/secrets.toml")
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
