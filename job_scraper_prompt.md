# Job Scraper — build prompt (paste into Claude Code from inside the `job scraper` folder)

You are my senior Python engineer. Build a job-hunt aggregator CLI that finds
AI/ML roles matching my CV and outputs a ranked spreadsheet with a DIRECT
APPLY LINK per role, so I can apply fast. I am a 2026 CS grad targeting
AI/ML/NLP roles, open to Germany/EU + remote.

=== INPUTS (all in this folder) ===
- seed_companies.txt : company names I provide (one per line)
- my_cv.(pdf|docx|txt) : read it, extract my skills/keywords automatically
- target_titles = ["ai engineer","machine learning engineer","data scientist",
  "ai automation engineer","generative ai engineer","agentic ai developer",
  "agentic ai engineer"]
- my core skills = Python, FastAPI, NLP, LLMs/agents, ML stack, Next.js,
  Oracle SQL, document-generation, security (IDOR-class). Junior/mid level.
- applied_log.csv : roles I've already applied to (create if missing; dedupe against it)

=== SOURCES — official/free APIs ONLY. Do NOT scrape LinkedIn or Indeed
(they ban scrapers and it violates ToS). ===
A) For each seed company, resolve its careers feed in this order and stop at the
   first that returns jobs:
   1. Greenhouse: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs
   2. Lever:      https://api.lever.co/v0/postings/{slug}?mode=json
   3. Ashby:      https://api.ashbyhq.com/posting-api/job-board/{slug}
   4. Workday:    many large firms use {tenant}.wdN.myworkdayjobs.com — attempt
      the public cxs JSON endpoint if a tenant/site can be found.
   5. FALLBACK (important — most big enterprises won't expose any of the above):
      query the aggregator APIs in (B) filtered by the company NAME + target
      titles, so the company's roles still surface with real apply links.
   Try a few slug variants per company (lowercase, no spaces, no punctuation,
   with/without "inc"/"group"). Log which source each company resolved to.
B) Discovery (find MORE companies hiring the 7 titles) AND the fallback for (A):
   - Arbeitnow (free, no key, Germany/EU): https://www.arbeitnow.com/api/job-board-api
   - Adzuna (free app_id+app_key; query country 'de' for Germany + 'gb','us')
   - Remotive (remote): https://remotive.com/api/remote-jobs

=== MATCHING ===
- Keep a role if its title fuzzy-matches one of the 7 AND its text overlaps my
  must-have skills (Python + at least one of: ML, NLP, LLM/agents, FastAPI).
- Score 0-100: title match + skill overlap + seniority fit. Down-rank
  senior/staff/lead/principal and "5+ years required".
- Flag each role english_ok = true/false (mark German-required roles; don't drop).
- Dedupe by (company+title+location); drop anything already in applied_log.csv.

=== OUTPUT ===
- jobs_YYYY-MM-DD.csv AND a stable latest.csv I can always open, PLUS a pretty
  console table:
  rank | company | title | location | source | match_score | english_ok | APPLY_LINK
- Sorted by match_score desc so I apply top-down.
- Print summary: N roles found, M new companies discovered, K seed companies
  that resolved vs ats_unknown.

=== SCHEDULING (Windows) — set up AFTER it runs clean manually ===
- Create a Windows Scheduled Task: daily at 4:00 AM (after the 11 PM Nabta
  builder and 2 AM Job 1 builder). If 4:00 collides with a god-mode slot, use 4:30.
- It runs `python run.py` in this folder and writes jobs_YYYY-MM-DD.csv,
  latest.csv, and run.log.
- Give me the exact schtasks command (or the .bat) you used so I can see/edit it.

=== RULES ===
- Official APIs only. No LinkedIn/Indeed scraping, no headless-browser evasion.
- NEVER invent an apply URL — emit only links returned by an API. No-link rows
  are dropped. If a company can't be resolved anywhere, log it "ats_unknown".
- Respect rate limits (sleep between calls); cache raw responses to /cache so
  re-runs are cheap and don't re-hit the APIs.
- API keys live in a .env I create (gitignored) — never hardcode, never log them.
- Runnable end-to-end via `python run.py`. Include a requirements.txt.

=== 10 WAYS THIS FAILS + MITIGATE (defend against each) ===
1.  LinkedIn/Indeed blocking -> don't use them; ATS + aggregator APIs only.
2.  Fabricated apply links -> emit only API-returned URLs; drop no-link rows.
3.  Big enterprises expose no clean ATS -> Workday attempt + aggregator fallback
    by company name, so seed companies still surface.
4.  Wrong slug guess -> try variants, verify 200 + jobs, else ats_unknown.
5.  Flooded with senior roles -> seniority down-ranking + filter.
6.  German-only roles I can't do -> english_ok flag, keep but mark.
7.  Duplicates across sources -> dedupe key + applied_log.
8.  Rate-limit bans -> sleep + cache raw responses.
9.  Stale/filled listings -> include posting date; flag older than 30 days.
10. Title says "AI" but it's a sales/marketing role -> require skill overlap,
    not just a title match.

Start by reading my_cv + seed_companies.txt, then list which seed companies
resolve to which source (Greenhouse/Lever/Ashby/Workday/aggregator-fallback)
before pulling any roles.
