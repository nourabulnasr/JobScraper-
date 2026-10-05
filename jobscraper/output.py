"""CSV writers + pretty console table + run summary."""
from __future__ import annotations

import csv
from datetime import date

from rich.console import Console
from rich.table import Table
from rich import box

import config
from jobscraper.model import Job

console = Console()

CSV_FIELDS = ["rank", "company", "title", "location", "source",
              "match_score", "english_ok", "work_mode", "needs_sponsorship",
              "sponsorship_offered", "stale", "posted_date", "apply_link"]


def write_csvs(jobs: list[Job]) -> tuple[str, str]:
    """Write jobs_YYYY-MM-DD.csv and latest.csv. Returns both paths."""
    dated = config.OUTPUT_DIR / f"jobs_{date.today().isoformat()}.csv"
    latest = config.OUTPUT_DIR / "latest.csv"
    for path in (dated, latest):
        with path.open("w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for rank, job in enumerate(jobs, start=1):
                row = job.to_row()
                writer.writerow({
                    "rank": rank,
                    "company": row["company"],
                    "title": row["title"],
                    "location": row["location"],
                    "source": row["source"],
                    "match_score": row["match_score"],
                    "english_ok": row["english_ok"],
                    "work_mode": row["work_mode"],
                    "needs_sponsorship": row["needs_sponsorship"],
                    "sponsorship_offered": row["sponsorship_offered"],
                    "stale": row["stale"],
                    "posted_date": row["posted_date"],
                    "apply_link": row["apply_link"],
                })
    return str(dated), str(latest)


def print_table(jobs: list[Job], limit: int = 40) -> None:
    table = Table(title="Ranked AI/ML roles — apply top-down",
                  box=box.SIMPLE_HEAVY, show_lines=False, header_style="bold")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Company", overflow="fold", max_width=18)
    table.add_column("Title", overflow="fold", max_width=34)
    table.add_column("Location", overflow="fold", max_width=20)
    table.add_column("Src", max_width=9)
    table.add_column("Score", justify="right")
    table.add_column("EN", justify="center")
    table.add_column("Mode · Visa", max_width=15)
    table.add_column("Apply link", overflow="fold", max_width=38)

    for rank, job in enumerate(jobs[:limit], start=1):
        score_style = "green" if job.match_score >= 70 else (
            "yellow" if job.match_score >= 50 else "red")
        en = "[green]yes[/]" if job.english_ok else "[red]no[/]"
        title = job.title + (" [dim](stale)[/]" if job.stale else "")
        table.add_row(
            str(rank), job.company, title, job.location, job.source,
            f"[{score_style}]{job.match_score}[/]", en, _visa_cell(job),
            job.apply_link,
        )
    console.print(table)
    if len(jobs) > limit:
        console.print(f"[dim]... and {len(jobs) - limit} more in latest.csv[/]")


def _visa_cell(job) -> str:
    """Compact work-mode + sponsorship indicator for the console."""
    if job.needs_sponsorship == "no":
        return f"[green]{job.work_mode}[/]"          # remote -> no visa fuss
    if job.needs_sponsorship == "yes":
        if job.sponsorship_offered == "yes":
            return f"[cyan]{job.work_mode}·visa[green]✓[/][/]"   # onsite + sponsors
        return f"[yellow]{job.work_mode}·visa?[/]"   # onsite, sponsorship unstated
    return f"[dim]{job.work_mode}[/]"


def print_summary(stats: dict) -> None:
    console.print()
    console.rule("[bold]Run summary")
    console.print(f"  Roles matched (kept)      : [bold]{stats['kept']}[/]")
    console.print(f"  New companies discovered  : [bold]{stats['new_companies']}[/]")
    console.print(f"  Seed companies resolved   : [bold green]{stats['resolved']}[/] "
                  f"/ {stats['seed_total']}")
    console.print(f"  Seed ats_unknown          : [bold yellow]{stats['ats_unknown']}[/]")
    console.print(f"  Roles already applied (skipped): {stats['applied_skipped']}")
    console.print(f"  Cross-source duplicates merged : {stats['collapsed']}")
    console.print(f"  Remote (no visa needed)        : [bold green]{stats['remote_n']}[/]")
    console.print(f"  Onsite/hybrid (visa needed)    : [bold yellow]{stats['onsite_n']}[/] "
                  f"(of which [cyan]{stats['sponsor_n']}[/] mention visa/relocation)")
    console.print(f"  Skill source             : {stats['skill_source']}")
    console.print(f"  Outputs                  : {stats['dated_csv']}")
    console.print(f"                             {stats['latest_csv']}")
