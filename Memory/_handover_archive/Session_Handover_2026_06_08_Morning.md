# Handover — June 8, 2026 Morning

## State (one line)
ORB-001 London variant-mining continued: tasks 9/14/16 resolved, **deploy config UNCHANGED** (frozen Mode A min-lot, 5% cap, immediate 08:05 entry, range_w 1R stop, 3:1 target). Every IS-strong alt reduced to the same fault line — gold's 2016–26 uptrend. Also **fixed the broken SessionStart hook** so the backlog now auto-surfaces every session.

---

## What was done this session

**Task 9 — structure/entry variation sweep** ([structures.py](../research/models/orb/structures.py), IS n=2046, control reproduced +0.3114R):
- **trail_1R = +0.7910R** (t+11.30, win 44%) — trailing stop 1 range_w behind the running peak nearly TRIPLES E[R]. Best alt found all session.
- **retest_3R FALSIFIED −0.2019R** — 3rd independent confirmation that any delayed/pullback entry kills the edge (after M15-confirm + entry-delay). Immediate 08:05 entry is now ironclad.
- breakeven_1R +0.28, partial_1p5R +0.21 (both below base). Range-width edge non-monotonic: Q3 ($1.0–1.7) best +0.47R, Q4_wide worst +0.21R.
- trail_1R NOT adopted: IS-only + breaks the fixed-3R/1R payoff the whole deploy package rests on → **task 13** (OOS + survival/DD re-run).

**Task 14 — stop-placement sweep** ([stops.py](../research/models/orb/stops.py), 9 arms, control OK):
- **CRITICAL CATCH: the E[R] ranking is a DENOMINATOR ILLUSION.** Tighter stop → higher E[R] purely because R is normalised by the stop. fixedpip_$0.5 had the BEST E[R] (+0.41) and the WORST dollars (+$0.20/trade). **Never select a stop on E[R] — use $/trade.** stops.py now reports $/trade.
- On $/trade: fixedpip_$2.0 wins +$0.4956 (+53% vs frozen +$0.3236) and is fill-robust (wide). BUT it risks $2.00/trade vs $1.60 (4% vs 3.2% of $50) → worsens the 33% DD floor, and a wide fixed stop just harvests more of gold's uptrend (trend-beta). → **task 21** (survival/DD + OOS gate).
- rangefrac_0.75 weakly dominates base (more $, less risk, vol-proportional) but +0.34 vs +0.31 E[R] is within ~1 SE — not significant. **Frozen range_w stop is NOT meaningfully beaten by a small tweak.**
- ATR-stop arm deferred on purpose: range_w IS itself a per-day vol measure, so rangefrac_* already covers vol-proportional stops.

**Task 16 — long/short asymmetry** ([direction.py](../research/models/orb/direction.py), pooled IS reproduced +0.3114R):
- IS: long +0.4286 (t+7.48) vs short +0.1793 (t+3.12); asym +0.2493R, **p=0.002**. OOS: long +0.9785 (t+8.34) vs short +0.7560 (t+6.02); asym +0.2224R, p=0.196.
- **CATCH: the script's auto-verdict wrongly called the IS asymmetry "selection noise."** It REPLICATED OOS — same sign, near-identical magnitude; p=0.196 is just OOS being underpowered (1/4 the n), not a contradiction. I corrected the verdict logic in direction.py and re-ran.
- **Decision: STAY SYMMETRIC at $50.** Both sides independently profitable IS+OOS, so long-only forfeits a profitable ~47% of trades + halves trade count (worse compounding) + is an implicit trend-up bet (fragile). Asymmetric sizing is infeasible at min-lot 0.01 anyway — it's a larger-account lever. This task CLOSES cleanly (no $50 follow-up).

**Backlog scoping** — mapped the genuinely-untested ORB-001 London axes into tasks **14–20** (stop-placement, anchor/OR-window timing, direction, range-width filter, day-of-week, re-entry, failed-breakout fade). Used the embedded-markdown-checklist-in-`detail` pattern (no schema change). Did NOT duplicate the regime filter — already open as task 5.

**Startup robustness fix** (your request): the old SessionStart hook `cat`-ed dead `baysix-engine/...` paths and never touched the DB. Replaced it with [session_brief.py](../.claude/hooks/scripts/session_brief.py) → prints live `open_backlog` + recent resolved + latest results every session. Added a 4-step Startup block to [CLAUDE.md](../CLAUDE.md) making "check open_backlog before proposing work" explicit.

---

## The meta-pattern (most important takeaway)
Three separate IS-strong signals this session — **trail_1R (+0.79R), fixedpip_$2 stop (+53% $), and the long-side tilt** — ALL reduce to one thing: **exposure to gold's 2016–26 secular uptrend.** The robust, regime-agnostic frozen config keeps winning on the metrics that matter ($/survival). Treat any new IS variant that "lets winners run" or "widens/biases long" as suspected trend-beta until proven on OOS + through a regime split. This is why the highest-value remaining work is the regime lens, not more variants.

## Next (priority order)
1. **Task 13 (P1)** — trail_1R OOS + survival/DD re-run. Highest upside (could ~3× E[R]) but most exposed to the trend-beta caveat. Scrutinise trail fill realism (task-12 lesson).
2. **Task 5 (P2→treat as P1)** — regime gate (trend/session filter). Directly tests whether the OOS>IS gap is trend-beta or real. De-risks everything above.
3. **Task 21 (P2)** — fixedpip_$2 stop survival/DD + OOS (does +53% $/trade survive the higher per-trade risk at $50?).
4. **Task 15 (P1)** — anchor/OR-window timing sweep (08:00 UTC is an untested assumption; note Dukascopy 07–08 UTC maintenance gap makes <08:00 unobservable — see orb_core docstring).
5. **Task 17 (P1)** — productionise the Q3 range-width filter + OOS confirm.
6. Untouched: **Task 3 (P1)** ORB-002 NY (own gate ladder from G0). DEFERRED by Syafiq: task 4 MQL5 port (live money). PARKED: task 11 open-spread.

## Bookkeeping / ground truth
- This session: log_human_decision call_ids **22, 23, 24**; step4_results **48** (stop $/trade), **49** (trail_1R backfill), **50** (direction asym). All non-agent (human+Claude) runs.
- Backlog is the source of truth — query `open_backlog` view, NOT just this handover. SessionStart hook now prints it automatically.
- All work committed + pushed to master (latest: direction.py + hook fix).

## Blockers
None.
