"""Resolve each seed company to its careers feed.

Order (stop at first that returns jobs): Greenhouse -> Lever -> Ashby ->
Workday -> aggregator-name fallback. We try a few slug variants per company
and log which source each resolved to.
"""
from __future__ import annotations

import logging
import re

import config
from jobscraper.model import Job
from jobscraper.sources import greenhouse, lever, ashby, workday

log = logging.getLogger("jobscraper")


def slug_variants(company: str) -> list[str]:
    """Generate plausible ATS slugs for a company name, most-likely first."""
    name = company.strip().lower()
    # Drop common corporate suffixes for one of the variants.
    stripped = re.sub(r"\b(inc|inc\.|llc|ltd|ltd\.|group|corp|co|company|plc|sa|ag|gmbh)\b",
                      "", name).strip()

    def collapse(s: str, sep: str = "") -> str:
        s = re.sub(r"&", " and ", s)
        s = re.sub(r"[^a-z0-9]+", sep, s).strip(sep)
        return s

    variants = [
        collapse(name, ""),       # johnsonjohnson
        collapse(name, "-"),      # johnson-johnson
        collapse(stripped, ""),
        collapse(stripped, "-"),
        collapse(name.split()[0], ""),  # first word only, e.g. "shell"
    ]
    # De-dupe while preserving order, drop empties.
    seen: set[str] = set()
    out: list[str] = []
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


# (source label, module) in resolution order
_ATS_ORDER = [
    ("greenhouse", greenhouse),
    ("lever", lever),
    ("ashby", ashby),
    ("workday", workday),
]


def resolve_company(company: str) -> tuple[str, list[Job]]:
    """Return (source_label, jobs). source_label is 'ats_unknown' if nothing
    direct resolved — the caller then applies the aggregator fallback."""
    for label, module in _ATS_ORDER:
        for slug in slug_variants(company):
            try:
                jobs = module.fetch(company, slug)
            except Exception as exc:  # a bad adapter must not kill the run
                log.warning("%s adapter error for %s (%s): %s",
                            label, company, slug, exc)
                jobs = None
            if jobs:  # non-empty list = resolved
                log.info("%s resolved via %s (slug=%s, %d roles)",
                         company, label, slug, len(jobs))
                return label, jobs
    log.info("%s -> ats_unknown (will use aggregator fallback)", company)
    return "ats_unknown", []
