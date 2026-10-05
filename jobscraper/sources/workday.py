"""Workday cxs JSON adapter.

Workday hosts each employer under {tenant}.{wdhost}.myworkdayjobs.com with a
named site. There is no reliable public way to discover tenant+site from just a
company name, so this adapter only fires for companies explicitly mapped in
config.WORKDAY_TENANTS. Everything else returns None and falls through to the
aggregator-name fallback (expected for most big enterprises).
"""
from __future__ import annotations

import config
from jobscraper import http
from jobscraper.model import Job


def fetch(company: str, _slug: str) -> list[Job] | None:
    mapping = config.WORKDAY_TENANTS.get(company.lower())
    if not mapping:
        return None
    tenant, wdhost, site = mapping

    base = f"https://{tenant}.{wdhost}.myworkdayjobs.com"
    cxs = f"{base}/wday/cxs/{tenant}/{site}/jobs"
    jobs: list[Job] = []
    offset = 0
    page_limit = 20

    while offset < 200:  # cap at ~10 pages to stay polite
        body = {"appliedFacets": {}, "limit": page_limit, "offset": offset,
                "searchText": ""}
        data = http.get_json(cxs, method="POST", json_body=body,
                             headers={"Content-Type": "application/json"})
        if not data or "jobPostings" not in data:
            break
        postings = data.get("jobPostings", [])
        if not postings:
            break
        for p in postings:
            path = p.get("externalPath")
            if not path:
                continue
            jobs.append(Job(
                company=company,
                title=(p.get("title") or "").strip(),
                location=(p.get("locationsText") or "").strip(),
                source="workday",
                apply_link=f"{base}/en-US/{site}{path}",
                description=(p.get("title") or ""),  # list view gives little text
                posted_date="",  # Workday list view uses relative "Posted X days ago"
            ))
        if len(postings) < page_limit:
            break
        offset += page_limit
    return jobs or None
