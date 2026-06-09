# Event-Cache Layer A — Design Note (2026-06-09)

**Status:** design only — no code until Syafiq approves this note.
**Problem:** every ORB task (13/14/15/22…) re-scans the full 24GB tick parquet tree from scratch — minutes per run, repeated dozens of times per sweep. Biggest time sink in the project.
**Goal:** scan the ticks once into a tiny causal intermediate; run every variant (anchor, window, stop, trail, fill-model) as a fast transform on it. Identical results, fraction of the time.

---

## Why this does NOT introduce look-ahead / data leakage

Caching is memoizing a deterministic transform. **Look-ahead comes from the logic (using future info, or fitting on data you shouldn't see), not from when a value is computed.** A causal transform stays causal when read from disk. Safe as long as we honour three rules:

1. **Store only causally-computed, point-in-time facts.** Per day: the session price path and levels derived only from data within that day, in time order. No field references a future timestamp.
2. **Never cache a full-sample-normalized feature.** No z-scores/means/stds over the whole sample (the classic leak). Cache **raw** values (prices, levels, widths); any normalization happens at use-time with IS-only / expanding windows.
3. **Preserve date + IS/OOS flag; slice at read-time.** Cache carries each row's date. Every fitting step still filters `< 2024-05-02` exactly like today. The cache never merges IS and OOS.

---

## Two layers (Layer A is the cheat code; Layer B optional)

### Layer A — session-slice cache (universal, leak-proof)
Pure causal data **reduction** — drop the ~95% of ticks outside the trading session; keep only what any ORB variant needs.

- **Grain:** one row-group per UTC day.
- **Window:** **07:00–22:00 UTC** mid-price path (LOCKED 2026-06-09). Covers London anchors 08:00/08:30/09:00 + EOD 21:00 exit, with headroom for Frankfurt-open (07:00) and the ORB-002 NY-session variant — so adding an anchor never forces a full 24GB rebuild. The dropped slice is the thin Asian session; the speedup is mostly *structural* (compact pre-sliced/pre-grouped columnar read) rather than raw row-count reduction.
- **Columns (raw only):** `date`, `ts_utc`, `mid` (= (bid+ask)/2), `bid`, `ask` (keep bid/ask so half-spread fills + slippage/gap models stay exact), `is_oos` flag.
- **Resolution:** full tick within the session window — do NOT downsample (fills/breakout timing depend on tick granularity; downsampling would change results). The win is dropping out-of-session rows + pre-aligning by day, not thinning ticks.
- **Format/location:** partitioned parquet under `data/parquet/session/` (mirrors existing `daily/` cache convention), utf-8, gitignored (it's derived data).
- **Consumers:** the OR-builder + breakout detector run on this slice for ANY (anchor, window, stop, exit, fill-model). Replaces the raw `_tick_files` full-tree scan in [orb_core.py](../research/models/orb/orb_core.py).

### Layer B — per-config trades/events table (DEFERRED 2026-06-09)
The resolved trades for ONE fixed config (anchor/window/stop/exit). Would cache to re-run the SAME config's OOS / fill-stress / MC without recomputing. **Deferred** — A delivers the bulk of the speedup; B adds cache-invalidation failure surface with no evidence yet that we re-run identical configs often enough to justify it (rule 8). Revisit only if fixed-config re-runs stay a bottleneck after A.

---

## Trust guard (non-negotiable)
`--verify` mode: rebuild N random days from raw ticks and assert byte-equality with the cache. Divergence → halt (cache stale/corrupt). Same philosophy as the existing "control repro" gate in [trail_oos.py](../research/models/orb/trail_oos.py) (reproduce IS reference E[R] before proceeding) — extend it to the cache layer. First run after any data change must verify before trusting.

---

## Proposed files (when approved)
- **New** `research/code/session_cache.py` — builder (`build_session_cache`), loader (`load_session_day`/`iter_session_days`), `--verify`.
- [research/models/orb/orb_core.py](../research/models/orb/orb_core.py) — `_tick_files` consumers read the cache instead of raw parquet.
- [anchor_sweep.py](../research/models/orb/anchor_sweep.py) + [trail_oos.py](../research/models/orb/trail_oos.py) — swap raw scan → cache read; keep control-repro gate.
- `.gitignore` — add `data/parquet/session/`.
- research.db — close/extend backlog task 7; log architecture decision (CLAUDE.md rule 11).

## Out of scope here
- Actual code (this is the design note).
- Layer B (defer unless we find we re-run fixed configs a lot).
- Any change to IS/OOS boundary (2024-05-02 stays sealed).

## Decisions (LOCKED 2026-06-09, Claude's call — Syafiq delegated)
1. **Session window = 07:00–22:00 UTC** — headroom for Frankfurt/NY-session + ORB-002, scan-once safe.
2. **Layer A only**; Layer B deferred (YAGNI / rule 8).

Build sequence: `session_cache.py` (+ `--verify`) → repoint [orb_core.py](../research/models/orb/orb_core.py) → swap [anchor_sweep.py](../research/models/orb/anchor_sweep.py) + [trail_oos.py](../research/models/orb/trail_oos.py) to cache reads (keep control-repro gate) → then Task 22 runs on top of it, fast.
