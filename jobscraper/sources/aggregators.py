"""Aggregator APIs: Arbeitnow, Remotive, Adzuna.

These serve two jobs:
  1. DISCOVERY — surface roles for the 7 target titles across many companies.
  2. FALLBACK  — when a seed company has no clean ATS, we still find its roles
     by filtering these feeds on the company name.

All are free; Adzuna needs app_id/app_key from .env and is skipped if absent.
"""
from __future__ import annotations

import os
import re
from urllib.parse import quote_plus

import config
from jobscraper import http
from jobscraper.model import Job


def _strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = s.replace("&amp;", "&").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", s).strip()


# --- Arbeitnow (Germany/EU, no key, paginated) -------------------------------
def arbeitnow(max_pages: int = 3) -> list[Job]:
    jobs: list[Job] = []
    url = config.ARBEITNOW_URL
    for _ in range(max_pages):
        data = http.get_json(url)
        if not data or "data" not in data:
            break
        for j in data.get("data", []):
            link = j.get("url")
            if not link:
                continue
            tags = " ".join(j.get("tags", []) or []) + " " + \
                   " ".join(j.get("job_types", []) or [])
            jobs.append(Job(
                company=(j.get("company_name") or "").strip(),
                title=(j.get("title") or "").strip(),
                location=(j.get("location") or "").strip(),
                source="arbeitnow",
                apply_link=link,
                description=_strip_html(j.get("description", "")) + " " + tags,
                posted_date=_epoch_to_date(j.get("created_at")),
                remote_hint=bool(j.get("remote")) if j.get("remote") is not None else None,
            ))
        nxt = (data.get("links") or {}).get("next")
        if not nxt:
            break
        url = nxt
    return jobs


def _epoch_to_date(v) -> str:
    from datetime import datetime, timezone
    try:
        return datetime.fromtimestamp(int(v), tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return str(v)[:10] if v else ""


# --- Remotive (remote, no key) ----------------------------------------------
def remotive(search: str = "") -> list[Job]:
    url = config.REMOTIVE_URL
    if search:
        url = f"{url}?search={quote_plus(search)}"
    data = http.get_json(url)
    if not data or "jobs" not in data:
        return []
    jobs: list[Job] = []
    for j in data.get("jobs", []):
        link = j.get("url")
        if not link:
            continue
        jobs.append(Job(
            company=(j.get("company_name") or "").strip(),
            title=(j.get("title") or "").strip(),
            location=(j.get("candidate_required_location") or "Remote").strip(),
            source="remotive",
            apply_link=link,
            description=_strip_html(j.get("description", "")),
            posted_date=(j.get("publication_date") or "")[:10],
            remote_hint=True,  # Remotive is a remote-only board
        ))
    return jobs


# --- Adzuna (needs keys) -----------------------------------------------------
def adzuna(what: str) -> list[Job]:
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        return []
    jobs: list[Job] = []
    for country in config.ADZUNA_COUNTRIES:
        url = config.ADZUNA_URL.format(
            country=country, app_id=app_id, app_key=app_key,
            what=quote_plus(what),
        )
        data = http.get_json(url)
        if not data or "results" not in data:
            continue
        for j in data.get("results", []):
            link = j.get("redirect_url")
            if not link:
                continue
            jobs.append(Job(
                company=((j.get("company") or {}).get("display_name") or "").strip(),
                title=(j.get("title") or "").strip(),
                location=((j.get("location") or {}).get("display_name") or "").strip(),
                source="adzuna",
                apply_link=link,
                description=_strip_html(j.get("description", "")),
                posted_date=(j.get("created") or "")[:10],
            ))
    return jobs


def discover() -> list[Job]:
    """Pull the full discovery set from every available aggregator once."""
    jobs: list[Job] = []
    jobs += arbeitnow()
    jobs += remotive(search="ai")
    jobs += remotive(search="machine learning")
    # One Adzuna query per target title (only runs if keys are set).
    for title in config.TARGET_TITLES:
        jobs += adzuna(title)
    return jobs
