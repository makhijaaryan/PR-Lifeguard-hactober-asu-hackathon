"""FastAPI wrapper around the existing Python pipeline. No scoring logic lives here.

Run from the repo root:  .venv/bin/uvicorn api.server:app --port 8000

Offline demo mode serves demo_cache.json and never touches the network, so the demo
works with no internet and no .streamlit/secrets.toml.
"""
import asyncio
import json
import logging
import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import requests  # noqa: E402

import github_client  # noqa: E402
import pipeline  # noqa: E402
import storage  # noqa: E402
from engine.config import load_config  # noqa: E402
from github_client import GitHubError, parse_repo  # noqa: E402

log = logging.getLogger("pr_lifeguard.api")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

CACHE_PATH = ROOT / "demo_cache.json"
MIN_LIMIT, MAX_LIMIT = 5, 25
STORAGE_LABELS = {storage.BACKEND_SNOWFLAKE: "Snowflake", storage.BACKEND_LOCAL: "Local (SQLite)"}
DEMO_STEPS = [
    ("Fetching PRs…", 0.12),
    ("Reading CONTRIBUTING.md…", 0.24),
    ("Reading PR template…", 0.3),
    ("Scoring {n}/{n}…", 0.9),
    ("Saving results…", 0.96),
]

@asynccontextmanager
async def lifespan(_app):
    threading.Thread(target=_warm_storage, daemon=True).start()
    yield


app = FastAPI(title="PR Lifeguard API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_cache_lock = threading.Lock()


# ---------- helpers ----------

def storage_label(value=None):
    value = value if value is not None else storage._backend
    return STORAGE_LABELS.get(value, "Checking…" if value is None else str(value))


def read_cache():
    try:
        return json.loads(CACHE_PATH.read_text())
    except Exception:  # missing or corrupt: behave as empty
        return {}


def save_to_cache(repo_key, result, limit):
    """Same format as app.py's cache, so Streamlit and the web app share it. Best effort."""
    with _cache_lock:
        try:
            cache = read_cache()
            cache[repo_key] = {**result, "_limit": limit}
            tmp = CACHE_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps(cache, indent=2))
            tmp.replace(CACHE_PATH)
        except Exception as e:
            log.warning("Could not update demo cache: %s", e)


def repo_key(repo):
    owner, name = parse_repo(repo)
    return f"{owner}/{name}".lower()


def public_result(result):
    out = {k: v for k, v in result.items() if not k.startswith("_")}
    out["storage_backend"] = storage_label(out.get("storage_backend"))
    return out


def sse(event, data):
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _explain_github_error(repo, err):
    """The pipeline reports any 404 as "Repo not found". If the repo exists, its PRs are disabled."""
    message = str(err)
    if not message.startswith("Repo not found"):
        return message
    try:
        owner, name = parse_repo(repo)
        resp = requests.get(f"{github_client.API}/repos/{owner}/{name}", headers=github_client._headers(), timeout=10)
        if resp.status_code == 200:
            return f"{owner}/{name} exists, but it doesn't accept pull requests on GitHub, so there's nothing to triage."
    except Exception:
        pass
    return message


def _warm_storage():
    try:
        storage.storage_backend()  # picks Snowflake or SQLite once, off the request path
    except Exception as e:
        log.warning("Storage check failed: %s", e)


# ---------- endpoints ----------

@app.get("/api/health")
def health():
    cfg = load_config()["llm"]
    return {
        "model": cfg.get("model") or "not configured",
        "storage_backend": storage_label(),
        "llm_configured": bool(cfg.get("api_key") and cfg.get("base_url")),
    }


@app.get("/api/demo-repos")
def demo_repos():
    cache = read_cache()
    repos = []
    for key, entry in cache.items():
        prs = entry.get("prs") or []
        repos.append({"key": key, "repo": entry.get("repo", key), "count": len(prs),
                      "model_used": entry.get("model_used")})
    return {"repos": repos}


class TriageRequest(BaseModel):
    repo: str
    limit: int = Field(12, ge=1, le=100)
    offline_demo: bool = False


async def _offline_stream(req):
    try:
        key = repo_key(req.repo)
    except GitHubError as e:
        yield sse("error", {"message": str(e)})
        return
    entry = read_cache().get(key)
    if not entry:
        names = ", ".join(read_cache()) or "none yet"
        yield sse("error", {"message": f"'{key}' isn't in the offline demo cache. Cached repos: {names}. "
                                       "Turn off Offline demo to triage it live."})
        return
    prs = (entry.get("prs") or [])[: req.limit]
    for message, fraction in DEMO_STEPS:
        yield sse("progress", {"message": message.format(n=len(prs)), "fraction": fraction})
        await asyncio.sleep(0.35)
    yield sse("progress", {"message": "Done.", "fraction": 1.0})
    yield sse("result", public_result({**entry, "prs": prs, "offline_demo": True}))


async def _live_stream(req):
    loop = asyncio.get_running_loop()
    queue = asyncio.Queue()
    limit = max(MIN_LIMIT, min(MAX_LIMIT, req.limit))

    def progress(message, fraction):
        loop.call_soon_threadsafe(queue.put_nowait, ("progress", {"message": message, "fraction": fraction}))

    def work():
        try:
            result = pipeline.triage(req.repo, limit, progress)
            if result.get("prs"):
                save_to_cache(result["repo"].lower(), result, limit)
            loop.call_soon_threadsafe(queue.put_nowait, ("result", public_result(result)))
        except GitHubError as e:
            loop.call_soon_threadsafe(queue.put_nowait, ("error", {"message": _explain_github_error(req.repo, e)}))
        except Exception:
            log.exception("Triage failed for %s", req.repo)
            loop.call_soon_threadsafe(queue.put_nowait, ("error", {
                "message": "Triage didn't complete. This is usually a network problem or a GitHub rate limit. "
                           "Try again, or switch on Offline demo to use a cached repo."}))

    threading.Thread(target=work, daemon=True).start()
    while True:
        event, data = await queue.get()
        yield sse(event, data)
        if event in ("result", "error"):
            return


@app.post("/api/triage")
async def triage(req: TriageRequest):
    stream = _offline_stream(req) if req.offline_demo else _live_stream(req)
    return StreamingResponse(stream, media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _history_from_cache():
    """When the database is empty (fresh clone), show the cached demo runs instead of nothing."""
    rows = []
    for entry in read_cache().values():
        for pr in entry.get("prs") or []:
            failed = [n for n, f in (pr.get("rule_flags") or {}).items() if not f.get("passed")]
            rows.append({"run_id": entry.get("run_id"), "scored_at": None, "repo": entry.get("repo"),
                         "pr_number": pr.get("number"), "title": pr.get("title"), "author": pr.get("author"),
                         "url": pr.get("url"), "final_score": pr.get("final_score"), "tier": pr.get("tier"),
                         "reason": pr.get("reason"), "failed_checks": ",".join(failed)})
    return rows


@app.get("/api/history")
def history():
    try:
        df = pipeline.load_history()
        rows = json.loads(df.to_json(orient="records", date_format="iso"))
        source = "database"
    except Exception as e:
        log.warning("Could not load history: %s", e)
        rows, source = [], "database"
    if not rows:
        rows, source = _history_from_cache(), "demo cache"
    return {"rows": rows, "source": source, "storage_backend": storage_label()}
