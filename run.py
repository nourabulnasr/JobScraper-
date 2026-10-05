#!/usr/bin/env python
"""Job-hunt aggregator CLI.

Usage:
    python run.py                 # full run: resolve seeds, discover, rank, write
    python run.py --no-discovery  # only resolve seed companies (skip aggregators)
    python run.py --limit 60      # change how many rows the console prints

Reads seed_companies.txt (+ optional my_cv.*), pulls roles from official/free
ATS and aggregator APIs only, scores them against my CV skills, and writes
jobs_YYYY-MM-DD.csv + latest.csv + run.log.
"""
from __future__ import annotations

import argparse
import logging
import sys

from dotenv import load_dotenv

# Windows consoles default to cp1252; force UTF-8 so München/—/… render right.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass

import config
from jobscraper import cv, dedupe, matching, output, resolve
from jobscraper.model import Job
from jobscraper.sources import aggregators


def setup_logging() -> logging.Logger:
    log = logging.getLogger("jobscraper")
    log.setLevel(logging.INFO)
    log.handlers.clear()
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh = logging.FileHandler(config.RUN_LOG, encoding="utf-8")
    fh.setFormatter(fmt)
    log.addHandler(fh)
    # Keep the console clean; rich handles user-facing output.
    log.propagate = False
    return log


def read_seeds() -> list[str]:
    if not config.SEED_FILE.exists():
        output.console.print(f"[red]Missing {config.SEED_FILE.name}[/]")
        sys.exit(1)
    seeds = []
    for line in config.SEED_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            seeds.append(line)
    return seeds


def main() -> None:
    parser = argparse.ArgumentParser(description="AI/ML job aggregator CLI")
    parser.add_argument("--no-discovery", action="store_true",
                        help="skip aggregator discovery/fallback (seeds only)")
    parser.add_argument("--limit", type=int, default=40,
                        help="rows to print in the console table")
    args = parser.parse_args()

    load_dotenv(config.ROOT / ".env")
    log = setup_logging()
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    skills, skill_source = cv.load_skills()
    seeds = read_seeds()
    seed_lower = {s.lower() for s in seeds}
    applied = dedupe.load_applied_keys()

    output.console.print(f"[bold]Job scraper[/] — {len(seeds)} seed companies, "
                         f"skills from: {skill_source}")
    output.console.print("[dim]Resolving seed companies to their ATS...[/]\n")

    all_jobs: list[Job] = []
    resolved_count = 0
    ats_unknown: list[str] = []
    resolution_report: list[tuple[str, str, int]] = []  # (company, source, n)

    # --- Step 1: resolve each seed company to a direct ATS feed -------------
    for company in seeds:
        source_label, jobs = resolve.resolve_company(company)
        if source_label == "ats_unknown":
            ats_unknown.append(company)
            resolution_report.append((company, "ats_unknown", 0))
        else:
            resolved_count += 1
            all_jobs.extend(jobs)
            resolution_report.append((company, source_label, len(jobs)))

    _print_resolution(resolution_report)

    # --- Step 2: aggregator discovery + fallback ----------------------------
    discovery: list[Job] = []
    if not args.no_discovery:
        output.console.print("\n[dim]Querying aggregator APIs "
                             "(Arbeitnow / Remotive / Adzuna)...[/]")
        discovery = aggregators.discover()
        # Fallback: for ats_unknown seeds, pull their rows out of the discovery set.
        for company in ats_unknown:
            hits = [j for j in discovery if matching.company_name_matches(j, company)]
            if hits:
                log.info("%s surfaced via aggregator fallback (%d rows)",
                         company, len(hits))
        all_jobs.extend(discovery)

    # --- Step 3: match + score ----------------------------------------------
    kept = matching.keep_matching(all_jobs, skills)

    # --- Step 4: dedupe + drop applied --------------------------------------
    kept, applied_skipped, collapsed = dedupe.dedupe(kept, applied)

    # --- Step 5: sort + output ----------------------------------------------
    kept.sort(key=lambda j: j.match_score, reverse=True)

    # New companies = companies in kept results not in the seed list.
    kept_companies = {j.company.lower() for j in kept if j.company}
    new_companies = sorted(c for c in kept_companies if c not in seed_lower)

    remote_n = sum(1 for j in kept if j.needs_sponsorship == "no")
    onsite_n = sum(1 for j in kept if j.needs_sponsorship == "yes")
    sponsor_n = sum(1 for j in kept
                    if j.needs_sponsorship == "yes" and j.sponsorship_offered == "yes")

    dated_csv, latest_csv = output.write_csvs(kept)

    output.console.print()
    output.print_table(kept, limit=args.limit)
    output.print_summary({
        "kept": len(kept),
        "new_companies": len(new_companies),
        "resolved": resolved_count,
        "seed_total": len(seeds),
        "ats_unknown": len(ats_unknown),
        "applied_skipped": applied_skipped,
        "collapsed": collapsed,
        "remote_n": remote_n,
        "onsite_n": onsite_n,
        "sponsor_n": sponsor_n,
        "skill_source": skill_source,
        "dated_csv": dated_csv,
        "latest_csv": latest_csv,
    })
    if ats_unknown:
        output.console.print(f"\n[yellow]ats_unknown seeds[/] (relied on aggregator "
                             f"fallback): {', '.join(ats_unknown)}")


def _print_resolution(report: list[tuple[str, str, int]]) -> None:
    from rich.table import Table
    from rich import box
    t = Table(title="Seed company resolution", box=box.MINIMAL, header_style="bold")
    t.add_column("Company")
    t.add_column("Resolved via")
    t.add_column("Roles", justify="right")
    for company, source, n in report:
        style = "green" if source != "ats_unknown" else "yellow"
        t.add_row(company, f"[{style}]{source}[/]", str(n) if n else "-")
    output.console.print(t)


if __name__ == "__main__":
    main()
