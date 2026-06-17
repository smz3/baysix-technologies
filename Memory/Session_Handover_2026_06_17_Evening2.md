# Handover — June 17, 2026 Evening2

## State
- **BRC MT5 emitter is CODE-COMPLETE (6/6 files) and compiles clean** (a `.ex5` appeared from a MetaEditor build before the rename → it compiled). All in `brc_system` namespace, lowercase snake_case ([[mql5_lowercase_filenames]]).
- **Files:** EA = [brc_baysix.mq5](mt5/Experts/brc_system/brc_baysix.mq5) (renamed from brc_emitter this session). Includes: [brc_types.mqh](mt5/Include/brc_system/brc_types.mqh) · [brc_swings.mqh](mt5/Include/brc_system/brc_swings.mqh) · [brc_breakouts.mqh](mt5/Include/brc_system/brc_breakouts.mqh) · [brc_zones.mqh](mt5/Include/brc_system/brc_zones.mqh) (Path-B 5-pointer core, built this session) · [brc_lifecycle.mqh](mt5/Include/brc_system/brc_lifecycle.mqh) · [brc_csv.mqh](mt5/Include/brc_system/brc_csv.mqh).
- **Versioning:** `#define BRC_VERSION "1.0.0"` in brc_types.mqh = single source — printed at OnInit, mirrored in `#property version`, baked into CSV name `brc_zones_XAUUSD_dukas_v1.0.0_<ts>.csv`. Filenames stay unversioned (git SHA + define = real VC). [[brc_terminal_junction_deploy]].
- **Deployed:** `brc_system` junction-linked into JM terminal (E7DB) Experts+Include — [[brc_terminal_junction_deploy]]. Visible in MetaEditor after Navigator→Refresh.
- **Design decision — chronological reconstruction:** brc_zones rebuilds the skeleton BACKWARDS from P4 ("last…before"), so freshness collapses to "P3 = last swing before P4" and there is NO look-ahead. This will NOT byte-match vectorized [zones.py](research/models/brc/brc001/zones.py) — that delta IS what the fidelity-diff measures. MT5 = oracle.
- **Symbol LOCKED = `XAUUSD_dukas`** (2.0 GB ticks, full 2016→Jun 2026, UTC import, Digits 2, chart mode = BID). `XAUUSD_pq` rejected (33 MB parquet slice 2024-05→2026; parquet retired for unsorted-tick look-ahead).
- **Open caveat (bid vs mid):** EA detects on `XAUUSD_dukas` BID bars; Python detects on Arctic MID bars. Near-constant shift, mostly cancels in swing/break geometry — flagged, not solved.

## Next
1. **Syafiq compiles `brc_baysix` in MetaEditor** (recompile after rename) → fix any first-pass errors → short Visual-Mode run on M5 XAUUSD_dukas.
2. **Verify D1 boundary alignment** (the make-or-break check): compare MT5 `XAUUSD_dukas` D1 OHLC vs Arctic mid anchors (2024-01-03 O=2070.43/H=2070.75/L=2031.83/C=2037.97; 2025-01-02 O=2625.85/H=2651.14/L=2621.78/C=2647.69; 2026-01-02 O=4325.80/H=4402.32/L=4324.34/C=4353.65 — Arctic `daily_bars`, mid). MT5 is bid so expect ~half-spread lower; confirm SAME date + bar shape. Misaligned date ⇒ fix import UTC offset before trusting fidelity-diff.
3. **BUILD `brc_visual.mqh`** (NEW task — requested this session): draw swings (arrows), raw breakouts (markers), zones (L1↔L2 rect + mid dashed + T1/T2/T3 dots + invalidation marker). Mirrors orb `Visualizer.mqh`. ⚠️ needs tester Visual Mode, NOT "Open prices only". Distinct from task 117 (Python panel).
4. Then: Phase-3 fidelity-diff EA-D1 vs `detect_zones('D1')` → 10-yr run → ingest (task 119) → Python L2 funnel (task 120).

## Blockers
None. All compile-untested locally (no MT5 toolchain in Claude's env) — compile happens on Syafiq's machine. `brc_visual.mqh` (Next #3) logged as **task 121** [port|P2] ([[handover_nextsteps_must_be_tasks]]).
