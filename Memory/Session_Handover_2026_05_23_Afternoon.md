# Session Handover — May 23, 2026 (Afternoon — IB-001 logged + idea-bank rebuilt as YAML→DuckDB system, ADR-0002)

## What Was Accomplished This Session

### 1. Designed IB-001 — the first real pipeline idea (Step 1, discuss-only first, then logged)
Long discussion with Syafiq pressure-testing a new strategy. Final shape:
- **Idea:** XAUUSD short-horizon edge, cost-survivable. Just Markets MT5, Pro account, $50 seed, 1:3000 dynamic leverage.
- **"HFT" explicitly dropped** — retail MT5 cannot run true HFT (no colocation, Fill-or-Kill rejects, broker throttles EA/HF). Executable band = scalping→intraday.
- **H1 (alpha):** short-horizon inefficiency (mean-reversion OR momentum) at *some* horizon between seconds and hours, per-trade expectancy positive **after the JM floating spread**, IC stable + significant (t-stat > 2) IS→OOS. Optimal horizon is a research OUTPUT (variance-ratio horizon scan decides), not assumed. Leverage/capital irrelevant to H1.
- **H2 (deployment):** fractional-Kelly sizing under JM's dynamic leverage tiers; the tier schedule (1:3000 <$1k → 1:500 >$30k) is a built-in risk taper matching log-optimal de-levering.
- **Objective anchor (locked):** maximise log-growth rate g **subject to P(ruin) < 5%**. "Grow $50 fast" and "don't blow up" are ONE objective under log-utility (log 0 = −∞ punishes ruin infinitely). Kelly fuses them.
- **Kill condition (written first), 3-part:** (1) variance ratio indistinguishable from random walk at all scanned horizons; (2) mean per-trade expectancy ≤ 0 after JM spread haircut; (3) IC t-stat < 2 IS→OOS after multiple-testing deflation for the horizon scan. Any one fails → graveyard.
- **Triage 3.75 → queued.** Family = TBD (test decides trend vs mean_reversion).

### 2. Cost model + data pinned down (from Syafiq's broker spec screenshots)
- **JM Pro XAUUSD:** spread-only cost (no commission, swap-free). Avg spread **2 pips ≈ $0.20** (working assumption 1 pip = $0.10 on the 2-digit quote; confirm on live Market Watch). Stop level 0 BUT spec warns it throttles HF/EA. Sessions Mon 01:02–Fri 23:58 **GMT+3**, daily break 23:58–01:01. News throttles leverage 15min before→5min after.
- **Data uploaded:** `step2-dataset/2026.5.23XAUUSD_dukascopy-TICK-No Session.csv`, **20.94 GB**. Schema VERIFIED `DateTime,Bid,Ask,Volume`, ms timestamps, starts 2016-05-23, **3-decimal prices**. Dukascopy source (ECN, discovery feed) ≠ JM Pro (live) → **transfer risk handled by a spread haircut + masking break/news windows**. Dukascopy=UTC, JM=GMT+3 → shift before any session logic. "No Session" = unfiltered; we apply the mask.
- The CSV is now **git-ignored** (`step2-dataset/*.csv`) — never commit the 20GB tape.

### 3. Rebuilt the idea bank as a YAML→DuckDB system (ADR-0002) — committed + pushed
Syafiq rejected hand-edited markdown (agents writing prose, not queryable, sample entries read as instructions, mis-numbered IB-005). Built the real thing, no phasing:
- **[ADR-0002](../workspace/baysix-engine/alpha-engine/adr/0002-idea-bank-storage.md)** (Accepted) — idea bank gets the ledger treatment: YAML files = source of truth → DuckDB index → generated markdown view. Extends ADR-0001's `signals`/`trials`/`datasets` spine, does NOT fork it.
- **[core/idea_bank/signals.py](../workspace/baysix-engine/alpha-engine/research-engine/core/idea_bank/signals.py)** — mirrors `ledger.py` (stdlib + PyYAML only). `load_ideas`/`validate` (typed enum + required-field contract that *raises* — kills agent prose sprawl, no freeform notes field), `rebuild` (idempotent drop+repopulate), `render` (generated dashboard). Run: `python core/idea_bank/signals.py` from research-engine/.
- **[schema.sql](../workspace/baysix-engine/alpha-engine/research-engine/core/db/schema.sql)** — extended `signals` (triage_*, objective, universe/frequency/capacity, data_ref soft-FK) + new `signal_hypotheses` child table. Status vocabulary reconciled to the funnel set (`queued|testing|live|parked|backlog|graveyard`) — was a real bug (schema said `idea|active|dead|live`).
- **[IB-001.yaml](../workspace/baysix-engine/alpha-engine/research-engine/step1-idea-bank/ideas/IB-001.yaml)** — the idea above, full detail (horizon_scan, data provenance, next_action all in YAML).
- **Tests:** 19 → **32 green** (+13: validation rejection of every bad-input class + YAML→DB→render round-trip). PyYAML 6.0.2 pinned in pyproject.

### 4. Cleanup (Syafiq's request — step1 must be content-only)
- **step1-idea-bank/ is now content-only:** `ideas/IB-001.yaml` + `IDEA_BANK_TEMPLATE.md` (now a static reference doc) + `DASHBOARD.md` (generated). No scripts, no tests, no `__pycache__`.
- Machinery → `core/idea_bank/` (with corelib/db/tools).
- **b2b-xauusd (21 files, code+evidence) moved step1 → step3-is-rapid-fire/strategies/b2b-xauusd/** (where its IC gets measured). The old IB-001-b2b sample entries are gone.
- All path/command references updated (ADR, schema comment, template, YAML, dashboard banner).

### 5. Committed + pushed to baysix-engine
Commit `8ed3aab` on `main`, pushed to `github.com/smz3/baysix-engine` (`acb8d41..8ed3aab`). Includes today's work + last session's stale IB-001-b2b wipe (run stubs + scoreboards) finished.

---

## What Is NOT Done / Still Open

- **Step 2 not started.** The 20.94GB CSV is uploaded but nothing has touched it. Next is the Step-2 honesty audit (see priorities).
- **No `/log-idea` writer skill built.** Ideas are hand-written YAML for now; deferred until idea #2 appears (Syafiq agreed).
- **JM pip definition unconfirmed** — working assumption is 1 pip = $0.10 (spread ≈ 20¢). Syafiq to eyeball live Market Watch (ask−bid in price terms) to confirm before the haircut is finalized.
- **Zero real data has ever run through the pipeline.** Foundation is tested on synthetic inputs only. IB-001 will be the first real end-to-end test — expect plumbing friction.
- **B2B is no longer a logged idea** — its code/evidence live in step3 but it has NO idea-bank entry. If Syafiq wants to pursue it, it needs its own IB-NNN.yaml.

---

---

## EVENING UPDATE (2026-05-23) — Step 2 converter built + 21GB tape converted

### Done this session
- **Converter built: [core/dataset/ticks.py](../workspace/baysix-engine/alpha-engine/research-engine/core/dataset/ticks.py)** — streams tick CSV → Hive-partitioned Parquet (`year=YYYY/month=M/`) via DuckDB COPY, memory-capped 4GB (spills to `parquet/.duckdb_tmp`, no OOM). Converts ONLY — no clean/mask/seal (those read this Parquet next). Column `ts_utc` keeps tz explicit; prices 3-decimal intact; volume = tick-vol proxy carried as-is. Run: `python core/dataset/ticks.py` from research-engine/.
- **+3 tests** ([core/dataset/tests/test_ticks.py](../workspace/baysix-engine/alpha-engine/research-engine/core/dataset/tests/test_ticks.py)): parse, partition layout, value round-trip. Suite **32 → 35 green**. Added `core/dataset/tests` to pyproject testpaths.
- **Full convert ran clean (109s):** `step2-dataset/parquet/CS-GOLD-DUKAS-TICK/` — **511,145,204 rows**, span 2016-05-23→2026-05-18 (matches), **0 null timestamps**, **121 month-partitions** (= calendar exactly), 21GB→**3.1GB** zstd. Parquet git-ignored (`*.parquet`).

### Series naming clarified
- IB-001's tape is a **NEW** series `CS-GOLD-DUKAS-TICK`. The registry's existing `CS-GOLD-JM-H1` is a DIFFERENT old H1 file (B2B). Dukascopy-as-JM-proxy was decided last session; spread haircut handles the feed gap.

### NOT done / open decisions for next session
- **NOTHING COMMITTED YET.** Converter + tests + pyproject edit are unstaged on `main`. First action next session: review + commit (converter is a clean self-contained unit, 35 green).
- **Validation gate NOT built** — this is the real honesty audit (the "landmines"). MUST discuss design before writing. Two traps flagged: (1) **Dukascopy spread ≠ JM cost** — Dukascopy spread histogram = data-QUALITY mask only; the cost haircut uses JM's ~20¢/2pip number. Never cross them. (2) **Timezone DST** — JM server offset is GMT+2↔GMT+3 with US DST, NOT a constant +3; session mask (Mon 01:02–Fri 23:58) + daily break (23:58–01:01) must shift DST-aware or it's an hour off ~5mo/yr.
- **OOS seal still honor-system** — schema has `oos_budget` table but DATA_MACHINERY lists OOS vault "not built". Decide: wire load-time touch-counter now, or documented honor-system for IB-001. Split date + by-calendar-vs-by-trade-count still to pre-register (10yr tick, density non-uniform).
- **Make cost model take pip as an INPUT** (not hard-coded 20¢) so Monday's live confirm is a one-line change.

---

## Running Processes

None. (Convert finished, exit 0.)

---

## Priority for Next Session

1. **Commit the converter** (unstaged: ticks.py, test_ticks.py, pyproject testpath, core/dataset/__init__.py).
2. **Discuss → build the validation gate** — monotonic ms timestamps, crossed quotes (bid≥ask), spread histogram (QUALITY mask only — see traps above), coverage histogram 2016→2026, DST-aware UTC→JM-server shift + session mask. THEN **seal OOS** (pre-register split before any peek) + register `CS-GOLD-DUKAS-TICK` in `datasets` table. (a)/(b) already DONE this session.
3. **Then the first real measurement: variance-ratio horizon scan** (Lo–MacKinlay + short-lag autocorrelation) across 1s/5s/30s/1m/5m/15m/1h, spread-cost overlaid at each, multiple-testing deflated. This resolves H1's mechanism (trend vs mean_reversion vs random walk) and the optimal horizon. It is the gate that either gives a mechanism or kills IB-001.
3. **Confirm the JM pip/spread number** with Syafiq so the haircut is anchored on a real figure, not the 20¢ assumption.

---

## Key Decisions Made

- **Idea-bank storage = YAML SoT → DuckDB index → generated MD (ADR-0002).** Hybrid chosen over DB-only (no git review) and MD-only (no trial-count denominator). YAML over JSONL because ideas are nested human-edited documents, not flat machine events. One conscious dependency (PyYAML), pinned, tooling-layer only.
- **Build it right, no phasing** — Syafiq explicitly rejected half-build-then-upgrade. Full system built in one pass: machinery is generic enough that datasets/runs adopt the same pattern later with zero rewrite.
- **Extend ADR-0001, never fork it.** Reused `signals`/`trials`/`datasets`; trial-count denominator stays in the ledger (`research-ledger/`), not duplicated.
- **step1 = content only; machinery in core/.** Syafiq's taste: no loose scripts under a step folder.
- **HFT is off the table for retail MT5** — the strategy is scalping→intraday; horizon is discovered, not assumed.
- **Leverage is NOT an edge.** It only removes margin as the size constraint. The research question (H1) is edge-net-of-cost; leverage/capital are H2 (deployment) only.

---

## Blockers

None. Step 2 is ready to start — the data exists and is git-safe.

## Process notes (honor next session)
- Run pipeline Python from `research-engine/` with `./.venv/Scripts/python.exe`. `python -m pytest -q` must stay green (now **35 tests**).
- Idea bank: edit `step1-idea-bank/ideas/IB-NNN.yaml`, then `python core/idea_bank/signals.py` to validate + rebuild DB + regenerate DASHBOARD.md. Never hand-edit DASHBOARD.md.
- baysix-engine is ONE git repo (`main`, pushed); sigma-brain is separate (`master`). Commit research code to baysix-engine, handovers to sigma-brain.
- Discuss-before-build still in force ([[feedback_discuss_before_build]]). Brevity mandatory ([[feedback_brevity_delivery]]). Spell out abbreviations in research docs ([[feedback_doc_abbreviations]]). ADR for major component decisions ([[feedback_adr_governance]]). Confirm before irreversible/outward actions.
