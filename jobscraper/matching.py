"""Filtering + scoring.

A role is KEPT only if:
  * its title fuzzy-matches one of the 7 target titles, AND
  * its text mentions Python AND at least one ML/NLP/LLM/FastAPI anchor skill.
Kept roles get a 0-100 score (title match + skill overlap + seniority fit),
an english_ok flag, and a stale flag.
"""
from __future__ import annotations

import re

from rapidfuzz import fuzz

import config
from jobscraper.model import Job


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def title_match(title: str) -> float:
    """Best fuzzy ratio (0-100) of the title against any target title."""
    t = _norm(title)
    if not t:
        return 0.0
    best = 0.0
    for target in config.TARGET_TITLES:
        # token_set_ratio handles word order / extra words ("Senior AI Engineer").
        best = max(best, fuzz.token_set_ratio(t, target))
        if target in t:          # direct substring is a strong signal
            best = max(best, 92.0)
    return best


def skill_overlap(text: str, skills: list[str]) -> tuple[bool, int]:
    """Return (passes_gate, overlap_count).

    Gate = mentions Python AND at least one anchor skill. overlap_count is how
    many of my skills appear, used for the score.
    """
    blob = _norm(text)
    has_primary = config.MUST_HAVE_PRIMARY in blob
    has_anchor = any(a in blob for a in config.MUST_HAVE_ANY)
    count = sum(1 for s in skills if s and s in blob)
    return (has_primary and has_anchor), count


def _has_word(blob: str, term: str) -> bool:
    """Whole-word / phrase match so 'intern' doesn't hit 'international'."""
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", blob) is not None


def _seniority_fit(title: str, text: str) -> int:
    """0-CAP seniority-fit.

    The TITLE is the strongest seniority signal, so junior/senior words there
    dominate. A '5+ years' requirement anywhere in the text also down-ranks.
    Tiers (CAP=15): explicit junior -> full; senior title word -> 15%;
    senior word in body only -> 40%; years-requirement -> 30%; else full.
    """
    cap = config.SENIORITY_CAP
    title_blob = _norm(title)
    body_blob = _norm(title + " " + text)

    # Explicit junior wins outright.
    if any(_has_word(title_blob, j) for j in config.JUNIOR_TERMS):
        return cap

    senior_in_title = any(_has_word(title_blob, t) for t in config.SENIORITY_PENALTY_TERMS)
    senior_in_body = any(_has_word(body_blob, t) for t in config.SENIORITY_PENALTY_TERMS)
    years_heavy = any(term in body_blob for term in config.SENIORITY_YEARS_TERMS)

    if senior_in_title:
        return int(round(cap * 0.15))
    if years_heavy:
        return int(round(cap * 0.30))
    if senior_in_body:
        return int(round(cap * 0.40))
    return cap


def _english_ok(text: str, location: str) -> bool:
    blob = _norm(text + " " + location)
    return not any(term in blob for term in config.GERMAN_REQUIRED_TERMS)


def _work_mode(job: Job) -> str:
    """remote | hybrid | onsite | unknown."""
    blob = _norm(f"{job.title} {job.location} {job.description}")
    if job.remote_hint is True:
        return "remote"
    if any(_has_word(blob, t) for t in config.HYBRID_TERMS):
        return "hybrid"
    if any(_has_word(blob, t) for t in config.REMOTE_TERMS):
        return "remote"
    if job.remote_hint is False and job.location.strip():
        return "onsite"
    return "onsite" if job.location.strip() else "unknown"


def _sponsorship(job: Job, work_mode: str) -> tuple[str, str]:
    """Return (needs_sponsorship, sponsorship_offered) for a non-EU national.

    Remote => no visa needed. Onsite/hybrid => a work visa / EU Blue Card is
    needed (I'd relocate). 'offered' = the posting explicitly mentions
    visa/relocation support, which is what makes an onsite role actually viable.
    """
    text = _norm(f"{job.title} {job.description}")
    offered = "yes" if any(t in text for t in config.SPONSORSHIP_OFFER_TERMS) else "unknown"

    if work_mode == "remote":
        return "no", offered
    if work_mode in ("onsite", "hybrid"):
        return "yes", offered
    return "unknown", offered


def score_job(job: Job, skills: list[str]) -> Job | None:
    """Apply the gate + scoring. Returns the mutated Job if kept, else None."""
    t_ratio = title_match(job.title)
    if t_ratio < config.FUZZY_TITLE_THRESHOLD:
        return None

    passes, overlap = skill_overlap(job.title + " " + job.description, skills)
    if not passes:
        return None

    # --- score components ---
    title_component = (t_ratio / 100.0) * config.TITLE_MATCH_CAP
    # Normalise overlap: ~6 skill hits saturates the cap.
    overlap_component = min(overlap / 6.0, 1.0) * config.SKILL_OVERLAP_CAP
    seniority_component = _seniority_fit(job.title, job.description)

    job.match_score = int(round(title_component + overlap_component + seniority_component))
    # Title matters: "... German Speaking" often lives only in the title.
    job.english_ok = _english_ok(job.title + " " + job.description, job.location)
    job.work_mode = _work_mode(job)
    job.needs_sponsorship, job.sponsorship_offered = _sponsorship(job, job.work_mode)
    days = job.days_old()
    job.stale = days is not None and days > config.STALE_AFTER_DAYS
    return job


def keep_matching(jobs: list[Job], skills: list[str]) -> list[Job]:
    out: list[Job] = []
    for j in jobs:
        scored = score_job(j, skills)
        if scored is not None:
            out.append(scored)
    return out


def company_name_matches(job: Job, company: str) -> bool:
    """Loose check that an aggregator row belongs to a seed company."""
    jc = re.sub(r"[^a-z0-9]+", " ", _norm(job.company))
    cc = re.sub(r"[^a-z0-9]+", " ", _norm(company))
    first = cc.split()[0] if cc.split() else cc
    return bool(first) and (first in jc or jc in cc)
