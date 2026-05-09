---
name: sigma-pm-morning
description: Build the daily PM Morning Brief — a Malaysian fund manager's perspective on global macro through an ETF lens, with Dalio structural anchor and a shadow portfolio. Trigger on "pm brief", "pm morning", "run pm morning", "morning brief for the fund", or auto-triggered by scheduled task at 6:45am MYT every weekday. This produces a multi-section HTML + PDF brief covering the Dalio Lens, regime call, overnight wrap, Asia open, Malaysia today, rotating deep dive (Mon-Fri), economic calendar, action prompts, desk conviction, shadow portfolio review, and (Fridays) ETF mechanics drill. Output is saved to outputs/pm-morning/YYYY-MM-DD/ and pushed to email.
---

# Sigma PM Morning Brief

This skill builds Syafiq's daily PM Morning Brief. Distinct from `sigma-daily-macro` (which is pre-NY trading prep for the personal MT5 / XAUUSD book). This brief simulates a Malaysian multi-asset fund manager's perspective with two purposes:

1. Daily macro discipline through a structural cycle anchor.
2. Building interview-grade ETF fluency for US ETF-only Quant Trader / Researcher applications.

**Spec reference:** `Braindump/PRD_sigma_pm_morning.md`. Read it once for full context; thereafter follow this skill's procedure.

---

## When to use this skill

- Manual trigger: user asks for "morning brief", "pm brief", "run pm morning", "fund brief", or similar.
- Scheduled trigger: 6:45am MYT every weekday (Mon–Fri) via `mcp__scheduled-tasks__create_scheduled_task`.
- Re-run trigger: if user asks to "rebuild today's brief" or similar — overwrite, don't append.
- Do NOT use for: pre-NY trading prep (use `sigma-daily-macro`), weekend recaps, ad-hoc macro questions.

---

## Critical execution order (Pro plan discipline)

Per `CLAUDE.md`: deliver the critical artifact FIRST in any session. Order:

1. **Must ship:** Sections −1, 0, 1, 3 (Dalio Lens, Regime Line, Overnight Wrap, Malaysia Today)
2. **Should ship:** Sections 4, 6, 8 (Deep Dive, Action Prompts, Shadow Portfolio)
3. **Nice to have:** Sections 2, 5, 7, 9 (Asia Open, Calendar, Desk Conviction, Mechanics Drill on Fridays)

If rate-limited or time-constrained mid-build, ship a partial brief with sections 1–3 above rather than nothing. Mark missing sections explicitly.

---

## File paths (absolute)

**State (persistent across runs):**
- `C:\Users\User\Desktop\sigma-brain\Memory\pm-morning\dalio_lens_current.json` — active weekly Dalio view
- `C:\Users\User\Desktop\sigma-brain\Memory\pm-morning\deep_dive_rotation.json` — Tuesday ETF cursor + Thursday theme cursor
- `C:\Users\User\Desktop\sigma-brain\Memory\pm-morning\shadow_portfolio.json` — current positions, NAV history
- `C:\Users\User\Desktop\sigma-brain\Memory\pm-morning\universe.yaml` — ETF universe definition
- `C:\Users\User\Desktop\sigma-brain\Memory\pm-morning\config.json` — email recipient, thresholds, etc.

**Outputs (one folder per day):**
- `C:\Users\User\Desktop\sigma-brain\outputs\pm-morning\YYYY-MM-DD\brief.html`
- `C:\Users\User\Desktop\sigma-brain\outputs\pm-morning\YYYY-MM-DD\brief.pdf`
- `C:\Users\User\Desktop\sigma-brain\outputs\pm-morning\YYYY-MM-DD\data_snapshot.json`
- `C:\Users\User\Desktop\sigma-brain\outputs\pm-morning\YYYY-MM-DD\portfolio_review.md` (Fridays only)

**Bash paths (for shell tool):**
- Outputs root: `/sessions/busy-optimistic-darwin/mnt/sigma-brain/outputs/pm-morning/`
- Memory root: `/sessions/busy-optimistic-darwin/mnt/sigma-brain/Memory/pm-morning/`

---

## Pre-flight checks (run first, every time)

1. **Confirm date and weekday in MYT.** Run:
   ```bash
   TZ=Asia/Kuala_Lumpur date '+%Y-%m-%d %A %H:%M'
   ```
   Use the date as the output folder name (`YYYY-MM-DD`). Use the weekday for Section 4 routing.

2. **Check / create Memory folder structure:**
   ```bash
   mkdir -p /sessions/busy-optimistic-darwin/mnt/sigma-brain/Memory/pm-morning
   mkdir -p /sessions/busy-optimistic-darwin/mnt/sigma-brain/outputs/pm-morning
   ```

3. **First-run bootstrapping:** if any state file is missing, create it from templates in the Appendix at the bottom of this file. Specifically:
   - `universe.yaml` — bootstrap from Appendix A
   - `dalio_lens_current.json` — bootstrap with placeholder, flag to user that a Monday refresh is needed
   - `deep_dive_rotation.json` — initialize cursors at index 0
   - `shadow_portfolio.json` — initialize with $100,000 USD cash, no positions yet (Day 0 construction happens on first manual run, not in scheduled mode)
   - `config.json` — bootstrap with email recipient and SMTP placeholder

4. **Check Python deps in bash sandbox:**
   ```bash
   pip install --break-system-packages yfinance fredapi pyyaml jinja2 weasyprint plotly kaleido pandas requests beautifulsoup4 pypdf 2>&1 | tail -5
   ```

5. **Verify env vars:**
   - `FRED_API_KEY` — required for Section 1 macro context
   - `GMAIL_APP_PASSWORD` (or `SMTP_PASSWORD`) — required for Option B email
   - If missing: log warning, continue, fall back to Gmail draft (Option A)

---

## Step-by-step procedure

Execute in this order. Each step is independent — if one fails, log and continue.

### Step 1 — Read state

Read the four state files. Hold their contents in working memory for the whole run.

### Step 2 — Determine day-of-week routing

```python
import datetime
from zoneinfo import ZoneInfo
now_myt = datetime.datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
weekday = now_myt.weekday()  # 0=Mon ... 4=Fri
```

Map to deep-dive theme:
- 0 (Mon) → ETF Flows of the Week
- 1 (Tue) → One ETF Dissected (use cursor in `deep_dive_rotation.json`)
- 2 (Wed) → Cross-Asset Rotation Signal
- 3 (Thu) → Thematic Spotlight (use thematic cursor)
- 4 (Fri) → Malaysia + ASEAN ETF Lens + (also) ETF Mechanics Drill (Section 9)

Skip Saturday/Sunday — if invoked on a weekend, log and exit cleanly.

### Step 3 — Fetch data (parallel where possible)

Run these bash blocks. Cache results to `data_snapshot.json` for the day.

**a) ETF closes via yfinance** — full universe from `universe.yaml`:
```python
import yfinance as yf, yaml, json, os
universe = yaml.safe_load(open("/sessions/busy-optimistic-darwin/mnt/sigma-brain/Memory/pm-morning/universe.yaml"))
tickers = [t["ticker"] for bucket in universe.values() for t in bucket]
data = yf.download(tickers, period="6mo", interval="1d", group_by="ticker", progress=False, threads=True)
# extract close, % chg, 1d, 5d, MTD, YTD per ticker → save to data_snapshot.json
```

**b) FRED macro:** UST 10Y (`DGS10`), UST 2Y (`DGS2`), DXY (`DTWEXBGS`), VIX (`VIXCLS`).
```python
from fredapi import Fred
fred = Fred(api_key=os.environ["FRED_API_KEY"])
series_ids = ["DGS10", "DGS2", "DTWEXBGS", "VIXCLS"]
fred_data = {sid: fred.get_series(sid).iloc[-5:].to_dict() for sid in series_ids}
```

**c) Bursa Malaysia data** — KLCI close, top movers, foreign flows. Try in order:
1. `https://www.bursamalaysia.com/market_information/equities_prices`
2. Maybank2u markets feed
3. Investing.com KLCI page

Use httpx + bs4. If all fail, mark Section 3 as "data stale — last known [date]" and proceed.

**d) PBoC fixing:** scrape `http://www.pbc.gov.cn` daily fixing or use Investing.com USD/CNY page.

**e) Economic calendar:** scrape Forex Factory or use `investpy`. Filter to next 24h, MYT-stamped.

Cache the entire fetched dataset to:
`/sessions/busy-optimistic-darwin/mnt/sigma-brain/outputs/pm-morning/YYYY-MM-DD/data_snapshot.json`

### Step 4 — Generate sections

**Section −1 (Dalio Lens):** Read `dalio_lens_current.json`. If `week_of` is older than this Monday, flag and use cached. Render as the half-page block at the top of the brief. (Weekly refresh is its own command — see "Weekly Dalio Refresh" below.)

**Section 0 (Regime Line):** Synthesize today's tilt in 2 sentences. Format: `Risk-{on/off/neutral}. [overnight headline]. [implied tilt with ETF tickers].`

**Section 1 (Overnight Wrap):** Build a markdown table from fetched data:

| Asset | Level | % chg | ETF |
|---|---|---|---|
| S&P 500 | 5,234 | -0.8% | SPY |
| Nasdaq 100 | 18,420 | -2.1% | QQQ |
| ... | ... | ... | ... |

Plus one sentence: *why* did markets move? (Use overnight news context.)

**Section 2 (Asia Open):** Regional ETF tape (EWJ, EWY, MCHI, FXI, EWT, INDA, EWS, EWM, ASEA, VWO). PBoC fixing line. EWM premium/discount line. 3 sentences max.

**Section 3 (Malaysia Today):** Use Bursa data. Required components:
- KLCI futures vs prior close, FBM 100, FBM Small Cap
- Foreign net flows yesterday (RM amount + sector breakdown)
- Top 5 movers + reason
- Today's local catalysts
- Sector to watch + numeric trigger
- BNM / MYR pulse
- EWM Watch line

**Section 4 (Rotating Deep Dive):** Route by weekday (Step 2). For depth quality, use Opus-4.7-grade reasoning here — produce 3 paragraphs + suggest 1–2 charts (saved as PNG via plotly+kaleido). Update the Tuesday/Thursday cursor in `deep_dive_rotation.json` after generating.

**Section 5 (Calendar):** 5 lines max, MYT-stamped, time-ordered. Format:
- `08:30 MYT — Malaysia trade balance (March)`
- `15:00 MYT — Eurozone CPI flash`

**Section 6 (Action Prompts):** 3–5 trigger-based one-liners. Each MUST contain a numeric trigger AND an ETF action. Reference the Dalio quadrant explicitly.

**Section 7 (Desk Conviction):** Generate a draft one-liner. Mark it `[DRAFT — Syafiq to finalize]`. The human owns this section.

**Section 8 (Shadow Portfolio):** Read `shadow_portfolio.json`. Compute today's NAV using fetched closes:
- Daily return, MTD return, YTD return
- Top 3 contributors / detractors
- Current sector + regional tilts vs benchmark (60/40 ACWI/AGG)
- Sharpe (rolling 60d), max DD (since inception)

If today is Friday, also run weekly review: check signals, drift, breaches. Output `portfolio_review.md` alongside the brief.

**Section 9 (ETF Mechanics Drill):** Fridays only. Use `deep_dive_rotation.json` mechanics cursor. Generate ~1 page on the next mechanic in the cycle. Update cursor.

### Step 5 — Compile HTML

Build a single self-contained HTML file using inline CSS. Structure:

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>PM Morning Brief — YYYY-MM-DD</title>
  <style>/* inline CSS — clean serif body, sans header, table styles, dark accent */</style>
</head>
<body>
  <header>
    <h1>PM Morning Brief</h1>
    <div class="meta">YYYY-MM-DD · Weekday · MYT</div>
  </header>

  <section id="dalio-lens"> ... </section>
  <section id="regime-line"> ... </section>
  <section id="overnight-wrap"> ... </section>
  <section id="asia-open"> ... </section>
  <section id="malaysia-today"> ... </section>
  <section id="deep-dive"> ... </section>
  <section id="calendar"> ... </section>
  <section id="action-prompts"> ... </section>
  <section id="desk-conviction"> ... </section>
  <section id="shadow-portfolio"> ... </section>
  <section id="mechanics-drill"> <!-- Friday only --> </section>

  <footer>
    <small>Generated [timestamp] · sigma-pm-morning v0.1</small>
  </footer>
</body>
</html>
```

Save to `outputs/pm-morning/YYYY-MM-DD/brief.html`.

### Step 6 — Render PDF

```python
from weasyprint import HTML
HTML(filename=html_path).write_pdf(pdf_path)
```

Save alongside the HTML at `brief.pdf`.

### Step 7 — Push to email

Try Option B first; fall back to Option A.

**Option B — SMTP (preferred):**
```python
import smtplib, ssl, os
from email.message import EmailMessage

msg = EmailMessage()
msg["Subject"] = f"[PM Brief] {date_str} — {quadrant} {tilt_line}"
msg["From"] = "syafiqmohdzin3@gmail.com"
msg["To"] = "syafiqmohdzin3@gmail.com"
msg.set_content(plain_text_summary)              # plain-text fallback
msg.add_alternative(html_body, subtype="html")    # rich HTML
with open(pdf_path, "rb") as f:
    msg.add_attachment(f.read(),
                       maintype="application",
                       subtype="pdf",
                       filename=f"PM_Brief_{date_str}.pdf")

ctx = ssl.create_default_context()
with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as server:
    server.login("syafiqmohdzin3@gmail.com", os.environ["GMAIL_APP_PASSWORD"])
    server.send_message(msg)
```

If `GMAIL_APP_PASSWORD` is not set or SMTP fails:

**Option A — Gmail draft via MCP:**
Use `mcp__16a029a7-15dc-4833-921c-8d14af44c0d8__create_draft` with the PDF attached. Subject as above. To: self. Notify user that the draft is ready to send.

### Step 8 — Update state

After successful generation, update:
- `deep_dive_rotation.json` — increment Tuesday or Thursday cursor as appropriate
- `shadow_portfolio.json` — append today's NAV record
- (Friday only) `deep_dive_rotation.json` mechanics cursor

Do NOT update `dalio_lens_current.json` from a daily run. That's only updated by the weekly refresh.

### Step 9 — Report completion

Return a summary message:

```
✅ PM Morning Brief generated for YYYY-MM-DD (Monday)

Quadrant: ↑G ↓I (unchanged from week of YYYY-MM-DD)
Regime: Risk-on. SPY +1.2%, defensives soft. Tilt: hold OW QQQ/SOXX.

Sections shipped: -1, 0, 1, 2, 3, 4 (ETF Flows), 5, 6, 7, 8
Sections skipped: 9 (not Friday)

Email: ✅ sent via SMTP
Files: outputs/pm-morning/2026-05-08/
- brief.html (217 KB)
- brief.pdf (412 KB)
- data_snapshot.json (89 KB)

Open: file:///C:/Users/User/Desktop/sigma-brain/outputs/pm-morning/2026-05-08/brief.html
```

---

## Weekly Dalio Refresh (separate command)

When user runs "refresh dalio lens" / "weekly lens" / scheduled task on Mondays at 6:30am MYT:

1. Read prior week's `dalio_lens_current.json`
2. Pull last 7 days of macro data (rates, FX, oil, equity vol, sector rotation, EM flows)
3. Reason from first principles using Opus-4.7-grade depth:
   - Is the quadrant still right? Why?
   - Has the historical analog shifted?
   - Have any "what would change my mind" triggers been hit? If yes, flip explicitly.
   - Five Forces — any escalation in the past week?
4. Output proposed update as a markdown diff
5. Ask user to approve / edit / replace
6. On approval, write to `dalio_lens_current.json` with new `week_of` date

This is the single most important weekly ritual. Do not skip.

---

## Scheduled task setup (one-time)

To make this run unattended at 6:45am MYT every weekday, register a scheduled task. Check the available tool first with ToolSearch:

```
ToolSearch query="select:mcp__scheduled-tasks__create_scheduled_task" max_results=1
```

Then create the task with these parameters (adjust syntax to match the tool schema once loaded):
- Name: `sigma-pm-morning-daily`
- Schedule: cron `45 22 * * 1-5` (22:45 UTC = 6:45 AM MYT, Mon-Fri)
- Action: invoke this skill (sigma-pm-morning)
- Notify on failure: yes

Also register a weekly task for the Dalio refresh:
- Name: `sigma-pm-morning-dalio-weekly`
- Schedule: cron `30 22 * * 1` (22:30 UTC Mondays = 6:30 AM MYT)
- Action: weekly Dalio refresh

Verify both tasks fire correctly with a smoke run before relying on them.

---

## Failure handling

| Failure | Action |
|---|---|
| FRED API down | Skip macro context; mark Section 1 as "FRED unavailable, fixed-income context stale" |
| Yahoo Finance rate limit | Retry 3× with 5s backoff; if still failing, use cached prices from yesterday + mark stale |
| Bursa scrape blocked | Try Maybank2u → Investing.com → fail open with "Section 3 unavailable, will retry" |
| Anthropic rate limit (Pro plan) | Ship the must-have sections (-1, 0, 1, 3) and stop; report partial brief with explicit list of skipped sections |
| WeasyPrint PDF render fails | Ship HTML only; mark email body to say "PDF render failed, see HTML link" |
| Email SMTP fails | Fall back to Gmail draft via MCP |
| Gmail MCP fails | Save brief to outputs folder and notify user via response message — they open file directly |

Never silently fail. Every degradation must be visible in the brief itself or the completion report.

---

## Output style guide

- **Lead with the table, follow with the prose.** Every section that has data starts with a scannable table; commentary comes second.
- **ETF tickers in every macro statement.** "Risk-off, defensives bid" → "Risk-off, XLU/XLP outperforming XLK."
- **Numeric triggers, not vibes.** "If 10Y breaks 5%" not "if rates rise."
- **MYT-stamped times.** Always.
- **One chart per section maximum.** No chart-stuffing.
- **Total read time ceiling: 12 minutes.** If a draft brief is longer, trim before shipping.

---

## Appendix A — Universe bootstrap (`universe.yaml`)

```yaml
us_broad:
  - {ticker: SPY,  name: "SPDR S&P 500",                    asset_class: equity, region: US}
  - {ticker: QQQ,  name: "Invesco QQQ",                      asset_class: equity, region: US}
  - {ticker: IWM,  name: "iShares Russell 2000",             asset_class: equity, region: US}
  - {ticker: VTI,  name: "Vanguard Total Market",            asset_class: equity, region: US}

us_factors:
  - {ticker: MTUM, name: "iShares MSCI USA Momentum",        asset_class: equity, factor: momentum}
  - {ticker: USMV, name: "iShares MSCI USA Min Vol",         asset_class: equity, factor: low_vol}
  - {ticker: VLUE, name: "iShares MSCI USA Value",           asset_class: equity, factor: value}
  - {ticker: QUAL, name: "iShares MSCI USA Quality",         asset_class: equity, factor: quality}

us_sectors:
  - {ticker: XLK,  name: "Technology Select Sector",         asset_class: equity, sector: tech}
  - {ticker: XLF,  name: "Financials Select Sector",         asset_class: equity, sector: financials}
  - {ticker: XLE,  name: "Energy Select Sector",             asset_class: equity, sector: energy}
  - {ticker: XLU,  name: "Utilities Select Sector",          asset_class: equity, sector: utilities}
  - {ticker: XLV,  name: "Health Care Select Sector",        asset_class: equity, sector: healthcare}
  - {ticker: XLP,  name: "Consumer Staples Select Sector",   asset_class: equity, sector: staples}
  - {ticker: XLY,  name: "Consumer Discretionary Sector",    asset_class: equity, sector: discretionary}
  - {ticker: XLI,  name: "Industrial Select Sector",         asset_class: equity, sector: industrials}
  - {ticker: XLB,  name: "Materials Select Sector",          asset_class: equity, sector: materials}
  - {ticker: XLRE, name: "Real Estate Select Sector",        asset_class: equity, sector: real_estate}
  - {ticker: XLC,  name: "Communication Services Sector",    asset_class: equity, sector: comm}

themes:
  - {ticker: SOXX, name: "iShares Semiconductor",            asset_class: equity, theme: semis}
  - {ticker: SMH,  name: "VanEck Semiconductor",             asset_class: equity, theme: semis}
  - {ticker: IGV,  name: "iShares Software",                 asset_class: equity, theme: software}
  - {ticker: IBIT, name: "iShares Bitcoin Trust",            asset_class: alt,    theme: crypto}
  - {ticker: ITA,  name: "iShares US Aerospace & Defense",   asset_class: equity, theme: defense}
  - {ticker: KWEB, name: "KraneShares China Internet",       asset_class: equity, theme: china_tech}

regional:
  - {ticker: EWM,  name: "iShares MSCI Malaysia",            asset_class: equity, region: MY,  flag: flagship}
  - {ticker: ASEA, name: "Global X ASEAN 40",                asset_class: equity, region: ASEAN}
  - {ticker: MCHI, name: "iShares MSCI China",               asset_class: equity, region: CN}
  - {ticker: FXI,  name: "iShares China Large-Cap",          asset_class: equity, region: CN}
  - {ticker: EWY,  name: "iShares MSCI South Korea",         asset_class: equity, region: KR}
  - {ticker: EWJ,  name: "iShares MSCI Japan",               asset_class: equity, region: JP}
  - {ticker: INDA, name: "iShares MSCI India",               asset_class: equity, region: IN}
  - {ticker: EWS,  name: "iShares MSCI Singapore",           asset_class: equity, region: SG}
  - {ticker: EWT,  name: "iShares MSCI Taiwan",              asset_class: equity, region: TW}
  - {ticker: EWZ,  name: "iShares MSCI Brazil",              asset_class: equity, region: BR}
  - {ticker: EWG,  name: "iShares MSCI Germany",             asset_class: equity, region: DE}
  - {ticker: VEA,  name: "Vanguard Developed ex-US",         asset_class: equity, region: DM_exUS}
  - {ticker: VWO,  name: "Vanguard Emerging Markets",        asset_class: equity, region: EM}

bonds:
  - {ticker: TLT,  name: "iShares 20+ Year Treasury",        asset_class: bond, maturity: long}
  - {ticker: IEF,  name: "iShares 7-10 Year Treasury",       asset_class: bond, maturity: intermediate}
  - {ticker: SHY,  name: "iShares 1-3 Year Treasury",        asset_class: bond, maturity: short}
  - {ticker: HYG,  name: "iShares iBoxx High Yield",         asset_class: bond, credit: HY}
  - {ticker: LQD,  name: "iShares iBoxx IG Corporate",       asset_class: bond, credit: IG}
  - {ticker: EMB,  name: "iShares JPM USD EM Bond",          asset_class: bond, region: EM}

commodities:
  - {ticker: GLD,  name: "SPDR Gold",                        asset_class: commodity, sub: gold}
  - {ticker: SLV,  name: "iShares Silver",                   asset_class: commodity, sub: silver}
  - {ticker: USO,  name: "US Oil Fund (WTI)",                asset_class: commodity, sub: oil_wti}
  - {ticker: BNO,  name: "US Brent Oil Fund",                asset_class: commodity, sub: oil_brent}
  - {ticker: CPER, name: "US Copper Fund",                   asset_class: commodity, sub: copper}
  - {ticker: URA,  name: "Global X Uranium",                 asset_class: commodity, sub: uranium}
  - {ticker: DBA,  name: "Invesco DB Agriculture",           asset_class: commodity, sub: ag}
  - {ticker: DBC,  name: "Invesco DB Commodity Index",       asset_class: commodity, sub: broad}

fx_vol:
  - {ticker: UUP,  name: "Invesco DB US Dollar Bullish",     asset_class: fx,  sub: usd}
  - {ticker: FXY,  name: "Invesco CurrencyShares Yen",       asset_class: fx,  sub: jpy}
  - {ticker: VXX,  name: "iPath Series B S&P 500 VIX",       asset_class: vol, sub: vix, hold: signal_only}
```

## Appendix B — Dalio Lens template (`dalio_lens_current.json`)

```json
{
  "week_of": "2026-05-04",
  "quadrant": "↑G ↓I",
  "quadrant_rationale": "Growth resilient (NFP, GDP nowcast); inflation easing (core CPI, services). Asset bias: SPY, QQQ, MTUM, SOXX.",
  "short_cycle": "mid expansion",
  "long_cycle": "late long cycle, structural debt overhang in DM sovereigns",
  "five_forces": {
    "debt_machine": "DM debt-to-GDP elevated; Fed easing path keeps refi tractable",
    "internal_conflict": "US election dynamics escalating; Malaysia politics stable",
    "external_conflict": "US-China tariff drumbeat; Taiwan stable; Middle East low-grade hot",
    "nature": "neutral; no major climate shock active",
    "technology": "AI capex supercycle in mid-innings; productivity tailwind"
  },
  "historical_analog": "1995-96 — late-cycle rate cuts into resilient growth, tech outperformance",
  "change_my_mind_triggers": [
    {"trigger": "10Y > 5.0% sustained 5 sessions", "if_hit": "flip to ↓G ↑I (stagflation)"},
    {"trigger": "Brent > $100 sustained 10 sessions", "if_hit": "flip to ↑G ↑I (commodity inflation)"},
    {"trigger": "Payrolls miss 2 months running AND ISM < 48", "if_hit": "flip to ↓G ↓I (recession)"}
  ],
  "last_reviewed": "2026-05-05T07:00:00+08:00",
  "version": 1
}
```

## Appendix C — Deep dive rotation (`deep_dive_rotation.json`)

```json
{
  "tuesday_etf_cursor": {
    "queue": ["EWM", "SOXX", "TLT", "GLD", "XLE", "KWEB", "URA", "IBIT", "MCHI", "INDA", "ASEA", "ITA"],
    "next_index": 0
  },
  "thursday_theme_cursor": {
    "queue": ["AI Infrastructure", "Scarce Metals", "Defense", "China Tech", "Energy Transition", "Bond Market", "Volatility", "EM Local Currency"],
    "next_index": 0
  },
  "friday_mechanics_cursor": {
    "queue": [
      "Creation/Redemption + APs",
      "Premium/Discount and Arbitrage",
      "NAV Calculation",
      "Tax Efficiency vs Mutual Funds",
      "Synthetic Replication (UCITS Swap-based)",
      "Leveraged/Inverse ETF Decay",
      "Fixed-Income ETF Basket Pricing",
      "Index Reconstitution Arbitrage",
      "ETF Closures",
      "Securities Lending Revenue",
      "Total Return Swap Structures",
      "Active ETF Mechanics"
    ],
    "next_index": 0
  }
}
```

## Appendix D — Shadow portfolio bootstrap (`shadow_portfolio.json`)

```json
{
  "inception_date": null,
  "base_currency": "USD",
  "starting_capital": 100000,
  "benchmark": "60/40 ACWI/AGG",
  "current_cash": 100000,
  "positions": [],
  "constraints": {
    "min_positions": 8,
    "max_positions": 15,
    "max_single_etf_weight": 0.15,
    "max_single_sector_weight": 0.50,
    "max_cash_weight": 0.20,
    "no_leverage": true
  },
  "nav_history": [],
  "transactions": [],
  "rebalance_log": [],
  "version": 1
}
```

Day 0 portfolio construction happens on the first **manual** invocation when `inception_date` is null. The skill prompts the user for initial allocation rationale and writes the first transactions. Scheduled runs do NOT initialize the portfolio.

## Appendix E — Config bootstrap (`config.json`)

```json
{
  "email": {
    "to": "syafiqmohdzin3@gmail.com",
    "from": "syafiqmohdzin3@gmail.com",
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 465,
    "smtp_user": "syafiqmohdzin3@gmail.com"
  },
  "thresholds": {
    "foreign_flow_alert_rm_million": 200,
    "myr_alert_level": 4.50,
    "dxy_alert_level": 105.50,
    "ust_10y_alert_pct": 5.0,
    "brent_alert_usd": 100
  },
  "read_time_ceiling_minutes": 12,
  "version": 1
}
```

---

## Glossary (quick reference)

- **AP** — Authorized Participant; institution that creates/redeems ETF units in the primary market.
- **CPO** — Crude Palm Oil; major Malaysian export, traded on Bursa Malaysia Derivatives.
- **EWM** — iShares MSCI Malaysia ETF; flagship for this brief, the bridge between Malaysia and US ETF markets.
- **KLCI** — FTSE Bursa Malaysia KLCI; top 30 Malaysian large-caps.
- **MGS** — Malaysian Government Securities; local sovereign bond curve.
- **MOVE** — Bond market volatility index (Treasury equivalent of VIX).
- **MPOB** — Malaysian Palm Oil Board; releases monthly inventory data.
- **OPR** — Overnight Policy Rate; BNM's policy rate.
- **Quadrant** — Growth × Inflation 2×2 matrix anchoring asset allocation tilt.

---

**End of skill v0.1.**
