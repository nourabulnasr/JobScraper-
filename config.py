"""Central configuration for the job scraper.

Everything the matching / sourcing logic depends on lives here so there is a
single place to tune the behaviour without touching the code.
"""
from __future__ import annotations

from pathlib import Path

# --- Folders -----------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / "cache"
OUTPUT_DIR = ROOT  # CSVs are written next to run.py, per the spec

SEED_FILE = ROOT / "seed_companies.txt"
APPLIED_LOG = ROOT / "applied_log.csv"
RUN_LOG = ROOT / "run.log"

# --- What I'm hunting for ----------------------------------------------------
TARGET_TITLES = [
    "ai engineer",
    "machine learning engineer",
    "data scientist",
    "ai automation engineer",
    "generative ai engineer",
    "agentic ai developer",
    "agentic ai engineer",
]

# Baseline skills. If a CV file is present these are MERGED with what we extract
# from it; if not, these alone drive the skill-overlap check.
CORE_SKILLS = [
    "python", "fastapi", "nlp", "llm", "llms", "agents", "agentic",
    "machine learning", "ml", "deep learning", "pytorch", "tensorflow",
    "scikit-learn", "sklearn", "pandas", "numpy", "transformers",
    "next.js", "nextjs", "oracle sql", "sql", "rag", "langchain",
    "generative ai", "genai",
]

# A role must mention Python AND at least one of these "anchor" skills to pass
# the overlap gate. This is what stops an "AI Sales Manager" slipping through.
MUST_HAVE_PRIMARY = "python"
MUST_HAVE_ANY = ["ml", "machine learning", "nlp", "llm", "llms", "agents",
                 "agentic", "fastapi", "deep learning", "generative ai", "genai"]

# Words that signal a role is above my level -> down-rank (not dropped).
# Matched on WORD BOUNDARIES (see matching._seniority_fit), so "lead" won't hit
# "leadership" and "sr" won't hit "disaster".
SENIORITY_PENALTY_TERMS = [
    "senior", "sr", "staff", "principal", "lead", "director",
    "head of", "vp", "vice president", "manager", "architect",
]
# Explicitly junior signals that RESTORE full seniority-fit marks.
JUNIOR_TERMS = [
    "junior", "jr", "graduate", "grad", "entry level", "entry-level",
    "working student", "werkstudent", "intern", "internship", "trainee",
    "early career", "new grad",
]
# Years-of-experience patterns that push a role out of junior/mid range.
SENIORITY_YEARS_TERMS = ["5+ years", "6+ years", "7+ years", "8+ years",
                         "9+ years", "10+ years", "5-7 years", "6-8 years",
                         "7-10 years", "at least 5 years", "minimum 5 years"]

# German-LANGUAGE-required signals -> english_ok = False (kept, just flagged).
# NOTE: "(m/w/d)" is only German legal gender notation, NOT a language
# requirement, so it is deliberately NOT in this list — many German firms post
# English-language roles tagged (m/w/d).
GERMAN_REQUIRED_TERMS = [
    "german speaking", "german-speaking", "deutschsprachig",
    "fließend deutsch", "fliessend deutsch", "fließende deutschkenntnisse",
    "deutsch erforderlich", "german required", "german language required",
    "fluent german", "fluent in german", "sehr gute deutschkenntnisse",
    "gute deutschkenntnisse", "verhandlungssicheres deutsch",
    "verhandlungssichere deutschkenntnisse", "muttersprache deutsch",
]

# --- Scoring weights (sum of the three caps = 100) ---------------------------
TITLE_MATCH_CAP = 45
SKILL_OVERLAP_CAP = 40
SENIORITY_CAP = 15

FUZZY_TITLE_THRESHOLD = 78   # rapidfuzz token_set_ratio 0-100 to count as a hit
STALE_AFTER_DAYS = 30        # posting older than this is flagged stale

# --- Work mode + visa sponsorship (I'm a non-EU / Cairo-based grad) ----------
# Remote => I can work from Cairo, no visa needed.
# Onsite/hybrid in the EU => I'd relocate and need a work visa / EU Blue Card.
REMOTE_TERMS = ["remote", "fully remote", "100% remote", "work from home",
                "home office", "homeoffice", "work from anywhere", "telecommute",
                "remote-first", "remote first"]
HYBRID_TERMS = ["hybrid"]

# Location hints that mean a physical EU/EEA/CH presence (travel = sponsorship).
EU_LOCATION_TERMS = [
    "germany", "deutschland", "berlin", "munich", "münchen", "muenchen",
    "hamburg", "frankfurt", "cologne", "köln", "koeln", "stuttgart",
    "düsseldorf", "dusseldorf", "leipzig", "nuremberg", "nürnberg",
    "austria", "vienna", "wien", "netherlands", "amsterdam", "rotterdam",
    "belgium", "brussels", "france", "paris", "lyon", "spain", "madrid",
    "barcelona", "italy", "milan", "rome", "ireland", "dublin", "poland",
    "warsaw", "krakow", "sweden", "stockholm", "denmark", "copenhagen",
    "finland", "helsinki", "portugal", "lisbon", "porto", "czech", "prague",
    "luxembourg", "switzerland", "zurich", "zürich", "geneva",
    "europe", "european union", "eu", "eea", "emea", "schengen",
]

# Employer explicitly supports relocation / visa => prioritise for onsite roles.
SPONSORSHIP_OFFER_TERMS = [
    "visa sponsorship", "visa support", "visa assistance", "we sponsor",
    "sponsor your visa", "sponsor a visa", "sponsorship available",
    "sponsorship provided", "relocation", "relocation support",
    "relocation package", "relocation assistance", "relocation bonus",
    "blue card", "eu blue card", "work permit", "work visa",
]

# --- Networking --------------------------------------------------------------
REQUEST_TIMEOUT = 20         # seconds
RATE_LIMIT_SLEEP = 1.0       # seconds between live API calls
CACHE_TTL_HOURS = 12         # re-use cached raw responses younger than this
USER_AGENT = "job-scraper/1.0 (personal job-hunt CLI; contact: local use)"

# --- Source endpoints --------------------------------------------------------
GREENHOUSE_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
LEVER_URL = "https://api.lever.co/v0/postings/{slug}?mode=json"
ASHBY_URL = "https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=false"

ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"
REMOTIVE_URL = "https://remotive.com/api/remote-jobs"
ADZUNA_URL = ("https://api.adzuna.com/v1/api/jobs/{country}/search/1"
              "?app_id={app_id}&app_key={app_key}&results_per_page=50"
              "&what={what}&content-type=application/json")
ADZUNA_COUNTRIES = ["de", "gb", "us"]

# Optional: known Workday tenants for seed companies. Most big firms won't be
# here (there's no reliable public way to discover tenant/site from a name),
# so they fall through to the aggregator-name fallback and that's expected.
# Format: "company name (lowercased)": ("tenant", "wd-host", "site-path")
WORKDAY_TENANTS: dict[str, tuple[str, str, str]] = {
    # "dell": ("dell", "wd1", "External"),  # example shape only
}
