"""Ashby public job-board API adapter."""
from __future__ import annotations

import re

import config
from jobscraper import http
from jobscraper.model import Job


def _strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", s).strip()


def fetch(company: str, slug: str) -> list[Job] | None:
    """Return jobs for an Ashby board, or None if the board doesn't exist."""
    data = http.get_json(config.ASHBY_URL.format(slug=slug))
    if not data or "jobs" not in data:
        return None
    jobs: list[Job] = []
    for j in data.get("jobs", []):
        # Only listed roles; apply link must be real.
        if j.get("isListed") is False:
            continue
        url = j.get("applyUrl") or j.get("jobUrl")
        if not url:
            continue
        jobs.append(Job(
            company=company,
            title=(j.get("title") or "").strip(),
            location=(j.get("location") or "").strip(),
            source="ashby",
            apply_link=url,
            description=_strip_html(j.get("descriptionPlain") or j.get("descriptionHtml") or ""),
            posted_date=(j.get("publishedAt") or "")[:10],
        ))
    return jobs
