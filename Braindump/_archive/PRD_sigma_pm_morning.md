# PRD — sigma-pm-morning

**Daily Morning Briefing for a Simulated Malaysian Fund Manager (with US ETF-Quant Career Pivot)**

| Field | Value |
|---|---|
| Version | 0.1 (Draft for review) |
| Author | Syafiq M. Zin (drafted with Claude as Chief of Staff) |
| Date | 2026-05-08 |
| Status | Draft — ready for build planning |
| Related | `PRD_baysix_ai_hedge_fund_v4.md`, `sigma-daily-macro` skill, `DEPLOYMENT_HANDOVER.md` |

---

## 1. TL;DR

A daily 10-minute morning brief, delivered **7:00am MYT every weekday**, that simulates a Malaysian fund manager's perspective on global macro — with **Malaysia as the home market** and **ETFs as the operational language throughout**.

Two purposes, one product:

1. **Daily discipline** — sharpen macro reasoning, build a structural cycle view, resist daily-noise reactivity.
2. **Career pivot fuel** — build interview-grade ETF fluency over 6 months for US ETF-only Quant Trader / Researcher applications, plus a verifiable shadow-portfolio track record to walk into interviews with.

This is a **distinct product** from `sigma-daily-macro` (which serves pre-NY session XAUUSD trading prep). Different decision-maker, different timing, different scope.

---

## 2. Problem Statement

Existing morning information sources fail in three ways:

- **Sell-side notes** (Maybank IB, CIMB, RHB, Kenanga morning packs) — broad, not decision-tied, no ETF vocabulary, no structural anchor.
- **Bloomberg / Reuters digests** — global but Malaysia-thin, no portfolio-decision framing.
- **DIY scattered consumption** — no compounding skill, no record, no rigour.

The gap: a single daily ritual that compounds **macro discipline + ETF fluency + Malaysia literacy** simultaneously, while producing an interview-ready artifact (shadow portfolio track record).

---

## 3. Goals & Non-Goals

### Goals
- **G1** Deliver a daily 10-min readable brief at 7:00am MYT every weekday.
- **G2** Express every macro view in ETF tickers — ETF as language, not as section.
- **G3** Anchor each brief in a structural cycle view (Dalio Lens) updated weekly.
- **G4** Maintain a paper shadow portfolio of US + global ETFs with verifiable track record.
- **G5** Cover Malaysia as home market without becoming Malaysia-only.
- **G6** Build interview-grade ETF fluency over 6 months (≥24 ETFs deeply dissected).
- **G7** Reuse existing `sigma-quant` + `sigma-research` infra. No greenfield rebuilds.

### Non-Goals
- **NG1** Not for live MT5 / XAUUSD trading prep — that is `sigma-daily-macro`'s job.
- **NG2** Not a comprehensive analyst report. 10-min read is a hard ceiling.
- **NG3** Not an academic ETF curriculum. Curriculum work runs in parallel.
- **NG4** Not Malaysia-only or Bursa-only. Global lens, Malaysia anchor.
- **NG5** Not real-money execution. Shadow portfolio is paper. No order routing.
- **NG6** Not a competitor to Bloomberg. Personal-use tool.

---

## 4. User & Persona

### Primary user
**Syafiq**, simulating a multi-asset Malaysian fund manager.

- **Assumed mandate** — KLCI-tilt benchmark, can hold global ETFs, can hedge FX, multi-asset (equities + bonds + commodities + FX), conservative-aggressive risk band.
- **Career interview targets** — US ETF-only Quant Trader / Researcher roles (firms in the Old Mission / Flow Traders / Jane Street / Astoria / WisdomTree style spectrum).
- **Time budget** — 15 min, 7:00–7:15am MYT, before morning routine.
- **Reading device** — desktop primary (HTML dashboard), phone secondary (PDF email).

### Secondary user
**Claude (Chief of Staff)** — maintains spec, generates deep-dive content, monitors shadow portfolio drift, refreshes Dalio Lens weekly.

---

## 5. Product Structure (Section-by-Section Spec)

The brief has **eleven sections** numbered −1 through 9. Section −1 is the structural anchor at the top.

### Section −1 — The Dalio Lens (structural anchor)

**Purpose:** Anchor every brief in a long-cycle structural view so daily noise doesn't drive tactical reactivity.

**Cadence:** Refreshed weekly (every Monday). Daily check confirms or breaks the view. Most days unchanged — that is the discipline.

**Six elements (one line each):**

1. **Quadrant call** — Growth direction (↑/↓) × Inflation direction (↑/↓). Four boxes:
   - ↑G ↑I → commodities, EM, value, energy → DBC, VWO, XLE, VLUE, GDX
   - ↑G ↓I → stocks (esp. tech/growth) → SPY, QQQ, MTUM, SOXX
   - ↓G ↑I → stagflation hedge → GLD, TIP, DBC, XLE
   - ↓G ↓I → long bonds, defensives, cash → TLT, IEF, XLU, XLP
2. **Short-term debt cycle position** — early / mid / late expansion or contraction.
3. **Long-term debt cycle position** — annual question, anchors interpretation.
4. **Five Forces temperature** — one line each: debt machine; internal conflict (politics, wealth gap, US elections, Malaysia politics); external conflict (US–China, Taiwan, Middle East, ASEAN); acts of nature (climate, disease, food); technology (AI productivity supercycle).
5. **Historical analog** — *"Today's setup most resembles [1971 / 1937 / 2000 / 1994 / 2018 / 2008]. Therefore expect…"*
6. **What would change my mind** — explicit pre-commitment with numeric triggers. Example: *"I flip from ↑G↓I to ↓G↑I if 10Y breaks 5%, oil breaks $100, AND payrolls miss two months running."*

**Output:** Half a page. Updated Mondays, otherwise read-only.

---

### Section 0 — The Regime Line (today's tilt)

**Purpose:** The one-liner the CIO would read if he had 30 seconds.

**Format:** Two sentences max. Risk-on / risk-off / neutral, plus the one thing that moved overnight, plus the implied tilt — all expressed in ETF tickers.

**Example:** *"Risk-off. Nasdaq −2.1%, MOVE +5pts on Powell hawkish surprise. Defensives bid (XLU, XLP outperforming XLK by ~3%). EWM likely opens −1% on EM rotation + MYR weakness. Today's tilt: lean USMV, fade SOXX rallies."*

**Generated by:** Sonnet 4.6.

---

### Section 1 — Overnight Wrap (US + EU close)

**Purpose:** Scannable table of what closed overnight, with ETF tickers in parallel.

**Columns:** Asset / Level / % chg / **ETF expression**.

**Rows (fixed):**
- Equity: S&P 500 (SPY), Nasdaq 100 (QQQ), Russell 2000 (IWM), Stoxx 600 (EZU), FTSE (EWU)
- Rates: UST 10Y (TLT), 2Y (SHY), 2s10s curve (custom)
- FX: DXY (UUP), EURUSD (FXE), USDJPY (FXY inverse), USDCNH, USDMYR
- Commod: Brent (BNO), WTI (USO), CPO (no clean US ETF — track futures), Gold (GLD), Copper (CPER)
- Vol: VIX (VXX as proxy), MOVE

**Plus:** one sentence — *why* did it move?

**Generated by:** Sonnet 4.6.

---

### Section 2 — Asia Open

**Purpose:** Capture overnight-to-now Asian tape via regional ETFs.

**Tracked:**
- Japan EWJ, Korea EWY, China MCHI / FXI, Taiwan EWT, India INDA, Singapore EWS, **Malaysia EWM**, ASEAN ASEA, EM broad VWO
- PBoC USD/CNY fixing
- Notable Asia overnight news

**Twist:** Note premium/discount of EWM specifically — it's how foreign capital prices Malaysia in real time.

**Generated by:** Sonnet 4.6.

---

### Section 3 — Malaysia Today (the differentiated section)

**Purpose:** Everything a Malaysian PM needs that Bloomberg won't give in one place.

**Components:**
- KLCI futures vs prior close, FBM 100, FBM Small Cap
- **Foreign net flows yesterday** — net buy/sell on Bursa, sector breakdown
- Top 5 Bursa movers + actual reason
- Today's local catalysts — results, ex-div, MGS auction, OPR meeting, MPOB palm oil inventory, Bursa announcements
- Sector to watch + numeric trigger (*"O&G if Brent breaks $90; Banks if MGS 10Y rises 5bps"*)
- BNM / MYR pulse — overnight fixing, intraday range, BNM speakers
- Politics & regulatory — government, budget items, regulatory news from PM's office, Bursa Malaysia announcements
- **EWM Watch line** — yesterday flows, premium/discount, top-10 weight changes

**Generated by:** Sonnet 4.6 with Qdrant retrieval over Bursa news corpus.

---

### Section 4 — Rotating Deep Dive (Mon–Fri)

**Purpose:** Genuine depth on one theme per day. Over a week you cover all five core themes without bloating any single brief.

**Cadence:**
| Day | Theme | Output |
|---|---|---|
| Mon | **ETF Flows of the Week** | Largest creations / redemptions across SPY, QQQ, sector ETFs, EM (VWO, EWM). What's smart money saying? |
| Tue | **One ETF Dissected** | Pick one ETF, unpack: index methodology, top-10 holdings, expense ratio, premium/discount history, AUM trend, who owns it. Rotate weekly: SOXX, SMH, EWM, GDX, TLT, XLE, IBIT, KWEB, URA, etc. |
| Wed | **Cross-Asset Rotation Signal** | Sector rotation (XLK vs XLU, XLF vs XLE), factor rotation (MTUM vs USMV vs VLUE), regional (DM vs EM, US vs Asia). Build the signal. |
| Thu | **Thematic Spotlight** | AI infra (SOXX vs SMH vs IGV vs power XLU+VPU), commodities (CPER, URA, PALL, GLD), defense ITA, etc. |
| Fri | **Malaysia + ASEAN through the ETF lens** | EWM / FLM / ASEA flows, vs MCHI / INDA / EEM. How is global capital expressing Malaysia and neighbours? |

**Format:** ~3 paragraphs + 1–2 charts.

**Generated by:** Opus 4.7 (depth matters here).

---

### Section 5 — Today's Calendar (MYT-stamped)

**Purpose:** What hits the tape today.

**Five lines max, time-ordered:**
- Economic data (US NFP, CPI, FOMC, Malaysia trade balance, China PMI, etc.)
- Central bank speakers
- Earnings (Bursa interim results, US after-close, Asia overnight)
- IPOs / listings
- Geopolitical scheduled events (G20, OPEC meetings, ASEAN summits)

**Generated by:** Sonnet 4.6.

---

### Section 6 — PM Action Prompts (the killer section)

**Purpose:** Decision triggers explicitly tied to today's setup AND the Dalio quadrant. Forces pre-commitment so you don't react in panic at 10:30am.

**Format:** 3–5 lines, rule-based, ETF-stated.

**Examples:**
- *"In ↑G↓I quadrant — overweight tilt SPY/QQQ confirmed. Resist urge to fade today's rally."*
- *"If DXY breaks 105.50 → trim SMH 1%, add UUP 1%. EWM puts vs spot."*
- *"If foreign net sells Bursa >RM200m 3 days running → cut EWM exposure, hedge with EEM short."*
- *"Maybank reports Thursday — banks sector reaction setup."*

**Generated by:** Sonnet 4.6 with reference to Dalio Lens quadrant + shadow portfolio state.

---

### Section 7 — Desk Conviction (one line)

**Purpose:** Your house view, owned. This is the line you'd put your name on.

**Format:** One sentence. Regime call + conviction (high/medium/low) + one trade idea.

**Example:** *"High conviction ↑G↓I; tactical OW SOXX, single-name avoid; one-trade: long XLE / short XLU on rate normalization."*

**Generated by:** human (Syafiq) — Claude can suggest, but you write it. This is the one section that requires daily human judgment.

---

### Section 8 — Shadow Portfolio (the artifact)

**Purpose:** The thing you put in front of an interviewer. *"I run a tactical ETF book; here's 6 months of daily NAV, here's my factor exposures, here's why I rotated to XLU on April 12th."*

**Strategy:** Tactical sector + regional rotation.

**Universe:** ~50 ETFs (Appendix A).

**Sizing constraints:**
- 8–15 holdings at any time
- Max 15% single ETF
- Max 50% single sector / region
- Cash 0–20%
- No leverage in shadow book (UCITS-clean)

**Cadence:**
- Daily NAV mark
- Weekly review (signals, drift, breaches)
- Monthly rebalance
- Quarterly attribution + factor exposure report

**Tracked metrics:**
- NAV, daily / weekly / MTD / YTD return
- Sharpe, Sortino, max drawdown
- Beta to ACWI, beta to AGG
- Factor exposures (size, value, momentum, quality, low-vol)
- Sector + regional tilts vs benchmark
- Top contributors / detractors

**Benchmark:** 60/40 ACWI/AGG.

**Persistence:** SQLite or JSON in `sigma-research` backend; daily snapshot in `sigma-brain/workspace/shadow-portfolio/`.

**Generated by:** Opus 4.7 weekly review + Sonnet 4.6 daily NAV update.

---

### Section 9 — ETF Mechanics Drill (weekly)

**Purpose:** Spaced repetition on ETF mechanics. Builds interview fluency.

**Cadence:** One mechanic per week (Friday). Cycle through:

1. Creation / redemption + Authorized Participants
2. Premium / discount and arbitrage
3. NAV calculation & end-of-day pricing
4. Tax efficiency vs mutual funds
5. Synthetic replication (swap-based UCITS)
6. Leveraged / inverse ETF decay
7. Fixed-income ETF basket pricing
8. Index reconstitution & rebalance arbitrage
9. ETF closures, soft / hard closes
10. Securities lending revenue
11. Total return swap structures
12. Active ETF mechanics (semi-transparent)

**Format:** ~1 page per topic. Concept + math + interview-style Q&A.

**Generated by:** Opus 4.7.

---

## 6. ETF Universe (~50)

Full list lives in **Appendix A** below. Summary count by bucket:

| Bucket | Count | Examples |
|---|---|---|
| US Broad / Factor | 8 | SPY, QQQ, IWM, MTUM, USMV, VLUE, QUAL |
| US Sectors (SPDR) | 11 | XLK, XLF, XLE, XLU, XLV, XLP, XLY, XLI, XLB, XLRE, XLC |
| Themes | 6 | SOXX, SMH, IGV, IBIT, ITA, KWEB |
| Regional / Country | 12 | **EWM**, ASEA, MCHI, FXI, EWY, EWJ, INDA, EWS, EWZ, EWG, VEA, VWO |
| Bonds / Rates | 6 | TLT, IEF, SHY, HYG, LQD, EMB |
| Commodities / Real Assets | 8 | GLD, SLV, USO, BNO, CPER, URA, DBA, DBC |
| FX / Vol | 3 | UUP, FXY, VXX |
| **Total** | **~54** | |

UCITS equivalents (for EU / UK reference): VWRL, VUSA, CSPX, EUNL, EIMI, IEMM. Tracked as cross-references, not core universe.

---

## 7. Technical Architecture

### Stack
- **Frontend:** Extend `sigma-quant` Cloudflare Pages with `/pm-morning` route. Reuse existing UI primitives.
- **Backend:** `sigma-research` FastAPI (currently blocked on Cloud Run deployment — see `DEPLOYMENT_HANDOVER.md`). New endpoints under `/pm-morning/*`.
- **Vector store:** Qdrant Cloud `sigma_market` collection (existing) for context retrieval.
- **LLM:** Anthropic API only.
  - Sonnet 4.6 → daily mechanical sections (0, 1, 2, 3, 5, 6).
  - Opus 4.7 → Section 4 (rotating deep dive), Section 8 (weekly portfolio review), Section 9 (mechanics drill), Section −1 (weekly Dalio Lens refresh).
- **Macro data:** FRED API (existing).
- **ETF data:** Yahoo Finance + ETFdb scrape + JustETF scrape (UCITS).
- **Bursa data:** Bursa Malaysia website scrape + Maybank2u markets feed.
- **Foreign flows:** Bursa Malaysia daily flow report (PDF parse).
- **Risk events:** NASA EONET (existing).
- **PDF render:** WeasyPrint or `playwright-pdf`.
- **Email delivery:** SendGrid API or SMTP via Cloudflare Email Workers.
- **Scheduler:** Cloudflare Cron Triggers (6:45am MYT = 22:45 UTC).
- **Shadow portfolio storage:** SQLite in `sigma-research` backend; daily snapshot JSON in `sigma-brain/workspace/shadow-portfolio/`.

### Data flow

```
22:30 UTC (6:30am MYT)
  ├─ Cloudflare Cron triggers /pm-morning/build
  ├─ Backend pulls: FRED data, Yahoo ETF prices, Bursa news, foreign flows, calendar
  ├─ Sonnet 4.6 generates Sections 0,1,2,3,5,6
  ├─ Opus 4.7 generates Section 4 (per day-of-week rotation)
  ├─ Backend computes Section 8 (shadow portfolio NAV)
  ├─ Templates assembled into HTML
  ├─ HTML renders to PDF
22:55 UTC (6:55am MYT)
  ├─ Email sent to syafiqmohdzin3@gmail.com with PDF attachment
  ├─ HTML published at sigma-quant.pages.dev/pm-morning
07:00 MYT
  └─ Read.
```

### Dependencies
- `sigma-research` backend deployment to Cloud Run **must unblock** before automation. Until then, run as local Python script triggered manually.
- Bursa Malaysia data — no clean public API, scraping required. Risk: ToS, breakage. Mitigation: cache + degrade-gracefully.

---

## 8. Model Usage & Cost Projection

| Section | Model | Calls/day | Tokens in | Tokens out | Daily $ est. |
|---|---|---|---|---|---|
| 0 Regime Line | Sonnet 4.6 | 1 | 2,000 | 200 | $0.01 |
| 1 Overnight Wrap | Sonnet 4.6 | 1 | 3,000 | 400 | $0.02 |
| 2 Asia Open | Sonnet 4.6 | 1 | 2,500 | 300 | $0.01 |
| 3 Malaysia Today | Sonnet 4.6 | 1 | 5,000 | 600 | $0.03 |
| 4 Rotating Deep Dive | Opus 4.7 | 1 | 8,000 | 1,500 | $0.30 |
| 5 Calendar | Sonnet 4.6 | 1 | 1,500 | 300 | $0.01 |
| 6 Action Prompts | Sonnet 4.6 | 1 | 3,000 | 400 | $0.02 |
| 7 Desk Conviction | (human) | 0 | — | — | $0 |
| 8 Shadow Portfolio | Sonnet 4.6 daily / Opus weekly | 1+1/wk | mixed | mixed | $0.05 avg |
| 9 ETF Mechanics | Opus 4.7 (Friday only) | 0.2 | 3,000 | 1,500 | $0.06 avg |
| **Total** | — | — | — | — | **~$0.50/day → $11/mo** |

Rounded up for retries, evals, weekly Dalio refresh: **~$15/mo**. Negligible.

---

## 9. Success Metrics

| Metric | Target | How measured |
|---|---|---|
| Delivery rate | ≥95% over 30-day rolling window | Cron logs |
| Read time | ≤12 min average | Self-report (toggle in HTML) |
| Shadow portfolio Sharpe | ≥0.5 over 6 months | Computed nightly |
| Shadow portfolio max DD | ≤15% | Computed nightly |
| ETFs deeply dissected | ≥24 over 6 months | Tuesday rotation log |
| Mechanics topics covered | ≥20 over 6 months | Friday rotation log |
| Subjective interview readiness | "Ready" by month 6 | Weekly self-score 1–10 |
| Brief quality (eval) | ≥4/5 average | Weekly Claude self-eval against rubric |

---

## 10. Risks & Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Cloud Run deployment stays blocked → no automation | High | High | Phase 1 runs as local Python script. Don't gate the brief on infra. |
| R2 | Daily ritual abandoned after 3 weeks | Medium | Critical | Make daily friction near zero — push notification, one-tap PDF, no manual steps. Section 7 is the only human input. |
| R3 | Bursa data scrape breaks | Medium | Medium | Cached fallback + explicit "stale" tag. Manual override path. |
| R4 | Shadow portfolio drifts unattended | Medium | High | Weekly review forced via Friday section + email reminder. |
| R5 | Brief becomes too long → not read | Medium | High | Hard 10-min ceiling. Quarterly trim review. |
| R6 | Dalio Lens becomes cosplay rather than genuine view | Medium | Medium | Force "what would change my mind" with numeric triggers. Track when triggers were hit and whether view actually flipped. |
| R7 | Anthropic API outage | Low | Medium | Fall back to cached prior-day summary with explicit "stale" tag. |
| R8 | Malaysia content too thin → defeats home-market angle | Medium | High | Section 3 is a hard requirement; brief does not ship if Section 3 fails to populate. |
| R9 | ETF universe drifts (de-listings, new launches) | Low | Low | Quarterly universe review. |
| R10 | Cost creep from Opus calls | Low | Low | Monthly cost monitor. Hard cap at $50/mo. |

---

## 11. Build Phases

### Phase 1 — MVP (Week 1–2)
- Local Python script, manual trigger.
- Sections 0, 1, 3, 5 only (mechanical).
- HTML output to local file.
- Sonnet 4.6 only.
- Goal: prove the daily flow works for 5 trading days.

### Phase 2 — Add structural & deep sections (Week 3–4)
- Section −1 Dalio Lens (weekly refresh).
- Section 4 rotating deep dive (Opus 4.7 integration).
- Section 6 Action Prompts.
- Goal: brief feels complete and useful.

### Phase 3 — Shadow portfolio (Week 5–7)
- Section 8 engine — universe definition, sizing rules, daily NAV computation.
- SQLite persistence.
- Weekly review automation.
- Goal: real track record begins.

### Phase 4 — Automation (Week 8–10)
- Cloud Run deployment unblocked (separate workstream).
- Cloudflare Cron scheduling.
- Email delivery via SendGrid.
- PDF rendering pipeline.
- HTML dashboard live at `sigma-quant.pages.dev/pm-morning`.
- Goal: zero-touch daily delivery.

### Phase 5 — Mechanics drill & polish (Month 3+)
- Section 9 ETF Mechanics Drill.
- Brief eval rubric + weekly self-eval.
- Quarterly review process.
- Goal: spaced repetition compounding.

---

## 12. Open Questions

1. **Format priority** — HTML dashboard primary or PDF email primary? (Default: dashboard primary, PDF as archive.)
2. **Shadow portfolio currency base** — USD or MYR? (Default: USD, since target role is US-based.)
3. **UCITS coverage depth** — track or just reference? (Default: reference only for now.)
4. **Bursa data source legality** — scrape acceptable risk vs paid data feed? (Default: scrape with attribution + cache, revisit if breakage.)
5. **Section 7 (Desk Conviction)** — should Claude generate a draft for human edit, or pure blank slate? (Default: Claude drafts, human edits and signs.)
6. **Brief delivery on Malaysian public holidays** — skip or run with reduced scope? (Default: run with reduced scope — global markets still trade.)
7. **Eval rubric** — who defines and reviews? (Default: Claude proposes, Syafiq approves.)

---

## 13. Composition with Existing Products

| Product | Role | Relationship |
|---|---|---|
| `sigma-daily-macro` | Pre-NY trading prep, MT5 / XAUUSD focus | **Independent.** Different time window (pre-NY ~9pm MYT) and different decision-maker (you-the-trader). Both can coexist; brief reads pull no shared state. |
| `sigma-quant` Intelligence Centre | Live deployed dashboard with crypto + macro signals | **Reused infra.** New `/pm-morning` route. Existing UI primitives, FRED + Groq pipes adapted. |
| `sigma-research` FastAPI | Vector retrieval + AI synthesis backend | **Reused.** New endpoints. Deployment unblock is prerequisite for full automation but not for Phase 1. |
| Qdrant `sigma_market` collection | Existing 245-doc embeddings | **Reused.** Add Bursa news + ETF prospectus embeddings over time. |

No replacement of existing products. Pure addition.

---

## Appendix A — Full ETF Universe

### US Broad / Factor (8)
SPY, QQQ, IWM, VTI, MTUM, USMV, VLUE, QUAL

### US Sectors (11)
XLK, XLF, XLE, XLU, XLV, XLP, XLY, XLI, XLB, XLRE, XLC

### Themes (6)
SOXX (semis), SMH (semis), IGV (software), IBIT (Bitcoin), ITA (defense), KWEB (China internet)

### Regional / Country (13)
- **EWM** — iShares MSCI Malaysia (flagship for this brief)
- ASEA — Global X ASEAN 40
- MCHI — iShares MSCI China
- FXI — iShares China Large-Cap
- EWY — iShares MSCI South Korea
- EWJ — iShares MSCI Japan
- INDA — iShares MSCI India
- EWS — iShares MSCI Singapore
- EWT — iShares MSCI Taiwan
- EWZ — iShares MSCI Brazil
- EWG — iShares MSCI Germany
- VEA — Vanguard Developed Markets ex-US
- VWO — Vanguard Emerging Markets

### Bonds / Rates (6)
TLT (long Treasuries), IEF (7–10Y), SHY (1–3Y), HYG (high yield), LQD (IG corporate), EMB (EM USD bonds)

### Commodities / Real Assets (8)
GLD (gold), SLV (silver), USO (WTI), BNO (Brent), CPER (copper), URA (uranium miners), DBA (agriculture), DBC (broad commodity basket)

### FX / Vol (3)
UUP (DXY), FXY (yen), VXX (vol — signal only, not held)

### UCITS reference (5)
VWRL, VUSA, CSPX, EUNL, EIMI — for cross-listing literacy.

**Total: ~54 ETFs.**

---

## Appendix B — Dalio Lens Worksheet Template

```
THE DALIO LENS — Week of [YYYY-MM-DD]

1. QUADRANT
   Growth: ↑ / ↓ (rationale: ____)
   Inflation: ↑ / ↓ (rationale: ____)
   → Quadrant: [↑G↑I / ↑G↓I / ↓G↑I / ↓G↓I]
   → Asset bias: [list ETF tickers]

2. SHORT-TERM DEBT CYCLE
   Position: [early / mid / late expansion / contraction]
   Evidence: ____

3. LONG-TERM DEBT CYCLE
   Position: ____
   (Annual question — refresh Q1 each year)

4. FIVE FORCES (one line each)
   Debt machine: ____
   Internal conflict: ____
   External conflict: ____
   Acts of nature: ____
   Technology: ____

5. HISTORICAL ANALOG
   Closest period: [year]
   Why: ____
   Therefore expect: ____

6. WHAT WOULD CHANGE MY MIND
   Trigger 1: ____ (numeric)
   Trigger 2: ____ (numeric)
   Trigger 3: ____ (numeric)
   If hit: flip from [current quadrant] to [new quadrant]
```

---

## Appendix C — Glossary

- **AP** — Authorized Participant. The institution that creates / redeems ETF units in the primary market.
- **All Weather** — Dalio's risk-parity portfolio designed to perform across all four economic environments.
- **CPO** — Crude Palm Oil. Major Malaysian export commodity. Traded on Bursa Malaysia Derivatives.
- **EWM** — iShares MSCI Malaysia ETF. Single most important ticker in this brief — the bridge between Malaysia and the US ETF market.
- **Foreign net flows** — Daily net buy/sell on Bursa by foreign investors. Critical KLCI sentiment indicator.
- **KLCI** — FTSE Bursa Malaysia KLCI Index. Top 30 Malaysian large-caps.
- **MGS** — Malaysian Government Securities. The local sovereign bond curve.
- **MOVE** — Bond market volatility index, Treasury equivalent of VIX.
- **MPOB** — Malaysian Palm Oil Board. Releases monthly inventory data, market-moving for CPO.
- **OPR** — Overnight Policy Rate. BNM's policy rate.
- **Quadrant (Dalio)** — Growth × Inflation 2×2 matrix used to drive asset allocation tilts.
- **Risk parity** — Portfolio construction allocating by risk contribution rather than capital.
- **Shadow portfolio** — Paper-traded ETF book run for skill-building and interview track record.
- **UCITS** — EU ETF regulatory wrapper. Many US ETFs have UCITS equivalents.

---

**End of PRD v0.1.**

*Next step: review, lock open questions in §12, then move to BUILD_PLAN_sigma_pm_morning.md.*
