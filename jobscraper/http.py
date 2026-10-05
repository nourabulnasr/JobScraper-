"""Cached, rate-limited HTTP layer.

Every outbound call goes through here so that:
  * raw responses are cached to /cache (re-runs are cheap, don't re-hit APIs),
  * we sleep between *live* calls to respect rate limits,
  * failures degrade gracefully (return None, log, carry on).
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

import requests

import config

log = logging.getLogger("jobscraper")

_last_live_call = 0.0


def _cache_path(key: str) -> Path:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return config.CACHE_DIR / f"{digest}.json"


def _read_cache(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    age_hours = (time.time() - path.stat().st_mtime) / 3600
    if age_hours > config.CACHE_TTL_HOURS:
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None


def _write_cache(path: Path, payload: dict) -> None:
    try:
        config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh)
    except OSError as exc:
        log.warning("cache write failed for %s: %s", path.name, exc)


def _throttle() -> None:
    global _last_live_call
    elapsed = time.time() - _last_live_call
    wait = config.RATE_LIMIT_SLEEP - elapsed
    if wait > 0:
        time.sleep(wait)
    _last_live_call = time.time()


def get_json(
    url: str,
    *,
    method: str = "GET",
    json_body: Optional[dict] = None,
    headers: Optional[dict] = None,
    cache_key: Optional[str] = None,
    expect_status: int = 200,
) -> Optional[Any]:
    """Fetch JSON with caching + throttling.

    Returns the parsed JSON, or None on any failure / non-expected status.
    The cache key defaults to the method+url+body so GET and POST variants
    don't collide.
    """
    key = cache_key or f"{method}:{url}:{json.dumps(json_body, sort_keys=True) if json_body else ''}"
    cpath = _cache_path(key)

    cached = _read_cache(cpath)
    if cached is not None:
        if cached.get("status") == expect_status:
            return cached.get("body")
        return None  # cached a known failure; don't retry within TTL

    _throttle()
    req_headers = {"User-Agent": config.USER_AGENT, "Accept": "application/json"}
    if headers:
        req_headers.update(headers)

    try:
        resp = requests.request(
            method, url, json=json_body, headers=req_headers,
            timeout=config.REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        log.warning("request error %s %s -> %s", method, _safe(url), exc)
        return None

    status = resp.status_code
    body: Any = None
    if status == expect_status:
        try:
            body = resp.json()
        except ValueError:
            log.warning("non-JSON body from %s", _safe(url))
            status = -1

    # Cache both successes and clean failures so re-runs are cheap.
    _write_cache(cpath, {"status": status, "body": body})
    if status != expect_status:
        log.info("non-%d status %s from %s", expect_status, status, _safe(url))
        return None
    return body


def _safe(url: str) -> str:
    """Strip query string so API keys never land in the log."""
    return url.split("?", 1)[0]
