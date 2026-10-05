"""Greenhouse boards API adapter."""
from __future__ import annotations

import re

import config
from jobscraper import http
from jobscraper.model import Job


def _strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = s.replace("&amp;", "&").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", s).strip()


def fetch(company: str, slug: str) -> list[Job] | None:
    """Return jobs for a Greenhouse board, or None if the board doesn't exist."""
    data = http.get_json(config.GREENHOUSE_URL.format(slug=slug))
    if not data or "jobs" not in data:
        return None
    jobs: list[Job] = []
    for j in data.get("jobs", []):
        url = j.get("absolute_url")
        if not url:
            continue  # never emit a row without a real apply link
        loc = (j.get("location") or {}).get("name", "") or ""
        jobs.append(Job(
            company=company,
            title=j.get("title", "").strip(),
            location=loc.strip(),
            source="greenhouse",
            apply_link=url,
            description=_strip_html(j.get("content", "")),
            posted_date=(j.get("updated_at") or j.get("first_published") or "")[:10],
        ))
    return jobs
