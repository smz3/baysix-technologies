# Session Handover — 2026-06-12 Afternoon3

## Theme
Token-efficiency triage → built the MT5 ⇄ research.db **fidelity flow** infrastructure
(scalping-ready). Started as "why are we burning session limit fast?", became the
permanent fix: a token-firewall data pipeline.

## What we did (all shipped + pushed)

### Diagnosis (the original question)
Token burn culprit = reading raw MT5 tester output (xlsx/CSV trade lists) straight into
context, where it lingers and re-sends every turn. Fix = a pipeline where **only a ~5-line
aggregate verdict ever reaches Claude**; unbounded trade data stays below a "firewall"
handled by scripts at $0. Cheat codes: never Read a CSV/xlsx; never `SELECT *`; scripts
(not smaller models) for deterministic parsing; smaller models only for read-many/return-little.

### Design-of-record — [braindump/mt5_fidelity_flow.md](braindump/mt5_fidelity_flow.md)
The locked flow. EA writes clean per-trade CSV (**Feed B**, authoritative) → stream-ingest
to research.db → Claude reads only the aggregate verdict. xlsx (**Feed A**) demoted to
run-summary + cross-check. One contract, two sinks: `tester_trades` (research) + live
`d3_trades` (execution).

### Task 55 ✅ — generalized `tester_trades` (migration 024)
ORB-shaped → strategy-agnostic. session_date demoted to nullable (was the join key, broke
at >1 trade/day); **join now ticket + entry_ts**. or_high/or_low/range_w → generic `meta`
JSON; +`lots`; +indexes (run_id, run_id+entry_ts). risk_unit stays the generic 1R.
**527 ORB-001 rows preserved.** tester.py schema + `ingest_tester_trade(meta=, lots=)` updated.

### Task 54 ✅ — Feed B per-trade CSV writer
[mt5/Include/orb_system/orb_trade_csv.mqh](mt5/Include/orb_system/orb_trade_csv.mqh) — my
own lean buffered `CTradeCSV` (NOT the MQL5 article download — Syafiq found article 22902,
we cherry-picked the buffering idea only; its OnTester workflow is run-level, wrong granularity).
FILE_COMMON; ';'-delimited (JSON meta needs no escaping); flush every InpTradeFlushN=50 +
OnDeinit; retry/backoff on share-lock. EA wired: `OrbTradeRec` captured at entry,
`RecordTradeClose()` pulls exit_px+net PnL from `HistorySelectByPosition` deals — covers
**both** the trail/SL-hit exit (the common path, in ManageTrail) and explicit ClosePosition.
**Compiles clean (0/0), ex5 rebuilt 15:02.**

## ⚠️ Open / next (P1, under existing tasks)
- **RUNTIME-UNVERIFIED**: task 54 compiles but no tester pass yet confirms the CSV lands +
  rows are correct. **This is the immediate next action** → run one ORB-001 tester pass,
  check `Common/Files/orb001_trades.csv`. Owned by **task 46**.
- **Task 46** — `run_and_verify.py` harness: drive tester headless → ingest Feed A + B →
  5-line verdict. Includes building **`ingest_tester_trades`** (streamed, sep=';', json.loads
  meta, join ticket+entry_ts) — that's also **task 43**.
- Then the real prize: ORB-001 Gate-7 fidelity diff (Python OOS vs tester) finally unblocked.

## Gotchas / notes
- MetaEditor64 (JustMarkets) returns **exit=1 even on success** — trust the compile.log
  ("Result: 0 errors"), not the exit code.
- research.db **is tracked in git** → prior state is the rollback (dropped my .pre024 backup).
- Feed B CSV is **;-delimited** — ingest must use `sep=';'`. Documented in the .mqh header.
- ORB exits are mostly **trail/SL hits detected in ManageTrail**, NOT ClosePosition — that's
  why the writer hooks both paths and reads deal history for the authoritative fill.

## Logged
tasks 54 + 55 → done; architecture decision → `log_agent` call_id 40 (ORB-001 gate 7).
Backlog still has the ORB sorted-tick re-validation P0/P1 (tasks 51/52/53) — untouched this
session, still open.
