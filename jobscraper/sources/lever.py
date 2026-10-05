"""Lever postings API adapter."""
from __future__ import annotations

from datetime import datetime, timezone

import config
from jobscraper import http
from jobscraper.model import Job


def _ms_to_date(ms) -> str:
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return ""


def fetch(company: str, slug: str) -> list[Job] | None:
    """Return jobs for a Lever account, or None if the account doesn't exist."""
    data = http.get_json(config.LEVER_URL.format(slug=slug))
    # Lever returns a JSON list on success.
    if not isinstance(data, list):
        return None
    jobs: list[Job] = []
    for j in data:
        url = j.get("hostedUrl") or j.get("applyUrl")
        if not url:
            continue
        cats = j.get("categories") or {}
        jobs.append(Job(
            company=company,
            title=(j.get("text") or "").strip(),
            location=(cats.get("location") or "").strip(),
            source="lever",
            apply_link=url,
            description=(j.get("descriptionPlain") or j.get("description") or "").strip(),
            posted_date=_ms_to_date(j.get("createdAt")),
        ))
    return jobs
