"""Result storage: Snowflake first, local SQLite (same table) if Snowflake fails for any reason.

The backend is chosen once per process on first use and then reused. Every operation opens
its own short-lived connection, so it is safe to call from several threads.
"""
import logging
import sqlite3
import threading
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd

from engine.config import load_config

log = logging.getLogger("pr_lifeguard.storage")

SQLITE_PATH = Path(__file__).resolve().parent / "pr_lifeguard.db"  # *.db is gitignored
TABLE = "PR_SCORES"
BACKEND_SNOWFLAKE = "Snowflake"
BACKEND_LOCAL = "Local (fallback)"
LOGIN_TIMEOUT = 15

# Order matters: load_history() must return exactly fake_history()'s columns.
HISTORY_COLUMNS = ["run_id", "scored_at", "repo", "pr_number", "title", "author", "url",
                   "final_score", "tier", "reason", "failed_checks"]
ALL_COLUMNS = HISTORY_COLUMNS + ["model_used"]

_SNOWFLAKE_DDL = f"""CREATE TABLE IF NOT EXISTS {TABLE} (
    run_id VARCHAR, scored_at TIMESTAMP_NTZ, repo VARCHAR, pr_number NUMBER, title VARCHAR,
    author VARCHAR, url VARCHAR, final_score NUMBER, tier VARCHAR, reason VARCHAR,
    failed_checks VARCHAR, model_used VARCHAR)"""
_SQLITE_DDL = f"""CREATE TABLE IF NOT EXISTS {TABLE} (
    run_id TEXT, scored_at TEXT, repo TEXT, pr_number INTEGER, title TEXT, author TEXT,
    url TEXT, final_score INTEGER, tier TEXT, reason TEXT, failed_checks TEXT, model_used TEXT)"""

_lock = threading.Lock()
_backend = None  # None until first use, then BACKEND_SNOWFLAKE or BACKEND_LOCAL


# ---------- connections ----------

def _snowflake_connect():
    import snowflake.connector  # imported lazily so a missing package just triggers the fallback
    warnings.filterwarnings("ignore", message=".*pyarrow.*")
    cfg = load_config()["snowflake"]
    missing = [k for k in ("account", "user", "api_key", "warehouse", "database") if not cfg.get(k)]
    if missing:
        raise RuntimeError("missing snowflake settings: " + ", ".join(missing))
    kwargs = dict(
        account=cfg["account"], user=cfg["user"], password=cfg["api_key"],  # PAT used as the password
        warehouse=cfg["warehouse"], database=cfg["database"], schema=cfg.get("schema") or "PUBLIC",
        login_timeout=LOGIN_TIMEOUT, network_timeout=30,
    )
    if cfg.get("role"):
        kwargs["role"] = cfg["role"]
    return snowflake.connector.connect(**kwargs)


def _sqlite_connect():
    con = sqlite3.connect(SQLITE_PATH, timeout=30)
    con.execute(_SQLITE_DDL)
    return con


def _use_local(reason):
    global _backend
    if _backend != BACKEND_LOCAL:
        log.warning("Snowflake unavailable (%s); using local SQLite at %s", reason, SQLITE_PATH.name)
    _backend = BACKEND_LOCAL
    return _backend


def _choose_backend():
    """Pick the backend on first use: try Snowflake (and create the table), else SQLite."""
    global _backend
    with _lock:
        if _backend is None:
            try:
                con = _snowflake_connect()
                try:
                    con.cursor().execute(_SNOWFLAKE_DDL)
                finally:
                    con.close()
                _backend = BACKEND_SNOWFLAKE
            except Exception as e:  # any failure at all -> local
                _use_local(str(e).splitlines()[0][:200] if str(e) else type(e).__name__)
            if _backend == BACKEND_LOCAL:
                _sqlite_connect().close()
        return _backend


def storage_backend():
    """"Snowflake" or "Local (fallback)"."""
    return _backend or _choose_backend()


# ---------- save ----------

def _rows(run_id, repo, prs, model_used):
    now = datetime.now().replace(microsecond=0)
    rows = []
    for pr in prs:
        failed = [name for name, flag in (pr.get("rule_flags") or {}).items() if not flag.get("passed")]
        rows.append((run_id, now, repo, pr["number"], pr.get("title", ""), pr.get("author", ""), pr.get("url", ""),
                     int(pr.get("final_score", 0)), pr.get("tier", ""), pr.get("reason", ""),
                     ",".join(failed), model_used))
    return rows


def _save_snowflake(rows):
    con = _snowflake_connect()
    try:
        con.cursor().executemany(
            f"INSERT INTO {TABLE} ({', '.join(ALL_COLUMNS)}) VALUES ({', '.join(['%s'] * len(ALL_COLUMNS))})", rows)
    finally:
        con.close()


def _save_sqlite(rows):
    rows = [(r[0], r[1].isoformat(sep=" "), *r[2:]) for r in rows]
    con = _sqlite_connect()
    try:
        with con:
            con.executemany(f"INSERT INTO {TABLE} ({', '.join(ALL_COLUMNS)}) VALUES ({', '.join('?' * len(ALL_COLUMNS))})", rows)
    finally:
        con.close()


def save_results(run_id, repo, prs, model_used):
    """Save one scored run (the `prs` list from triage). Returns the backend that stored it."""
    rows = _rows(run_id, repo, prs, model_used)
    if storage_backend() == BACKEND_SNOWFLAKE:
        try:
            _save_snowflake(rows)
            return BACKEND_SNOWFLAKE
        except Exception as e:
            _use_local(f"save failed: {str(e)[:150]}")
    _save_sqlite(rows)
    return BACKEND_LOCAL


# ---------- load ----------

def load_history():
    """All saved results as a DataFrame with exactly fake_history()'s columns, newest first."""
    df = None
    if storage_backend() == BACKEND_SNOWFLAKE:
        try:
            con = _snowflake_connect()
            try:
                cur = con.cursor()
                cur.execute(f"SELECT {', '.join(HISTORY_COLUMNS)} FROM {TABLE}")
                df = pd.DataFrame(cur.fetchall(), columns=HISTORY_COLUMNS)
            finally:
                con.close()
        except Exception as e:
            _use_local(f"load failed: {str(e)[:150]}")
    if df is None:
        con = _sqlite_connect()
        try:
            df = pd.read_sql_query(f"SELECT {', '.join(HISTORY_COLUMNS)} FROM {TABLE}", con)
        finally:
            con.close()
    df["scored_at"] = pd.to_datetime(df["scored_at"])
    for col in ("pr_number", "final_score"):
        df[col] = df[col].astype(int)
    df["failed_checks"] = df["failed_checks"].fillna("")
    return df.sort_values("scored_at", ascending=False).reset_index(drop=True)[HISTORY_COLUMNS]


def delete_run(run_id):
    """Remove one run (used by tests to clean up after themselves)."""
    if storage_backend() == BACKEND_SNOWFLAKE:
        try:
            con = _snowflake_connect()
            try:
                con.cursor().execute(f"DELETE FROM {TABLE} WHERE run_id = %s", (run_id,))
            finally:
                con.close()
            return
        except Exception as e:
            _use_local(f"delete failed: {str(e)[:150]}")
    con = _sqlite_connect()
    try:
        with con:
            con.execute(f"DELETE FROM {TABLE} WHERE run_id = ?", (run_id,))
    finally:
        con.close()
