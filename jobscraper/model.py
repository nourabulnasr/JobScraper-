"""The single normalized Job record every source produces.

Each source adapter is responsible for mapping its own API shape onto this
dataclass, so the matching / dedupe / output layers only ever deal with Jobs.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


@dataclass
class Job:
    company: str
    title: str
    location: str
    source: str            # greenhouse | lever | ashby | workday | arbeitnow | adzuna | remotive
    apply_link: str        # MUST be an API-returned URL; never fabricated
    description: str = ""  # plain-ish text used for skill-overlap matching
    posted_date: str = ""  # ISO date string if the API gave one, else ""

    # Hint a source can set (e.g. Arbeitnow's remote flag, Remotive = remote-only).
    remote_hint: bool | None = None

    # Filled in by the matching layer:
    match_score: int = 0
    english_ok: bool = True
    stale: bool = False
    work_mode: str = "unknown"          # remote | onsite | hybrid | unknown
    needs_sponsorship: str = "unknown"  # no | yes | unknown  (for a non-EU national)
    sponsorship_offered: str = "unknown"  # yes | unknown (text mentions visa/relocation)

    def dedupe_key(self) -> str:
        """Normalized identity used to collapse the same role across sources."""
        def norm(s: str) -> str:
            s = (s or "").lower()
            s = re.sub(r"[^a-z0-9]+", " ", s)
            return re.sub(r"\s+", " ", s).strip()
        return f"{norm(self.company)}|{norm(self.title)}|{norm(self.location)}"

    def days_old(self) -> int | None:
        if not self.posted_date:
            return None
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z",
                    "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"):
            try:
                dt = datetime.strptime(self.posted_date, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return (datetime.now(timezone.utc) - dt).days
            except ValueError:
                continue
        return None

    def to_row(self) -> dict:
        d = asdict(self)
        # English-friendly booleans for the CSV
        d["english_ok"] = "yes" if self.english_ok else "no"
        d["stale"] = "yes" if self.stale else "no"
        return d
