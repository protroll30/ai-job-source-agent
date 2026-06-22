# AI Job Source Agent — Architecture

## Core abstraction: a 3-stage enrichment pipeline

One record flows through three transformers, accumulating fields. Each stage has a single clear contract: `record in → record out + status`. A failure in one stage still emits a partial result.

```
LinkedIn URL ──▶ [Stage 1: Source]    ──▶ company name + website
                       │
website URL  ──▶ [Stage 2: Discovery] ──▶ career page URL
                       │
career URL   ──▶ [Stage 3: Extraction] ─▶ one open position URL
                       │
                       ▼
            company, career_url, position_url   (CSV / stdout)
```

### Data model

A single `JobLead` (pydantic) travels through the pipeline carrying provenance alongside values:

```
JobLead:
  source_url, company_name, company_website,
  career_url, position_url,
  stage_status: {source, discovery, extraction}   # ok | partial | failed
  method: {discovery: "heuristic|llm|search", extraction: "ats_api|dom|llm"}
  confidence: float
  error: str | None
```

`method` + `confidence` turn a scraper into something triageable and trustworthy.

---

## Stage strategies: cheap → expensive escalation

Try deterministic/free methods first; escalate to browser/LLM only when ambiguous. This controls cost and latency while staying robust.

### Stage 1 — LinkedIn source (pluggable adapter)

Interface `LinkedInSource` with multiple implementations:
- **API adapter** — Proxycurl / Bright Data / Apify (LinkedIn blocks naive scraping)
- **FixtureSource** — for tests, never burns credits or hits the network

Note the likely two-hop reality: a job listing often doesn't show the company website — listing → company page → website. Encapsulate that inside the adapter.

### Stage 2 — Career page discovery

1. **Heuristic link match** — fetch homepage, scan anchors for `careers|jobs|join|work-with-us|life-at` in text/href; probe common paths (`/careers`, `/jobs`).
2. **Sitemap / robots.txt parse**.
3. **LLM semantic match** — when heuristics are ambiguous, hand Claude the extracted link list and let it pick (handles odd phrasing, non-English, "We're hiring").
4. **Fallback search** (per CLAUDE.md): search API `site:domain "careers" OR "jobs"`.

### Stage 3 — Open position extraction

- **ATS detection first** — most companies use Greenhouse, Lever, Ashby, Workday, SmartRecruiters, or Recruitee. Several expose **public JSON APIs** (e.g. `boards-api.greenhouse.io`, `api.lever.co/v0/postings`, Ashby board API). Detect the ATS → hit the JSON endpoint → get a real requisition URL with zero scraping fragility.
- **Fallback for custom career pages**: render with Playwright, collect candidate job links, filter placeholders/generic registration forms, optionally confirm via LLM "is this a real requisition URL," pick one.

---

## Cross-cutting concerns

- **Orchestrator**: bounded async concurrency (asyncio + semaphore) with per-domain rate limiting.
- **Strict 30s per-page timeout** + "log precise exception, continue to next record" (CLAUDE.md constraints).
- **Config-driven**: API keys, concurrency, timeouts, output path via env/YAML.
- **Structured logging** + per-stage funnel summary at the end (how many leads survived each stage).

---

## Project structure

```
src/
  main.py              # CLI + orchestration entry point
  config.py
  models.py            # JobLead, StageResult
  pipeline.py          # concurrency, checkpoints, error policy
  sources/
    linkedin/
      base.py          # LinkedInSource interface
      api_adapter.py   # Proxycurl / Bright Data / Apify
      fixture_adapter.py
  discovery/
    career_finder.py   # heuristic + LLM + search fallback
    ats_detector.py    # identify which ATS the company uses
  extraction/
    position_finder.py
    ats_clients.py     # Greenhouse, Lever, Ashby JSON API clients
  agent/
    browser.py         # Playwright session management
    llm.py             # Claude API helpers
  output/
    writer.py          # CSV / stdout serializer
  utils/
    cache.py           # disk cache keyed by URL
    rate_limit.py
    logging.py
tests/
  fixtures/            # sample LinkedIn pages, career pages, ATS responses
  test_source.py
  test_discovery.py
  test_extraction.py
```

Stack: Python, Playwright, httpx + selectolax/BeautifulSoup, pydantic, Claude API, pytest, black/ruff.

---

## "Above and beyond" additions

Worth doing (high value, low cost):
- **ATS-aware extraction via public JSON APIs** — the single biggest robustness win; no DOM scraping needed for the majority of tech companies.
- **Confidence + method provenance** on every output field — makes results triageable.
- **Graceful partial results** — emit company + career page even when no open position is found, rather than dropping the row.
- **Disk cache** keyed by URL — faster dev loops, politer to targets, cheaper LLM usage.
- **Resumable checkpoint** — re-running skips already-completed records.
- **URL validation** — confirm the position URL returns 200 before emitting.

Deliberately skipped (over-engineering for a take-home): queue/worker service, database, web UI, distributed crawling, ML ranking.

---

## Build order

1. `JobLead` model + CSV writer + CLI skeleton (end-to-end on a hardcoded record)
2. Stage 2 + 3 with heuristics & ATS clients (testable without LinkedIn)
3. Stage 1 LinkedIn adapter + fixture adapter
4. Async orchestration, caching, checkpointing
5. LLM escalation paths + confidence scoring
6. Tests, funnel summary, polish

This sequence gets a working end-to-end skeleton fastest, then hardens each stage.
