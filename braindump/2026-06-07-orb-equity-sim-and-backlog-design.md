# Design Spec — ORB-001 $50 Equity Simulator + Research Backlog Table

**Date:** 2026-06-07
**Author:** Syafiq + Claude (brainstorm)
**Status:** Approved design → ready for implementation plan
**Scope:** Two deliverables this session: (1) a dollar-equity simulator for ORB-001 London, (2) a `step6_backlog` DB table to track follow-ups. NY-open (ORB-002) is recorded *into* the backlog, not built now.

---

## 1. Why

ORB-001 (London-open breakout, XAUUSD) passed the full gate ladder G0→G6, but **entirely in R-multiples** — a deliberate choice (edge must be proven independent of bet-sizing and account size; R-multiples give a clean t-stat, dollar curves are path-dependent and un-inferable). See [research/models/orb/](../research/models/orb/).

That leaves one question unanswered: **can a real $50 account survive trading this edge?** Min-lot risk at $3300 gold is a large fraction of $50 (median ~6%, p90 ~33% per trade). That is a survival question, not an edge question, and it was deferred until the edge was proven — which it now is.

| Question | Status |
|----------|--------|
| Does the breakout have an edge? | ✅ Validated G0–G6 (R-multiples) |
| Can a real $50 account survive it? | ❌ Never simulated — **this spec** |

---

## 2. Deliverable 1 — `$50` Equity Simulator

### 2.1 Location
`research/models/orb/equity_sim.py` — sits beside the existing gate files, consumes the same trade DataFrame the backtest already produces.

### 2.2 Input
The trade DataFrame from `orb_backtest.run_backtest_multi(...)` (already exists). Each row carries everything needed:
- `R` — the realised R-multiple (+target_R, −1.0, or fractional eod)
- `range_w` — opening-range width in price ($/oz) = **1R in price units**
- `direction`, `entry_px`, `entry_ts`, `exit_ts`, `date`

We run on the **OOS slice** (sealed 2024-05-02 → 2026-05-18) at the frozen config (N=5, 3R target, 2-pip spread). IS can be run too for comparison, but OOS is the honest survival picture.

### 2.3 Dollar conversion math (exact, from [brokers/justmarkets.yaml](../brokers/justmarkets.yaml))
- Contract size: **1.00 lot = 100 oz**; min lot **0.01** (= 1 oz); lot step **0.01**.
- Dollar P&L for a price move Δ ($/oz) on lot size `L`:  `pnl = Δ × 100 × L`.
- A trade's dollar P&L:  `pnl = R × range_w × 100 × L`.
  - On min lot (L=0.01): `pnl = R × range_w` → a −1R loss costs exactly `range_w` dollars. (range_w median ≈ $3 → −$3 = 6% of $50; p90 ≈ $16.5 → 33%. ✓ matches the survival flag.)

### 2.4 Costs (already settled — do not re-litigate)
- **Spread**: already baked into each trade's `R` as a win-rate drag (B-book/swap-free model, corrected 2026-06-06). Do **not** deduct it again in dollars.
- **Swap**: $0 (swap-free + EOD-flat, no overnight).
- **Commission**: $0 (Pro account).
- So dollar P&L = `R × range_w × 100 × L` with no further deductions. Spread is the only cost and it's upstream.

### 2.5 Margin / leverage (confirmed NOT the binding constraint)
At JM 1:3000 dynamic leverage, margin per min-lot at $3300 ≈ **$1.50**. The sim still checks affordability (`used_margin = notional / leverage`; block trade if `free_margin < used_margin`), and models stop-out (`equity/used_margin × 100 < 20%`), but in practice **risk-per-trade, not margin, is the wall.** Ruin ≈ equity eaten to ~0 by a loss string, not a margin call.

### 2.6 Two sizing modes — run sequentially, both required
Syafiq: "we have to do both, one at a time." Mode A is this session; Mode B is a backlog row.

**Mode A — Fixed min-lot + survival skip-filter (BUILD NOW):**
- Always trade 0.01 lot (you cannot size finer on $50 anyway).
- **Survival filter**: skip any day where `risk_$ / equity > cap`. Cap expressed as **% of equity** (and a parallel **ATR-relative** variant), NOT fixed dollars — the old fixed-$5 cap broke when gold doubled.
- Sweep the cap (e.g. 5% / 10% / 15% / 20% / no-cap) and report survival + terminal equity for each.

**Mode B — Fixed-fractional / compounding (BACKLOG, next):**
- Risk a target % of *current* equity, rounded to lot step 0.01. Compounds as equity grows; coarse on $50 until the account is much larger. Compare its equity curve against Mode A.

### 2.7 Outputs
1. **Equity curve** trade-by-trade, starting $50 → terminal balance.
2. **quantstats tearsheet** (HTML) — Sharpe/Sortino/Calmar, max drawdown, monthly-returns heatmap, VaR. Feed it the daily-returns series derived from the equity curve (ORB = one trade/day, maps cleanly). Save to `research/outputs/`.
3. **Custom plotly** equity + drawdown chart (the one view quantstats doesn't nail). Save to `research/outputs/`.
4. **Console summary**: start/terminal equity, CAGR, max DD %, longest losing streak, # trades skipped by filter, **did it blow up? (y/n)**, per-cap-setting table.
5. **DB**: log the survival result to `step4_results` via `pipeline.log_result(...)` (this is a real validation output) + `log_human_decision` for the methodology.

### 2.8 Non-goals (YAGNI)
- No multi-asset, no multi-strategy portfolio, no live broker connection.
- No re-running the edge gates — edge is settled.
- No Mode B in this session (backlog).
- No new viz dependency — quantstats + plotly are already installed.

---

## 3. Deliverable 2 — `step6_backlog` Table

### 3.1 Why a table, not markdown
Decided with Syafiq: markdown backlogs get orphaned by agents; the system is DB-centric and agents already query `research.db`. A queryable table is the consistent, durable choice. Kept minimal to avoid building a sprawling task tracker.

### 3.2 Schema (add to [research/code/db_init.py](../research/code/db_init.py), `CREATE TABLE IF NOT EXISTS`)
```sql
CREATE TABLE IF NOT EXISTS step6_backlog (
    task_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    idea_id     TEXT REFERENCES step1_ideas(idea_id),   -- nullable: some tasks are cross-cutting infra
    title       TEXT NOT NULL,
    detail      TEXT,
    kind        TEXT NOT NULL CHECK(kind IN
                  ('variant','sizing','filter','port','infra','data','cleanup')),
    priority    TEXT NOT NULL DEFAULT 'P2' CHECK(priority IN ('P0','P1','P2')),
    status      TEXT NOT NULL DEFAULT 'open'
                  CHECK(status IN ('open','in_progress','done','dropped')),
    created_at  DATETIME NOT NULL,
    updated_at  DATETIME NOT NULL,
    resolved_at DATETIME,
    resolution  TEXT
);
```
Plus an `open_backlog` view (status IN open/in_progress, ordered by priority) mirroring the existing `*_queue` views.

### 3.3 Code layer — `research/code/backlog.py`
All writes via code layer (rule 15). MYT timestamps, validation, same `_conn()` pattern as agent_log.py.
- `add_task(title, kind, detail='', idea_id=None, priority='P2') -> task_id`
- `update_task(task_id, **fields)` (status/priority/detail; bumps `updated_at`)
- `resolve_task(task_id, resolution, status='done')`
- `get_backlog(status='open', idea_id=None) -> list[dict]`

### 3.4 Migration
`research/migrations/012_create_backlog.py` — additive only (CREATE TABLE/VIEW IF NOT EXISTS). No data touched. Re-runnable.

---

## 4. Backlog seed entries (insert on table creation)

| title | kind | priority | idea_id |
|-------|------|----------|---------|
| ORB equity sim — Mode B fixed-fractional/compounding | sizing | P1 | ORB-001 |
| ORB %/ATR survival filter — productionise winning cap | filter | P1 | ORB-001 |
| ORB-002 — NY-session ORB: re-state Gate 0, inherit G1, re-run G3/5/6 | variant | P1 | ORB-001 |
| ORB-001 MQL5 port into Sigma EA (live XAUUSD) | port | P2 | ORB-001 |
| ORB-001 regime gate (Gate 4 attempt 2) — trend/session filter | filter | P2 | ORB-001 |
| Rename ORB-001 "London → NY" → "London" (NY split to ORB-002) | cleanup | P2 | ORB-001 |

**ORB-002 note (lineage decision):** when spun up, register as its own top-level idea `ORB-002` with `parent_idea_id='ORB-001'`. The parent pointer records *why* its ladder is partial. Gate 0 (economic rationale) is **re-answered** — NY-open fires into the London afternoon, a different liquidity regime than London-open's overnight-range break; the edge does not transfer for free. G1 inherits; G2 quick re-confirm; G3/5/6 full re-run.

---

## 5. Testing
- **equity_sim**: unit-test the dollar conversion against a hand-worked trade (R=−1, range_w=$3, min lot → −$3.00 exactly; R=+3, range_w=$3 → +$9.00). Test the skip-filter boundary. Test ruin detection on a forced losing-streak fixture.
- **backlog.py**: round-trip test (add → get → update → resolve → get) on a temp DB; CHECK-constraint rejection of bad `kind`/`status`.

## 6. Build order
1. `step6_backlog` table + `backlog.py` + migration 012 + seed entries (infra first, so follow-ups are captured immediately).
2. `equity_sim.py` Mode A + survival-filter sweep.
3. Generate tearsheet + plotly outputs, console summary.
4. Log result to `step4_results` + `log_human_decision`.

## 7. Open questions
None blocking. Resolved in brainstorm: both sizing modes required (A now, B backlog); backlog as DB table not MD; ORB-002 = separate idea w/ parent pointer + re-stated Gate 0; spread already in R (don't double-count); margin not the wall.
