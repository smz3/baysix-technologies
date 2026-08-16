> ⚠️ **SUPERSEDED / ARCHIVED 2026-06-22.** Describes the old Gate-7 MT5⇄Python fidelity flow, which Protocol 4.0 dissolved (7-gate ladder → 4 gates G1–G4; the Python fill-sim + tester-vs-Python fidelity diff are gone). Historical context only — not a current design of record.

# MT5 ⇄ research.db Fidelity Flow — Design of Record

**Locked:** 2026-06-12 · **Owner:** Claude + Syafiq · **Status:** building (tasks 55 → 54 → 46/43)

The end-to-end path from an MT5 Strategy-Tester run to a Gate-7 fidelity verdict, designed
around ONE principle: **unbounded trade data never enters the agent's (Claude's) context.**
Built scalping-ready from day one (100s of trades/day) so it never needs re-cutting.

---

## The token firewall (the whole point)

```
  below the line  =  unbounded rows · handled by scripts + SQLite · ZERO model tokens
 ─────────────────────────────────  FIREWALL  ─────────────────────────────────
  above the line  =  bounded ~200-token verdict · the only thing Claude ever reads
```

The firewall IS the aggregate SQL. A 1-trade ORB run and a 2-million-trade scalper both
reach Claude as the same 5-line verdict. Context cost is **flat and constant** regardless
of strategy aggressiveness.

**Three rules that keep it airtight:**
1. Claude never `Read`s a CSV or `.xlsx`. They live below the firewall. If Claude opens one, that's a leak — treat as a bug.
2. Claude never `SELECT *` from `tester_trades`. Aggregates only.
3. The EA writes feed B clean (schema = contract), so no model ever interprets raw output.

---

## Flow

### 1. WRITE PATH — MT5 (in-tester)
- The EA (ORB-001 today, scalpers later) holds **one** `CCSVExporter` instance.
- Every `ClosePosition()` chokepoint → buffer a per-trade row.
- Buffer **flushes every N rows + on `OnDeinit`** — mandatory for scale; unbuffered FileWrite
  at 100s/day × multi-year would make the tester crawl.
- Output **Feed B**: clean per-trade CSV via `FILE_COMMON` + retry/backoff (Excel/Python lock race).
  **Feed B is the AUTHORITATIVE per-trade record** — we do NOT parse the xlsx Deals section.
- MT5 auto-writes **Feed A** on run-end: `ReportTester-<login>.xlsx` = run summary + config only.

### 2. INGEST PATH — disk → research.db (one script · $0 model tokens)
Orchestrated by `run_and_verify.py` (task 46):
- `ingest_tester_report.py` — Feed A → `tester_runs` (run_id), renames xlsx 1:1 to run_id.
- `ingest_tester_trades` (NEW, task 43) — Feed B → `tester_trades`:
  - **streamed/chunked** (million-row safe — never `read_csv` whole into memory),
  - join key = **ticket + entry_ts** (NOT session_date),
  - indexed on `run_id (, entry_ts)`.
- **Integrity assert:** `feedA.n_trades == COUNT(feedB)` and `feedA.net ≈ SUM(feedB.pnl)`.

### 3. VERDICT PATH — research.db → Claude (the only thing that crosses)
- ONE aggregate SQL + `tester.log_fidelity_diff()`:
  `run_id · n_trades · $/trade · t-stat · R_corr vs Python · trade_overlap% · PASS/FAIL`.
- On PASS → `pipeline.pass_gate(idea, 7)`.
- Claude reads THIS. ~5 lines. Never a row, never the CSV, never the xlsx.

---

## Feed B schema (the contract — universal, not ORB-specific)

`tester_trades` after migration 024 (task 55):

| column | role |
|---|---|
| `ticket` | MT5 position id — unique within a run |
| `session_date` | nullable convenience (daily strategies only) |
| `direction` | long / short / flat |
| `entry_ts`, `entry_px` | entry (entry_ts = cross-system join key with ticket) |
| `exit_ts`, `exit_px`, `exit_reason` | exit |
| `lots` | position size (matters at scale / sizing) |
| `risk_unit` | **generic 1R denominator** (price units) — ORB sets = range_w; scalper sets = stop distance |
| `realized_R`, `realized_pnl_usd` | outcome |
| `meta` (JSON) | **strategy-specific context** — ORB: `{or_high, or_low, range_w}`; scalper: its own |

`realized_R = (exit_px − entry_px)·sign(dir) / risk_unit` — derived on the join, EA file stays raw.

**Why generic:** one `ingest_tester_trades` + one differ serve ORB *and* every future scalper.
Strategy-specific fields live in `meta`, never as first-class columns.

---

## One contract, two sinks (design once)
The same Feed-B row shape serves both worlds:
- **Tester** → `tester_trades` (research.db, Gate 7 fidelity).
- **Live** → `d3_trades` (execution.db, via the task-35 HistoryDeal adapter).

---

## Build order
1. **Task 55** — migration 024: generalize `tester_trades` (ticket+entry_ts join, `meta` JSON, `lots`). *First — defines the contract.*
2. **Task 54** — buffered Feed-B writer (own lean `.mqh`) + recompile EA.
3. **Task 46 / 43** — streamed `ingest_tester_trades` + `run_and_verify.py` harness → 5-line verdict.
