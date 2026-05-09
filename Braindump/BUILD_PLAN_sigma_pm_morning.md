# BUILD PLAN — sigma-pm-morning

**Implementation plan for the daily PM morning brief defined in `PRD_sigma_pm_morning.md`**

| Field | Value |
|---|---|
| Version | 0.1 |
| Author | Syafiq M. Zin (with Claude as Chief of Staff) |
| Date | 2026-05-08 |
| Status | Ready to build (Phase 1) |
| Related | `PRD_sigma_pm_morning.md`, `DEPLOYMENT_HANDOVER.md`, `BAYSIX_BUILD_PLAN_v4.md` |

---

## 0. Build Philosophy

Three rules for this build:

1. **Ship MVP in Week 1.** A daily ritual that doesn't exist for 6 weeks while you build infra dies before it starts. The first version runs as a single Python CLI command outputting one HTML file. Nothing more. Polish later.
2. **No Cloud Run dependency for Phase 1–3.** The deployment is blocked (see `DEPLOYMENT_HANDOVER.md`). Don't gate the brief on it. Local script first, automation later.
3. **One critical artifact per session.** Pro plan rate-limits are real. Each work session ships one tangible thing — section generator, data fetcher, template, eval — not exploratory wandering.

---

## 1. Repo Layout

New project lives at `sigma-brain/workspace/sigma-pm-morning/`. Self-contained for Phase 1–3. Promotes into `sigma-research` backend in Phase 4.

```
sigma-brain/workspace/sigma-pm-morning/
├── README.md
├── pyproject.toml                    # uv-managed project
├── .env.example
├── .env                              # gitignored
├── pm_morning/
│   ├── __init__.py
│   ├── cli.py                        # entry point: `pm-morning build`
│   ├── config.py                     # load .env, constants
│   │
│   ├── data/                         # data fetchers
│   │   ├── __init__.py
│   │   ├── fred.py                   # FRED macro data (reuse sigma-quant logic)
│   │   ├── yahoo.py                  # Yahoo Finance ETF prices
│   │   ├── bursa.py                  # Bursa Malaysia scraping
│   │   ├── flows.py                  # Foreign net flows parser
│   │   ├── calendar.py               # Economic calendar
│   │   └── cache.py                  # Local cache layer (SQLite)
│   │
│   ├── sections/                     # one module per brief section
│   │   ├── __init__.py
│   │   ├── s_minus1_dalio_lens.py
│   │   ├── s0_regime_line.py
│   │   ├── s1_overnight_wrap.py
│   │   ├── s2_asia_open.py
│   │   ├── s3_malaysia_today.py
│   │   ├── s4_deep_dive.py           # day-of-week rotation
│   │   ├── s5_calendar.py
│   │   ├── s6_action_prompts.py
│   │   ├── s7_desk_conviction.py     # stub — human writes
│   │   ├── s8_shadow_portfolio.py
│   │   └── s9_mechanics_drill.py     # weekly (Friday only)
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py                 # Anthropic API wrapper
│   │   ├── sonnet.py                 # Sonnet 4.6 calls
│   │   └── opus.py                   # Opus 4.7 calls
│   │
│   ├── portfolio/
│   │   ├── __init__.py
│   │   ├── universe.py               # ETF universe definition
│   │   ├── nav.py                    # Daily NAV computation
│   │   ├── rebalance.py              # Monthly rebalance logic
│   │   ├── attribution.py            # P&L attribution
│   │   └── persistence.py            # SQLite schema + queries
│   │
│   ├── render/
│   │   ├── __init__.py
│   │   ├── html.py                   # Jinja2 template render
│   │   ├── pdf.py                    # WeasyPrint render (Phase 4)
│   │   └── templates/
│   │       ├── brief.html.j2
│   │       └── partials/
│   │           ├── section_*.html.j2
│   │           └── styles.css
│   │
│   └── state/                        # persisted state
│       ├── dalio_lens_current.json   # active weekly Dalio view
│       ├── deep_dive_rotation.json   # which Tuesday ETF next
│       └── portfolio.db              # SQLite for shadow book
│
├── prompts/                          # LLM prompts (versioned, reviewable)
│   ├── s_minus1_dalio_lens.md
│   ├── s0_regime_line.md
│   ├── s1_overnight_wrap.md
│   ├── s2_asia_open.md
│   ├── s3_malaysia_today.md
│   ├── s4_deep_dive_mon.md
│   ├── s4_deep_dive_tue.md
│   ├── s4_deep_dive_wed.md
│   ├── s4_deep_dive_thu.md
│   ├── s4_deep_dive_fri.md
│   ├── s6_action_prompts.md
│   └── s9_mechanics_drill.md
│
├── outputs/                          # generated briefs (gitignored)
│   └── YYYY-MM-DD/
│       ├── brief.html
│       ├── brief.pdf                 # Phase 4
│       └── data_snapshot.json
│
└── tests/
    ├── test_data_fetchers.py
    ├── test_sections.py
    ├── test_portfolio.py
    └── fixtures/
```

---

## 2. Tech Stack

| Layer | Tool | Why |
|---|---|---|
| Python project | `uv` | Fast, reproducible. You're already on it for sigma-research. |
| LLM | Anthropic SDK (`anthropic`) | Sonnet 4.6 + Opus 4.7 only |
| Data — macro | FRED API via `fredapi` | Reused from sigma-quant |
| Data — ETF prices | `yfinance` | Free, sufficient for daily close |
| Data — Bursa | `httpx` + `beautifulsoup4` | Scrape Bursa Malaysia + Maybank2u |
| Data — calendar | `investpy` or scrape Forex Factory | Economic calendar |
| Cache | SQLite via `sqlite3` stdlib | Zero-deps, single file |
| HTML render | `Jinja2` | Standard, fast |
| PDF render | `weasyprint` | Phase 4 only |
| Charts | `plotly` (HTML) → static PNG via `kaleido` (PDF) | Reuses sigma-quant stack |
| CLI | `typer` | Clean CLI ergonomics |
| Scheduling | `cron` (Phase 4: Cloudflare Cron Triggers) | Simple |
| Tests | `pytest` | Standard |

---

## 3. Phase 1 — Local MVP (Week 1–2)

**Goal: a single command produces a readable HTML brief with Sections 0, 1, 3, 5 every morning by Friday of Week 2.**

### Phase 1 deliverables

- [x] PRD signed off (this is the line that's already done)
- [ ] Project scaffold (`uv init`, repo layout above)
- [ ] Anthropic API integration tested (one Sonnet call returning valid JSON)
- [ ] Data fetchers: Yahoo Finance ETF close, FRED macro, Bursa scrape MVP
- [ ] Section generators for 0, 1, 3, 5
- [ ] HTML template renders all four sections
- [ ] CLI command `pm-morning build` runs end-to-end in <60s
- [ ] One full week of generated briefs (Mon–Fri)

### Phase 1 task breakdown

#### Day 1 — Scaffold + LLM smoke test
1. Create `sigma-brain/workspace/sigma-pm-morning/`
2. `uv init`, add deps: `anthropic`, `httpx`, `pyyaml`, `jinja2`, `typer`, `python-dotenv`, `yfinance`, `fredapi`, `beautifulsoup4`, `pytest`
3. Create `pm_morning/llm/client.py` — Anthropic SDK wrapper, both Sonnet 4.6 and Opus 4.7
4. Create `.env.example` with `ANTHROPIC_API_KEY`, `FRED_API_KEY`
5. Smoke test: `python -c "from pm_morning.llm.client import sonnet; print(sonnet('hi'))"`

#### Day 2 — Data fetchers (Yahoo + FRED)
1. `pm_morning/data/yahoo.py` — fetch close + 1d/5d/MTD/YTD return for any ticker list
2. `pm_morning/data/fred.py` — fetch any FRED series with date range
3. `pm_morning/data/cache.py` — SQLite cache, key = (source, ticker, date), TTL 12h
4. Tests: pytest for both fetchers with VCR fixtures

#### Day 3 — Section 1 (Overnight Wrap)
1. Build the fixed asset table data structure
2. `pm_morning/sections/s1_overnight_wrap.py` — fetches data, formats, calls Sonnet for the "why" sentence
3. Prompt: `prompts/s1_overnight_wrap.md` — versioned, reviewable
4. Output: dict with `table_rows`, `commentary`, `ts`
5. Test on 3 sample days, eyeball output

#### Day 4 — Section 5 (Calendar)
1. `pm_morning/data/calendar.py` — scrape Forex Factory or use `investpy`
2. `pm_morning/sections/s5_calendar.py` — filter to MYT today, format as 5-line summary
3. Sonnet call to compress to 5 lines max with MYT timestamps
4. Test

#### Day 5 — Section 0 (Regime Line) + Section 3 (Malaysia)
1. Section 0 reads outputs of Sections 1 + 2 + 3, synthesises one-line tilt
2. Section 3: Bursa scraping starts. KLCI close, top 5 movers, foreign flows.
3. Bursa scrape: hit `https://www.bursamalaysia.com/market_information/equities_prices` with httpx, parse with bs4. Cache aggressively.
4. Foreign flows: Bursa publishes daily PDF — parse with `pypdf` or scrape Maybank2u summary.

#### Day 6 — HTML render + CLI
1. Jinja2 template `brief.html.j2` with section partials
2. Inline CSS (no external deps for portability)
3. `pm_morning/cli.py` — `typer` app with `build` command
4. Run end-to-end: `pm-morning build --date 2026-05-08`
5. Output: `outputs/2026-05-08/brief.html`

#### Day 7 — Eat the dogfood
1. Generate brief Mon, Tue, Wed, Thu, Fri of Week 2
2. Read each one at 7:00am MYT
3. Note what's missing, what's broken, what's noise
4. Log issues in `BUILD_PLAN_sigma_pm_morning.md` as a "Phase 1 issues" section

### Phase 1 acceptance criteria
- `pm-morning build` runs in <90s on local
- Output HTML is readable in 8 minutes
- Sections 0, 1, 3, 5 populate from real data daily for 5 trading days
- No manual editing required for the brief to be useful
- Sonnet 4.6 cost <$0.10/day measured

---

## 4. Phase 2 — Full sections + Opus (Week 3–4)

**Goal: brief is feature-complete by end of Week 4 except shadow portfolio and automation.**

### Phase 2 deliverables
- [ ] Section −1 (Dalio Lens) with weekly persistence
- [ ] Section 2 (Asia Open)
- [ ] Section 4 (Rotating Deep Dive) with day-of-week routing + Opus 4.7
- [ ] Section 6 (Action Prompts) referencing Dalio quadrant + portfolio state
- [ ] Section 7 (Desk Conviction) stub with edit interface
- [ ] All 5 deep-dive prompts written and tested

### Phase 2 task breakdown

#### Week 3, Day 1–2 — Section −1 (Dalio Lens)
1. State file: `state/dalio_lens_current.json` schema:
   ```json
   {
     "week_of": "2026-05-04",
     "quadrant": "↑G↓I",
     "quadrant_rationale": "...",
     "short_cycle": "mid expansion",
     "long_cycle": "late long cycle, debt overhang",
     "five_forces": {
       "debt": "...", "internal_conflict": "...", "external_conflict": "...",
       "nature": "...", "technology": "..."
     },
     "historical_analog": "1995–96",
     "change_my_mind_triggers": [
       {"trigger": "10Y > 5%", "if_hit": "flip to ↓G↑I"},
       {"trigger": "Brent > $100", "if_hit": "..."}
     ],
     "last_reviewed": "2026-05-08T07:15:00+08:00"
   }
   ```
2. `pm_morning/sections/s_minus1_dalio_lens.py`:
   - `get_active_lens()` — read JSON
   - `propose_weekly_refresh()` — Opus 4.7 call with prior week + this week's data, returns proposed update
   - `commit_lens(json)` — write new JSON
3. CLI: `pm-morning dalio-refresh` runs Mondays
4. Daily check: brief reads active lens, displays at top, no LLM call needed

#### Week 3, Day 3 — Section 2 (Asia Open)
1. Yahoo fetch for: EWJ, EWY, MCHI, FXI, EWT, INDA, EWS, EWM, ASEA, VWO
2. Compute regional ETFs' overnight + premium-discount where data available
3. PBoC fixing — scrape `http://www.pbc.gov.cn` daily fixing table
4. Sonnet 4.6 commentary: 3 sentences max

#### Week 3, Day 4–5 — Section 4 (Rotating Deep Dive)
1. Day-of-week router in `s4_deep_dive.py`:
   ```python
   ROUTER = {
       0: "mon_etf_flows",      # Monday
       1: "tue_etf_dissect",    # Tuesday
       2: "wed_rotation_signal",
       3: "thu_thematic",
       4: "fri_malaysia_asean",
   }
   ```
2. State: `state/deep_dive_rotation.json` — tracks which ETF gets dissected next Tuesday (cycles through universe), which thematic on Thursday
3. Each day's prompt is its own file in `prompts/s4_deep_dive_*.md`
4. Opus 4.7 call with ~8K tokens of context (data tables, prior week's view, news headlines)
5. Output: 3 paragraphs + 1–2 plotly charts saved as static PNG

#### Week 4, Day 1 — Section 6 (Action Prompts)
1. Inputs: Dalio Lens active state, today's data, shadow portfolio current positions
2. Sonnet 4.6 prompt forces output as 3–5 trigger-based one-liners
3. Format check: each line must contain a numeric trigger AND an ETF action

#### Week 4, Day 2 — Section 7 (Desk Conviction)
1. Sonnet drafts a candidate one-line conviction
2. CLI shows the draft, prompts you to type final version
3. Final version persists in brief; draft is logged for self-eval comparison

#### Week 4, Day 3–4 — Integration + dogfood
1. All 11 sections wired together
2. Run for 5 days, fix what breaks
3. Tighten read time to <12 min

#### Week 4, Day 5 — Eval rubric v1
1. Self-score weekly: regime accuracy, action prompt utility, deep-dive insightfulness, time-to-read, ETF fluency gain
2. Save in `eval/week_NN_score.json`

### Phase 2 acceptance criteria
- All 11 sections present and populated
- Dalio Lens persists across days, refreshes weekly
- Deep Dive rotates correctly Mon–Fri
- Brief read time still ≤12 min
- Total cost <$1/day measured

---

## 5. Phase 3 — Shadow Portfolio (Week 5–7)

**Goal: real paper-traded book with daily NAV and weekly review by end of Week 7.**

### Phase 3 deliverables
- [ ] ETF universe loaded as YAML
- [ ] SQLite schema for positions, NAVs, transactions
- [ ] Daily NAV computation
- [ ] Initial portfolio construction (Day 0 capital allocation)
- [ ] Weekly rebalance logic (signals + drift)
- [ ] Section 8 fully populated
- [ ] Attribution + factor exposure reports

### Phase 3 task breakdown

#### Week 5, Day 1 — Universe + schema
1. `pm_morning/portfolio/universe.yaml`:
   ```yaml
   us_broad:
     - {ticker: SPY, name: "SPDR S&P 500", asset_class: equity, region: US}
     - {ticker: QQQ, name: "Invesco QQQ", asset_class: equity, region: US}
     ...
   us_sectors: [...]
   themes: [...]
   regional: [...]
   bonds: [...]
   commodities: [...]
   fx_vol: [...]
   ```
2. SQLite schema in `portfolio/persistence.py`:
   ```sql
   CREATE TABLE positions (
     date DATE, ticker TEXT, shares REAL, cost_basis REAL,
     PRIMARY KEY (date, ticker)
   );
   CREATE TABLE nav_history (
     date DATE PRIMARY KEY, nav REAL, cash REAL, total_value REAL,
     daily_return REAL
   );
   CREATE TABLE transactions (
     id INTEGER PRIMARY KEY, date DATE, ticker TEXT, action TEXT,
     shares REAL, price REAL, rationale TEXT
   );
   CREATE TABLE rebalance_log (
     id INTEGER PRIMARY KEY, date DATE, type TEXT, notes TEXT
   );
   ```

#### Week 5, Day 2 — Day 0 portfolio construction
1. Starting capital: $100,000 USD (paper)
2. Initial allocation: tactical sector + regional rotation, 10 positions
3. Initial weights based on current Dalio quadrant + your conviction (you decide)
4. Logged with rationale

#### Week 5, Day 3 — Daily NAV
1. Fetch close prices for all held tickers
2. Compute mark-to-market value
3. Record daily NAV, daily return, cumulative return
4. Persist
5. Run as part of `pm-morning build` automatically

#### Week 6 — Rebalance logic
1. Weekly signal review (Friday):
   - Sector momentum (4-week vs 13-week return)
   - Factor tilts vs benchmark
   - Drift check (any position >18% or <2%)
2. Monthly rebalance (first trading day of month):
   - Apply signal-based reweighting
   - Capped trades (max 25% turnover/month)
   - Log every rebalance with rationale
3. Constraints enforced in code:
   - 8–15 positions
   - Max 15% single ETF
   - Max 50% single sector / region
   - Cash 0–20%
   - No leverage

#### Week 7 — Attribution + exposure reports
1. Sector attribution (Brinson)
2. Factor exposures via regression vs Fama-French 5-factor (free CSV from Kenneth French data lib)
3. Beta to ACWI, beta to AGG
4. Sharpe, Sortino, max drawdown
5. Plot in Section 8 of brief
6. Weekly summary persisted in `outputs/portfolio_review_YYYY-WW.md`

### Phase 3 acceptance criteria
- Shadow portfolio runs daily without manual intervention
- All metrics computed and visible in Section 8
- Weekly review fires every Friday
- Monthly rebalance logged with rationale
- Portfolio NAV graph renders in HTML brief

---

## 6. Phase 4 — Automation (Week 8–10)

**Goal: zero-touch daily delivery. Brief lands in inbox at 6:55am MYT, dashboard live online.**

### Phase 4 prerequisites
- `sigma-research` Cloud Run deployment unblocked. See `DEPLOYMENT_HANDOVER.md`. **If still blocked at start of Phase 4, defer this phase and push automation to Phase 5.** Phase 1–3 brief is fully functional locally.

### Phase 4 deliverables
- [ ] Brief generation moved into `sigma-research` FastAPI backend
- [ ] New endpoints under `/pm-morning/*`
- [ ] PDF rendering pipeline via WeasyPrint
- [ ] Email delivery via SendGrid
- [ ] Cloudflare Cron at 22:30 UTC (6:30am MYT)
- [ ] HTML dashboard at `sigma-quant.pages.dev/pm-morning`

### Phase 4 task breakdown

#### Week 8 — Backend endpoints
1. New router `app/routers/pm_morning.py` in sigma-research:
   - `POST /pm-morning/build` — triggers full brief
   - `GET /pm-morning/today` — returns latest brief HTML
   - `GET /pm-morning/portfolio` — current shadow portfolio state
   - `POST /pm-morning/dalio-refresh` — weekly lens refresh
2. Move pm_morning code from local repo into sigma-research as `app/services/pm_morning/`
3. Tests still run

#### Week 9 — PDF + email
1. WeasyPrint render of HTML to PDF
2. SendGrid integration: send PDF attachment to syafiqmohdzin3@gmail.com
3. Subject line: `[PM Brief] YYYY-MM-DD — [Quadrant] [One-line tilt]`
4. Test delivery 5 days

#### Week 10 — Scheduling + dashboard
1. Cloudflare Cron Trigger at 22:30 UTC weekdays
2. Calls `https://sigma-research.../pm-morning/build` with auth
3. Frontend: extend sigma-quant Pages with `/pm-morning` route
4. Server-side fetch of latest brief HTML; render in iframe or inline
5. Add a "Today" / "Archive" toggle, archive lists last 30 briefs

### Phase 4 acceptance criteria
- Brief delivered to inbox 6:55am MYT every weekday
- Dashboard renders live within 30s of trigger
- Failure alerting if cron fails (PagerDuty-lite via email)
- Archive of last 30 briefs accessible via dashboard

---

## 7. Phase 5 — Mechanics drill + polish (Month 3+)

**Goal: spaced repetition of ETF mechanics, brief eval discipline, quarterly review.**

### Phase 5 deliverables
- [ ] Section 9 mechanics drill (Friday only)
- [ ] Eval rubric formalised
- [ ] Weekly self-eval workflow
- [ ] Quarterly review template
- [ ] Universe drift monitor

### Phase 5 task breakdown

1. **Mechanics drill rotation** — 12-topic cycle defined in PRD §5 Section 9. State file tracks position. Opus 4.7 generates ~1 page per topic with concept + math + interview Q&A.
2. **Eval rubric v2** — score each brief on 5 dimensions weekly: regime accuracy, action prompt utility, deep-dive insight, time-to-read, fluency gain. Persist in JSON.
3. **Quarterly review** — review eval scores, prune low-utility sections, update universe (de-listings, new launches), refresh prompt library.
4. **Universe drift monitor** — script that flags any tracked ETF with: AUM <$50M, expense ratio change, index methodology change, scheduled closure.

---

## 8. Critical Path & Timeline

| Week | Phase | Output | Hard dependency |
|---|---|---|---|
| 1 | P1 | Scaffold + LLM smoke + first 2 sections | Anthropic API key |
| 2 | P1 | All 4 MVP sections + HTML + CLI | Bursa scrape working |
| 3 | P2 | Dalio Lens + Asia Open + Deep Dive Mon/Tue | Opus 4.7 access |
| 4 | P2 | Action Prompts + Conviction + integration | — |
| 5 | P3 | Universe + schema + NAV | Fama-French CSV |
| 6 | P3 | Rebalance logic | — |
| 7 | P3 | Attribution + exposures + Section 8 live | — |
| 8 | P4 | Backend endpoints in sigma-research | **Cloud Run unblock** |
| 9 | P4 | PDF + email | SendGrid account |
| 10 | P4 | Cron + dashboard | Cloudflare Pages access |
| 12+ | P5 | Mechanics drill, eval, quarterly review | — |

**Critical path:** Phase 1 ships in 2 weeks regardless of what else is broken. Cloud Run blocker only matters at Phase 4. Phase 1–3 brief is fully usable locally.

---

## 9. Setup Commands (Phase 1, Day 1)

Copy-paste runnable. Run from `sigma-brain/workspace/sigma-pm-morning/`.

```bash
# 1. Create project
mkdir -p sigma-brain/workspace/sigma-pm-morning
cd sigma-brain/workspace/sigma-pm-morning

# 2. uv init
uv init --package pm-morning
uv add anthropic httpx pyyaml jinja2 typer python-dotenv yfinance fredapi beautifulsoup4 pypdf plotly kaleido
uv add --dev pytest pytest-vcr ruff mypy

# 3. Folder structure
mkdir -p pm_morning/{data,sections,llm,portfolio,render/templates/partials,state}
mkdir -p prompts outputs tests/fixtures

# 4. Env
cat > .env.example <<EOF
ANTHROPIC_API_KEY=sk-ant-...
FRED_API_KEY=...
EOF
cp .env.example .env
# fill in real keys in .env

# 5. Gitignore
cat > .gitignore <<EOF
.env
.venv/
__pycache__/
*.pyc
outputs/
state/portfolio.db
.pytest_cache/
.mypy_cache/
.ruff_cache/
EOF

# 6. Smoke test scaffold
echo "from anthropic import Anthropic" > pm_morning/llm/client.py
# (then build out properly)

# 7. First commit
git add .
git commit -m "feat(pm-morning): Phase 1 scaffold"
```

---

## 10. Risks (Build-Specific)

| # | Risk | Mitigation |
|---|---|---|
| BR1 | Bursa scrape breaks on first deploy | Use multiple sources (Bursa, Maybank2u, Investing.com) with fallback chain. Cache 12h. |
| BR2 | Pro plan rate limit kills mid-build session | Each session ships ONE concrete artifact. Save state aggressively. Plan sessions around natural completion points. |
| BR3 | Cloud Run blocker delays Phase 4 indefinitely | Phase 1–3 stays local-runnable. Phase 4 is pure automation polish, not feature work. Brief works without it. |
| BR4 | Anthropic API outage | Cache prior-day output; degrade-gracefully with explicit "stale" tag. |
| BR5 | Yahoo Finance rate limit / API change | Add IEX Cloud or Alpha Vantage as backup. Cache aggressively. |
| BR6 | Time zone bugs (MYT vs UTC vs ET) | Use `pendulum` or `zoneinfo` everywhere. Single source of truth: `config.LOCAL_TZ = ZoneInfo("Asia/Kuala_Lumpur")`. Never use naive datetimes. |
| BR7 | LLM hallucinations in financial data | All numeric data is fetched, never generated. LLM only writes commentary on top of structured data tables. Templates enforce this. |
| BR8 | Prompts drift, output quality drops | Prompts versioned in `/prompts`, reviewed weekly. Eval rubric flags quality regressions. |
| BR9 | Shadow portfolio data corrupts | SQLite WAL mode + daily backup of `portfolio.db` to `outputs/backups/`. |
| BR10 | Fama-French CSV download fails | Cache locally; refresh monthly only. |

---

## 11. Definition of Done (per phase)

### Phase 1 DoD
- `pm-morning build` runs cleanly on demand
- Sections 0, 1, 3, 5 generated from real data
- HTML brief is readable in <12 min
- 5 consecutive trading-day briefs generated
- All Phase 1 issues logged

### Phase 2 DoD
- All 11 sections present
- Dalio Lens has been refreshed at least once
- Deep Dive has rotated through Mon–Fri at least once
- Cost ≤$1/day

### Phase 3 DoD
- Shadow portfolio Day 0 constructed with logged rationale
- Daily NAV recorded for ≥10 trading days
- One monthly rebalance executed and logged
- Section 8 renders portfolio metrics in brief

### Phase 4 DoD
- Brief delivered to inbox 6:55am MYT 5 days running
- Dashboard live and refreshing
- Cron fires reliably at 22:30 UTC

### Phase 5 DoD
- 4 mechanics drill topics covered
- 4 weeks of eval scores logged
- One quarterly review completed

---

## 12. Out of Scope (explicit)

Not building these in this project (yet):
- Real-money execution
- Multi-user support
- Real-time intraday updates (brief is once-daily)
- Mobile-native app (PDF email + responsive HTML is enough)
- Backtest engine for strategies (use existing tools if needed)
- News sentiment scoring beyond what LLM does inline
- Trade journaling for the live MT5 book (separate system)

---

## 13. Next Action

**Start Phase 1, Day 1.** Concretely:

1. Open new session focused on Phase 1 scaffold only.
2. Run the setup commands in §9.
3. Confirm Anthropic SDK call returns valid Sonnet 4.6 response.
4. Commit the empty scaffold.
5. End session.

That's the first session. Tomorrow is Day 2 (data fetchers). Don't try to do more in one sitting on Pro plan.

---

**End of Build Plan v0.1.**

*If a Phase 1 issue list grows, update this doc with a `## Phase 1 issues` section before starting Phase 2.*
