# Session Handover — May 25, 2026 (Morning-2 — JM venue spec, Layer 0 relocation + rename, IB-001 confluence hypothesis)

> Continues the earlier `Morning` handover (DuckDB schema fixes). This session did broker-spec capture, a structural cleanup, and shaped IB-001's hypothesis.

## What Was Accomplished This Session

### 1. Verified DuckDB schema matches BAYSIX_FRAMEWORK
Checked live `research.duckdb` (not just schema.sql). Tier-2 lock present and *enforced* (`METRIC_POLICY` in [signals.py](../workspace/baysix-engine/research-engine/core/lib/idea_bank/signals.py) mirrors the framework Tier-2 table; validator rejects illegal `(idea_type, asset_mode, primary_metric)`). `family_key` in both `signals` + `trials`. No fix needed. Clarified the metric→Sharpe bridge has no gap — it's a `metrics` row (`step=1, name='bridge_predicted_sharpe'`), not a missing column.

### 2. Rewrote [quant-researcher.md](../.claude/agents/quant-researcher.md) (was badly outdated)
Fixed a real bug: it instructed annualised Sharpe (`sqrt(365)`) — now per-period Sharpe with T=obs, t-stat `SR×√T`, PSR `(kurt−1)/4`. Embedded the quant-modeller Iron Laws inline (it can't call the skill from a spawned context). Wired to the real funnel (Tier 0/1/2 gates, N_min≥100, IS/OOS>0.5, DSR). Killed all dead `sigma-crypto/lean/mt5` paths → `baysix-engine`. quant-modeller skill needs no change (already current).

### 3. Built the broker-agnostic venue-spec system
New: [venues/README.md](../workspace/baysix-engine/research-engine/core/engines/cost-venue/venues/README.md) (the agnostic schema, same keys for JM/Darwinex/IBKR) + [venues/justmarkets.yaml](../workspace/baysix-engine/research-engine/core/engines/cost-venue/venues/justmarkets.yaml) (fully populated from the JM XAUUSD.s spec + trading-conditions page). Key facts captured: Pro account (spread-only ~2 pip), symbol `XAUUSD.s` (digits=2, contract 100oz, min lot 0.01), dynamic leverage ladder (1:3000<$1k → 1:500≥$30k), **margin call 40% / stop-out 20%**, **swap-free** (XAUUSD qualifies → swap=0), Market execution + FOK, stops-level 0 (HFT/EA caveat), sessions GMT+3. Raw account saved for reference (1-pip + $3.5/lot/side, **$200 min deposit** so unavailable at $50). Decision: **model on Pro** (Raw only ~15% cheaper AND locked behind $200). The `*_cfd_model.py` placeholders are NOT yet wired to read the YAML — that's a future code task (code-reviewer gate).

### 4. Created the `jm-microcap` Deployment Profile + relocated it out of `Memory/`
- Profile written: $50 XAUUSD growth account, kill = acceptable-ruin (P(lose $50) ≤ 0.50), objective = max P(reach $1,000 before $0), state-dependent Kelly under the leverage ladder. **Validity gates KEPT HARD** (N_min, honest N_trials, DSR, cost gate, OOS persistence); survival gates relaxed (ruin ≤ 50%); portfolio gates dropped. Records that the broker 20% stop-out is NOT protection at 1:3000 (used margin ~$1.52/0.01lot → stop-out at ~$0.30 equity) — **YOUR stop-loss is the real ruin boundary.**
- **Relocated** `risk_parameters.md` from `Memory/` → [research-engine/step1_ideation/layer1_deployment-profile/risk_parameters.md](../workspace/baysix-engine/research-engine/step1_ideation/layer1_deployment-profile/risk_parameters.md) so it versions with the engine it gates. `strategy_state.md` + `research_queue.md` future-homed at `research-engine/` root. Repointed in one pass: SessionStart hook ([settings.json](../.claude/settings.json)), quant-researcher, code-reviewer, risk-check, update-memory, run-backtest, check-mt5-health, check-lean-health. `alpha_insights.md` + handovers stay in `Memory/` (CoS narrative). Verified zero stale `Memory/` refs.

### 5. Fixed the "Layer 0" naming inconsistency
The deployment profile was called both "Layer 0" (doc) and "step1/layer1_deployment-profile" (folder) — same thing, two names, the source of real confusion. Renamed to **"step 1 · layer 1"** consistently in [BAYSIX_FRAMEWORK.md](../BAYSIX_FRAMEWORK.md) (header, subtitle/path, funnel line, boundary table, routing table), risk-check skill, and risk_parameters.md. Left the edit-log (a record) and XAUUSD_OPTIONS_FRAMEWORK.md ("Layer 0 — GEX" = unrelated concept) untouched, by design.

### 6. Shaped IB-001's layer-2 hypothesis (timeframe confluence) — saved to memory
Confirmed with Syafiq. Saved to [project_ib001_hypothesis.md](../../.claude/projects/c--Users-User-Desktop-sigma-brain/memory/project_ib001_hypothesis.md). Summary below under Key Decisions.

---

## What Is NOT Done / Still Open

- **IB-001 hypothesis not formally locked** — one decision remains: the timeframes (M1 entry / M15 direction [simpler] vs M1 / M5-confirmed-by-M15 [closer to how Syafiq trades]). My lean: start M1+M15, prove the gap, then test adding M5.
- **`strategy_state.md` (IB-001 manifest) not written** — correctly, because the hypothesis (metric/timeframes) isn't locked yet. Write it once locked.
- **No code yet** — the continuation/reversal classifier + layer-3 confirmation are still talk-only (layer 2). Nothing built.
- **Venue TO_VERIFY**: news/rollover spread widening, regulator. (Swap + stop-out + leverage now confirmed.)
- **`justmarkets_cfd_model.py` not wired** to read the new YAML (placeholders still `None`).
- **LEAN runnability unverified** — Docker + XAUUSD data. Run `/check-lean-health` before any backtest.

---

## Running Processes

None.

---

## Priority for Next Session

1. **Lock IB-001 layer-2 hypothesis** — settle the timeframe question (M1/M15 first, per recommendation), then it's locked: idea_type=timing, primary_metric=hit_rate, edge=continuation-vs-reversal classification of swing-point breakouts.
2. **Write the IB-001 manifest** to `research-engine/strategy_state.md` once locked (profile=jm-microcap, step1/layer2, locked metric, N_trials=0).
3. **Spec the layer-3 confirmation** — start simplest: define continuation/reversal by swing structure alone (HH/HL vs LL/LH), measure the conditional hit-rate gap on Dukascopy ticks. Causal labels only (no hindsight). Then code → code-reviewer → run.

---

## Key Decisions Made

- **IB-001 = multi-timeframe confluence.** Edge = being on the side the higher timeframe is already pushing; M1 trigger is just the *when*. HTF direction read from **swing-point breakouts**.
- **The actual alpha = classifying breakout *purpose* (continuation vs reversal)** — the variable a human can't track unemotionally. Falsifiable: hit-rate(M1 aligned | continuation) >> hit-rate(M1 aligned | reversal); kill if equal.
- **CRITICAL trap flagged:** the continuation/reversal label MUST be causal (computable at the breakout instant from past+present only). Labeling by what happened after = lookahead = fake edge.
- **Hard scope (Syafiq, firm):** B2B-detection-independent — the ONLY thing borrowable from B2B is **swing-point detection**. Discover the edge with math (swing structure → HMM regime → tick impulse), not the discretionary B2B ruleset.
- **Build order:** start parameter-free (swing structure); add HMM/impulse only if they widen the hit-rate gap (each addition = a trial).
- **Model on Pro, not Raw** (Raw ~15% cheaper but needs $200 deposit; unavailable at $50).
- **Engine state versions with the engine; CoS narrative stays in `Memory/`.**

---

## Blockers

None. (sigma-research Cloud Run deploy still blocked by org policy — not on critical path.)

---

## Repo State (uncommitted)

- **sigma-brain** `master`: CLAUDE.md (prior session), BAYSIX_FRAMEWORK.md (Layer-0 rename), settings.json (hook repoint), .claude/agents/{quant-researcher,code-reviewer}.md, .claude/skills/{risk-check,update-memory,run-backtest,check-mt5-health,check-lean-health}, new Memory handover. `Memory/risk_parameters.md` deleted (moved).
- **baysix-engine** `main`: new `venues/README.md` + `venues/justmarkets.yaml`, new `step1_ideation/layer1_deployment-profile/risk_parameters.md`. Not committed.
- Nothing pushed. No commits made this session.
