"""Dedupe across sources and against the applied log."""
from __future__ import annotations

import csv
import logging
from pathlib import Path

import config
from jobscraper.model import Job

log = logging.getLogger("jobscraper")


def load_applied_keys() -> set[str]:
    """Read applied_log.csv -> set of dedupe keys. Creates the file if missing.

    The log is expected to have company/title/location columns (any order);
    we build the same normalized key the Job uses.
    """
    path = config.APPLIED_LOG
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["company", "title", "location", "apply_link", "applied_on"])
        log.info("created empty applied_log.csv")
        return set()

    keys: set[str] = set()
    try:
        with path.open("r", newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                probe = Job(
                    company=row.get("company", ""),
                    title=row.get("title", ""),
                    location=row.get("location", ""),
                    source="applied", apply_link="x",
                )
                keys.add(probe.dedupe_key())
    except OSError as exc:
        log.warning("could not read applied_log.csv: %s", exc)
    return keys


def dedupe(jobs: list[Job], applied: set[str]) -> tuple[list[Job], int, int]:
    """Collapse duplicate roles and drop anything already applied to.

    When the same role appears from several sources we keep the one with the
    higher score (ATS direct links tend to win on skill text anyway).

    Returns (kept_jobs, dropped_applied_count, collapsed_duplicate_count).
    """
    best: dict[str, Job] = {}
    dropped_applied = 0
    collapsed = 0
    for j in jobs:
        key = j.dedupe_key()
        if key in applied:
            dropped_applied += 1
            continue
        if key in best:
            collapsed += 1
            if j.match_score > best[key].match_score:
                best[key] = j
        else:
            best[key] = j
    if dropped_applied:
        log.info("dropped %d roles already in applied_log", dropped_applied)
    if collapsed:
        log.info("collapsed %d cross-source duplicate roles", collapsed)
    return list(best.values()), dropped_applied, collapsed
