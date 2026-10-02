"""Loads settings from .streamlit/secrets.toml (env vars override)."""
import os
from pathlib import Path

try:
    import tomllib as _toml_load  # Python 3.11+
    _BINARY = True
except ImportError:
    import toml as _toml_load  # pip install toml
    _BINARY = False

SECRETS_PATH = Path(__file__).resolve().parent.parent / ".streamlit" / "secrets.toml"

DEFAULTS = {
    "snowflake": {"model": "llama3.1-70b", "fallback_model": "mistral-large2", "schema": "PUBLIC"},
    "github": {},
}


def _read_file():
    if not SECRETS_PATH.exists():
        return {}
    if _BINARY:
        with open(SECRETS_PATH, "rb") as f:
            return _toml_load.load(f)
    return _toml_load.load(SECRETS_PATH)


def load_config():
    """Return {"snowflake": {...}, "github": {...}}.

    Env overrides: SNOWFLAKE_<KEY> (e.g. SNOWFLAKE_API_KEY), GITHUB_TOKEN.
    """
    raw = _read_file()
    cfg = {sec: {**DEFAULTS[sec], **raw.get(sec, {})} for sec in DEFAULTS}
    for key in list(cfg["snowflake"]) + ["account", "user", "api_key", "role", "host", "warehouse", "database"]:
        val = os.environ.get(f"SNOWFLAKE_{key.upper()}")
        if val:
            cfg["snowflake"][key] = val
    if os.environ.get("GITHUB_TOKEN"):
        cfg["github"]["token"] = os.environ["GITHUB_TOKEN"]
    return cfg


def missing_keys(cfg=None):
    """List 'section.key' names that are required but empty (never returns values)."""
    cfg = cfg or load_config()
    required = {
        "snowflake": ["host", "api_key", "model"],
        "github": ["token"],
    }
    return [f"{s}.{k}" for s, keys in required.items() for k in keys if not cfg[s].get(k)]


if __name__ == "__main__":
    c = load_config()
    for sec, vals in c.items():
        for k, v in vals.items():
            shown = v if k in ("model", "fallback_model", "host", "account", "database", "schema", "warehouse", "role") else f"set ({len(str(v))} chars)"
            print(f"{sec}.{k} = {shown}")
    m = missing_keys(c)
    print("MISSING:", m or "none")
