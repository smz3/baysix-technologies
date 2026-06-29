# Handover — June 29, 2026 Afternoon2

## State
- **Task 193 DONE — FOB path-A capture CSV built.** [fob_csv.mqh](../mt5/Include/fob_system/fob_csv.mqh) now emits ONE wide row/event (`fob_capture_<sym>_<runid>.csv`, **45 cols**), replacing the old 17-col birth-only row. TIER A+B **values** + TIER C **headers** (deferred). Compiled **0 errors** (emitter + trader; only benign Market `xxx.yyy` warning).
- **Lifecycle now stamped onto the CSV:** [fob_lifecycle.mqh](../mt5/Include/fob_system/fob_lifecycle.mqh) `FobReplayZoneLife` extended to also compute `n_l1/mid/l2_touches` (rising-edge), `bars_alive`, `vr_fresh`; [fob_baysix.mq5](../mt5/Experts/fob_system/fob_baysix.mq5) OnDeinit replays each event's zone over its event-TF buffer before writing (VR rows track RT).
- **htf_state** = RAW per-TF live-cycle `{dir,cf}` JSON of all 9 TFs, stamped CAUSALLY right after each `FobClassifyBreak` (frozen #2). RFC4180-quoted in CSV.
- **body_clears repurposed** (was a useless constant 1) → now a real **full-body impulse** flag: plumbed the breaking bar's **open** through detection + recorded it raw (new `bar_open` col). `body_clears = opened already beyond L1`.
- **Phase-2 = structurally ready, waiting on data only.** `fob_zones` already has `confirm_time/confirm_price/continued/mfe_r/mae_r/realized_r/zone_key/is_primary/superseded_by` (migration 035, verified live). CSV emits them as empty headers. §5 sharpeners (distance/setup-type/regime/ML labels) ride in `meta` JSON, not columns.
- `FOB_VERSION` → **1.21.0**; emitter + trader `#property` in lockstep. All committed + pushed.

## Next
1. **(task 191, P1)** Build `ingest_fob` in [tester.py](../research/code/io/tester.py): wide `fob_capture_*.csv` → `fob_cycles`/`fob_events`/`fob_zones`, `idea_id='FOB-001'`, reconstruct cycle linkage by grouping `(setup_tf, seq)`. **Decide `bar_open`'s home** (no `fob_events.bar_open` col → `meta` JSON, or rely on derived `body_clears`).
2. **(task 190, P1)** Run `fob_baysix` emitter: XAUUSD_dukas, 8 TF, 2016–2024, Open-prices → produces the capture CSV.
3. **(task 192, P1)** Re-screen storyline-alignment on FOB OWN zones; pin run_id + assert `idea_id='FOB-001'`.
4. **AUDIT (do first):** inspect this session's CSV-contract work for gaps before trusting the first emit — see Live-Threads for the specific judgment calls.

## Blockers
- None.

## Why
- **body_clears was caught as nonsense by Syafiq** — close-based detection guarantees the close cleared the level, so the column was a constant 1 (zero info). Repurposed rather than dropped: recording the break-bar **open** lets `body_clears` distinguish a strong full-body impulse break from a weak closing break. Principle Syafiq set: *record everything the code computes, for rich data.*
- **`bar_open` rides on the `FobZone` payload, not threaded through the classifier** — the zone struct already travels intact through `FobClassifyBreak`/`FobAppendEvent`, so putting `bar_open` there avoided changing 2 more signatures. Semantically slightly muddy (it's a break-bar fact, not zone geometry) but documented in [fob_types.mqh](../mt5/Include/fob_system/fob_types.mqh).
- **Lifecycle is REPLAYED at emit, not stored live** — `g_events[e].zone` only holds break-time geometry; the visual layer replays lifecycle into a chart-TF-only copy. So OnDeinit re-runs `FobReplayZoneLife` per event over its own event-TF buffer. Same stateless function the chart uses → CSV and chart can't disagree.
- **Phase-2 deliberately NOT executed** — Syafiq confirmed schema+columns are set, just waiting on data. `realized_r` value is frozen-deferred because its denominator must inherit the trader's real L2-stop rule at sim time; the emitter has no entry/stop concept.

## Ruled-Out
- **body_clears as a constant `1`** — REJECTED this session (uninformative under close-based detection). Replaced with the open-vs-L1 full-body flag. Do not revert to constant.
- **Threading `bar_open` through `FobClassifyBreak` → `FobAppendEvent`** — rejected in favour of the zone-payload transport (fewer signature changes, same result).
- **Storing `htf_state` as interpreted TF direction** — already rejected last session (frozen #2); kept RAW `{dir,cf}` snapshot. Not revisited.

## Live-Threads
- **AUDIT TARGETS — judgment calls I made that need Syafiq/next-agent eyes before the 8yr emit is trusted:**
  1. **`vr_fresh` definition** = `no post-break bar CLOSED back inside [L1,L2]` (my literal read of "no close back into the VR zone"). Computed for ALL zones, emitted only on VR rows. **Confirm this matches the manual's Fresh/Not-Fresh mental model** — if wrong, it mis-flags the single most important behavioural bit.
  2. **`vr_made_first_tf`** = I emit the `event_tf` that made the VR (literal "which TF made this VR"). The cross-TF "which fired FIRST when two break together" comparison is left to ingest/analysis from `bar_time`+`event_tf`, NOT baked in MQL5. Confirm that's the intended split.
  3. **Touch COUNTS** use rising-edge hysteresis (one episode per distinct return to a level), NOT a per-bar tally. Reasonable but unverified against intent.
  4. **`body_clears` semantics** = full body = open beyond L1. An alternative reading ("body size vs wick") was not taken. Confirm.
- **`bar_open` has no `fob_events` column** — ingest (task 191) must decide: drop, or stash in `meta`. Flagged, not blocking.
- **`instruments` table** still designed-not-created; needed before the first FOB *trader* $ run (not blocking the emitter chain).
- **Storyline numbers in [storyline-alignment findings](../docs/specs/2026-06-27_fob_storyline_alignment_findings.md) are still VOID for FOB** (computed on BRC-contaminated `tester_zones` run_id 5) until task 192 re-screens on FOB own zones.
