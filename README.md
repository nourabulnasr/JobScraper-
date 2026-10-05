# Job Scraper — AI/ML role aggregator

A single-command CLI that finds AI/ML/NLP roles matching my CV across **official,
free APIs only** (no LinkedIn/Indeed scraping), scores them against my skills, and
writes a ranked spreadsheet with a **direct apply link per role** so I can apply
top-down.

Built for a 2026 CS grad targeting AI/ML/NLP roles in Germany/EU + remote.

---

## Quick start

```bash
# 1. (one-time) create a virtualenv and install deps
python -m venv .venv
.venv\Scripts\activate           # Windows
pip install -r requirements.txt

# 2. (optional) add Adzuna keys for more coverage
copy .env.example .env           # then paste your keys

# 3. run it
python run.py
```

Outputs, written next to `run.py`:

| File | What |
|------|------|
| `jobs_YYYY-MM-DD.csv` | Dated snapshot of this run |
| `latest.csv` | Stable file I can always open |
| `run.log` | What resolved to what, warnings, rate-limit notes |
| A pretty console table | Ranked, colour-coded, apply links |

CSV columns: `rank, company, title, location, source, match_score, english_ok,
work_mode, needs_sponsorship, sponsorship_offered, stale, posted_date,
apply_link`, sorted by `match_score` descending.

### Flags
- `python run.py --no-discovery` — only resolve seed companies, skip aggregators
- `python run.py --limit 60` — print more rows to the console (CSV always has all)

---

## Inputs (all in this folder)

- **`seed_companies.txt`** — one company per line (provided).
- **`my_cv.(pdf|docx|txt)`** — *optional*. If present, it's parsed and any known
  skills it mentions are merged in. **If absent, the core skills baked into
  `config.py` are used** (Python, FastAPI, NLP, LLMs/agents, ML stack, Next.js,
  Oracle SQL, …). The run tells you which source it used.
- **`applied_log.csv`** — roles already applied to. Auto-created if missing;
  anything in it (matched by company+title+location) is dropped from results.
- **`.env`** — `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` (optional). Gitignored.

---

## How it works

### 1. Resolve each seed company to a careers feed
For every seed, it tries ATS feeds **in order, stopping at the first that returns
jobs**, trying a few slug variants (lowercase, no spaces, no punctuation,
with/without corporate suffixes):

1. **Greenhouse** → `boards-api.greenhouse.io`
2. **Lever** → `api.lever.co`
3. **Ashby** → `api.ashbyhq.com`
4. **Workday** → public `cxs` JSON endpoint *(see limitation below)*
5. **Fallback** → the aggregator APIs, filtered by company name

It logs which source each company resolved to, or `ats_unknown`.

### 2. Discover more companies
The aggregator APIs surface roles for the 7 target titles across many employers:
- **Arbeitnow** (Germany/EU, no key)
- **Remotive** (remote, no key)
- **Adzuna** (`de`, `gb`, `us` — only if keys are set)

### 3. Match + score (0–100)
A role is **kept only if** its title fuzzy-matches one of the 7 target titles
**and** its text mentions **Python + at least one** of ML / NLP / LLM-agents /
FastAPI. That skill gate is what stops an "AI Sales Manager" slipping through on
title alone.

Score = title match (≤45) + skill overlap (≤40) + seniority fit (≤15).
Senior/staff/lead/principal titles and "5+ years required" are **down-ranked, not
dropped**. Explicitly junior/grad/intern roles get full seniority marks.

Each role is also flagged:
- `english_ok = no` when German *language* is required (e.g. "German Speaking",
  "fließend Deutsch"). Note: the `(m/w/d)` tag alone is just German legal gender
  notation and does **not** flip the flag.
- `stale = yes` when the posting is older than 30 days.

### Visa / sponsorship (I'm a non-EU, Cairo-based grad)
- `work_mode` — `remote` / `onsite` / `hybrid` / `unknown`.
- `needs_sponsorship` — `no` for remote (I work from Cairo, no visa);
  `yes` for onsite/hybrid (I'd relocate and need a work visa / EU Blue Card).
- `sponsorship_offered` — `yes` when the posting explicitly mentions visa
  sponsorship / relocation / Blue Card, else `unknown` (absence of a mention is
  not a "no"). **Prioritise onsite roles where this is `yes`** — those are the
  ones actually viable without an EU passport.

> Caveat: some aggregator "remote" roles are *remote-within-Germany/EU* and may
> still require local work authorization. For truly remote roles, double-check
> the posting's geographic eligibility before assuming no visa is needed.

### 4. Dedupe
Collapses the same role across sources (keeping the higher score) and drops
anything already in `applied_log.csv`.

---

## The 10 failure modes, and how this defends against each
1. **LinkedIn/Indeed blocking** → never touched; ATS + aggregator APIs only.
2. **Fabricated apply links** → only API-returned URLs are emitted; **no-link rows
   are dropped** (verified: 0 blank links in output).
3. **Big enterprises expose no clean ATS** → Workday attempt + aggregator
   name-fallback so seeds still surface.
4. **Wrong slug guess** → multiple variants tried; only a 200 + non-empty jobs
   list counts as resolved, else `ats_unknown`.
5. **Flooded with senior roles** → seniority down-ranking.
6. **German-only roles** → `english_ok` flag, kept but marked.
7. **Duplicates across sources** → dedupe key + applied-log drop.
8. **Rate-limit bans** → sleep between calls + raw responses cached to `/cache`.
9. **Stale listings** → posting date captured; `stale` flag over 30 days.
10. **"AI" title but a sales role** → requires skill overlap, not just a title hit.

---

## Known limitation — Workday
Workday hosts each employer at `{tenant}.{wdN}.myworkdayjobs.com/{site}`. There is
**no reliable public way to discover a company's tenant+site from just its name**,
so the Workday adapter only fires for companies explicitly mapped in
`config.WORKDAY_TENANTS`. Everything else correctly falls through to the
aggregator name-fallback — which is exactly what failure-mode #3 anticipates for
large enterprises. To enable Workday for a specific company, add its tenant/site
to that map (the shape is documented inline).

In practice most of the seed list (Unilever, P&G, Shell, Google, Amazon, …) are
large enterprises on bespoke/Workday portals and resolve to `ats_unknown`; they're
picked up by the aggregators when they post to Arbeitnow/Remotive/Adzuna. Adding
Adzuna keys noticeably widens enterprise coverage.

---

## Scheduling (Windows) — set up AFTER a clean manual run

Not created automatically (per my approval rule — run it clean by hand first).
`run_scheduled.bat` is the wrapper the task should call (it uses `.venv` if present
and appends to `run.log`). To register a daily 4:00 AM task:

```bat
schtasks /Create /TN "JobScraper-Daily" /TR "\"C:\Users\noura\projects\Job Scraper\run_scheduled.bat\"" /SC DAILY /ST 04:00 /F
```

If 4:00 collides with a god-mode slot, use `/ST 04:30` instead.

Inspect / edit / remove later:
```bat
schtasks /Query  /TN "JobScraper-Daily" /V /FO LIST
schtasks /Delete /TN "JobScraper-Daily" /F
```

---

## Project layout
```
run.py              orchestrator / CLI entry point
config.py           titles, skills, scoring weights, endpoints, tunables
requirements.txt
run_scheduled.bat   wrapper for the Windows Scheduled Task
.env.example        Adzuna keys template (copy to .env)
jobscraper/
  cv.py             optional CV parsing + skill merge
  http.py           cached, rate-limited HTTP (keys never logged)
  model.py          the normalized Job record
  resolve.py        seed-company -> ATS resolution + slug variants
  sources/          greenhouse, lever, ashby, workday, aggregators
  matching.py       title fuzzy-match, skill gate, scoring, flags
  dedupe.py         cross-source + applied-log dedupe
  output.py         CSV writers + rich console table + summary
```
