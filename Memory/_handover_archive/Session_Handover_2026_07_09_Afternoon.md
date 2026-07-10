# Handover — July 9, 2026 Afternoon

## State
- **Task 261 DONE** — the two poisoned FOB payload columns are quarantined, committed, pushed. Verified end-to-end, not just written.
- `mfe_r`/`mae_r` are **NULL** in [data/fob_payload/run_19/zones.parquet](../data/fob_payload/run_19/zones.parquet) (0 non-null). Producer [derive_fob_excursion.py](../research/code/io/derive_fob_excursion.py) raises `RuntimeError` on entry.
- `confirm_time`/`confirm_price` → **`next_cf_time`/`next_cf_price`**. Labels only, zero logic change: 162,771 non-null and 766,067 rows before and after.
- Two guards live: `fob_payload._check_quarantine()` raises if a quarantined column is requested; `tester._assert_tier_c_unpopulated()` fails ingest if the emit CSV ever populates a Tier-C outcome column (also catches the legacy `confirm_time` name).
- Migration [036](../research/migrations/036_fob_quarantine_excursion_and_rename_confirm.py), idempotent. `fob_run_stats.mean_mfe_r` was already NULL — no rollup touched.
- **Nothing we trade changed.** The live H4-CF3 config came from the MT5 arbiter, never from these columns.
- New **CLAUDE.md rule 4a** (namespace discipline) — see Why.
- strategy_log **108** (FALSIFIED, the fill-gate root cause) + **109** (ADOPTED, the rename), then **110/111** correcting a lineage self-inflicted wound — see Why.

## Next
1. **(task 202, P1)** Fix [derive_fob_excursion.py](../research/code/io/derive_fob_excursion.py) — it EXISTS and is hard-stopped, it is not a greenfield build. Add: (a) **fill gate** — a zone is a trade only if price *touches* `l1` at or after the CF event `bar_time`; (b) **censoring** — sweep reaches end-of-data without a stop → NaN, never a value; (c) `SL = l2 ∓ 0.5·band`, not bare `l2`; (d) **R floor** (p0.1 of `R` = 0.007); (e) anchor always on CF `bar_time`, never `next_cf_time`.
2. **(task 263, P1 — NOT blocked on 202)** Zone-width contradiction on the MT5 arbiter: 2×2 A/B of `range_w` tercile {narrow, wide} × exit {fixed-RR2.0, trail}, real ticks, H4 CF3, session 12–23. Uses tester fills only.
3. **(task 262, P2)** Re-run the blocked-CF1 / `room_R` screen on the valid excursion once 202 lands, controlling for R. Then MT5 arbiter.

## Blockers
- **Tasks 260, 240, 245, 262 remain blocked on task 202** — no valid excursion measure exists. Unchanged.
- **Task 263 is NOT blocked** — it settles on tester fills, so it can run in parallel with 202.

## Why
- **Root cause of the bad excursion, and it is not what the last handover recorded.** [derive_fob_excursion.py](../research/code/io/derive_fob_excursion.py) has **no fill gate**: it assumes a limit fill at `l1` on the CF bar unconditionally. Measured on [run_19 zones.parquet](../data/fob_payload/run_19/zones.parquet), n=278,592 CF zones:
  - **39.1%** already had price **past `l1`** at the CF bar → never fills, never stops, sweep runs to end-of-data. 98.8% of the `mfe_r > 100` rows are these. Max `mfe_r` = 32,120 R = the 2016-24 gold bull, not a trade.
  - **56.0%** already had price **beyond `l2`** → stops on bar 0, so `mae_r ≤ −1` by construction. 96.0% of the `mfe_r < 0` rows are these.
  - ~95% of rows are one or the other. Unresolved sweeps also wrote a number instead of NaN.
  - **"An MFE cannot be negative" is a SYMPTOM, not the defect.** Do not re-diagnose from that framing.
- **Three factual corrections to the 2026-07-09 Morning2 handover, now in the DB:**
  1. The producer is `derive_fob_excursion.py` (task 246), **not** `ingest_fob_phase2` Part B. Task 202 is a *fix*, not a build — its `log_tasks` detail was rewritten to say so.
  2. `fob_zones`/`fob_events` SQLite are **empty** (task 229 cleared them). The parquet is sole truth, so "add an assert in `ingest_fob`" guards a door nobody walks through. The real chokepoint is `fob_payload.read_fob_payload()`. Both are now guarded.
  3. The `confirm_time` perfect-separation counts in that handover (1,624 / 1,937) were an H1 subset, not the population. On all CF zones it is 115,821 null / 162,771 non-null. The *claim* holds — it is non-null iff a later CF exists — and is true **by construction** from [tester.py](../research/code/io/tester.py) `derive_fob_confirm_linkage`, which sets it to the next same-cycle CF's `bar_time`.
- **Why rename rather than drop `confirm_time`.** It is the only cheap next-CF pointer, and the danger was never the value — it was the name. `next_cf_time` cannot be mistaken for a fill time. Syafiq confirmed: labels only, no logic change.
- **`strategy_log` lineage wound, self-inflicted and repaired — read this before logging infra work.** `VALID_COMPONENT` has no `data`/`infra` option, so I tagged the two task-261 data-integrity events `component='config'`. Because `get_live_config()` takes *the latest ADOPTED/VALIDATED row per component*, log 109 hijacked it and reported the traded FOB config as **a column name**. Log 110 tried to undo it with `SUPERSEDED` — that failed silently, because `_LIVE_VERDICTS` ignores `SUPERSEDED`. Log **111** (VALIDATED, result_id 25) restores log 90's value verbatim and `get_live_config('FOB-001')` now reads `cf3 k0.50 RR2.0` again. **Lesson: a data/infra event has no home in `log_strategy`'s component vocab — do not force it into `config`.** Either add a `data` component to `VALID_COMPONENT`, or log infra with `component=None`.
- **Why CLAUDE.md rule 4a exists.** Mid-session I grepped the bare column name `confirm_time` repo-wide, hit BRC's unrelated `tester_zones.confirm_time` (a different field, `p4_time`), and raised it as a scoping concern inside a FOB decision that had nothing to do with BRC. Syafiq: *"why in the hell is BRC doing in your suggestions?"* The collision was meaningless — CLAUDE.md already says FOB does not use `tester_zones`. `mfe_r` collides the same way (`research/models/brc/brc001/` computes its own), so it would have bitten again. The rule now names each system's namespace and states that a parked system surfacing in a live decision is **a bug in the search, not a finding**. Per [[enforcement_code_not_prose]], it lives in the repo, not in my resolve.

## Ruled-Out
- **`mfe_r`/`mae_r` as they stood — FALSIFIED, strategy_log 108.** Do not re-run `derive_fob_excursion.py` to "just get numbers"; it raises on purpose. Evidence: [run_19 zones.parquet](../data/fob_payload/run_19/zones.parquet) pre-quarantine (backup in the session scratchpad as `zones.parquet.pre261.bak`).
- **`confirm_time` as an entry anchor — BANNED, carried forward and now enforced in code.** A screen anchored on it produced a fake **t = +7.72** (discarded last session; see [Session_Handover_2026_07_09_Morning2.md](_handover_archive/Session_Handover_2026_07_09_Morning2.md) Ruled-Out). The column no longer exists under that name and `read_fob_payload` raises if asked for it.
- **"Add an assert in `ingest_fob`" as the *sole* guard — rejected as insufficient.** SQLite staging is empty; the assert was still added (it catches a future EA that starts emitting outcomes) but the load-bearing guard is at the parquet read boundary.
- **Dragging BRC into FOB scoping — rejected, now a code-adjacent rule (CLAUDE.md 4a).** Do not re-surface `tester_zones` in FOB work.
- **`realized_r` as an arbiter — still rejected as an instrument** (unchanged from last handover). Naive fixed-RR2.0 barrier sim; it cannot reproduce the live CF3 result (+$3.23/tr OOS, **result_id 50**). Rough baseline only.

## Live-Threads
- **Zone-width contradiction is now the loudest live thread and it is NOT blocked** (task 263, promoted to P1 this session). Narrow zones crush wide under the naive fixed-2R sim ([fob_zonewidth_Rtercile_2026_07_09.csv](../research/outputs/fob_zonewidth_Rtercile_2026_07_09.csv)) yet our own IS result says **wide** was good under the trailing exit (`H4_cf3_wideRange_net_usd_per_trade` = +2.73, **result_id 39** family). Hypothesis: **the sign flip is the EXIT, not the zone.** Settles on tester fills, so it does not wait for 202. Likely resolves tasks 259 and 250 as a by-product.
- **Blocked-CF1 hypothesis still SURVIVES** but is now *un-measurable* until 202 — its only instrument was `realized_r` plus the excursion we just nulled. Carry the two measurement traps into 262: (a) `corr(1/R, room_R) = +0.566`, so **always control for R** ([fob_room_r_wall_by_Rtercile_2026_07_09.csv](../research/outputs/fob_room_r_wall_by_Rtercile_2026_07_09.csv)); (b) `room_R > 0` for only 40% of entries — use the **far** band edge when entry sits inside the band.
- **Open question 202 must answer, not assume:** with a real fill gate, what fraction of CF zones are even *tradeable*? On run_19 only ~5% had price between `l2` and `l1` at the CF bar. If the true fill rate is that low, the H4-CF3 population we trade may be reached by a *different* entry mechanic than "limit at `l1`" — worth checking against what the TRADE-mode EA actually does before trusting 202's `n`.
- **Doc landmines, still not fixed** (carried, unchanged): [2026-06-27_fob_storyline_alignment_findings.md](../docs/specs/2026-06-27_fob_storyline_alignment_findings.md) has no warning banner but its §2 is void; [v0.2 entry-logic spec §6](../docs/specs/2026-07-02_fob_sequence_storyline_entry_logic_v0.2.md) points at retired `fob_trader.mq5`.
- **$50 rapid-scalp mandate still unscoped** (carried). Live H4-CF3 is a *swing* setup by the manual's own taxonomy. The one cheap falsifiable scalp claim remains the M30 reversal "cheat code" (imgs 6.5/6.6) — unclaimed.
