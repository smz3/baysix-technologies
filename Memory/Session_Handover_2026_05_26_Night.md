# Handover — May 26, 2026 Night

## What We Did

### DB Architecture — Designed + Built from Scratch
Replaced `research_log.db` with two purpose-built stores:

**`research/ideas_log.db`** — ideation journal
- `ideas` table: every idea captured, with `id`, `code`, `name`, `parent_idea_id`, `asset_class`, `signal_type`, `status`, `source`, `role` (infrastructure/strategy), `notes`
- `generate_calls` table: every GENERATE agent call logged here
- Rule: GENERATE gear → this DB

**`research/research_log.db`** — research pipeline tracker (Kanban)
- `pipeline` table: one row per promoted idea, tracks `current_stage`
- `pipeline_events` table: full audit trail — every stage transition + VALIDATE call
- Rule: VALIDATE gear → this DB

**Pipeline stages locked:**
```
CAPTURED → HYPOTHESIS_SET → IS_DEVELOPMENT → WALK_FORWARD →
COST_CHECK → OOS_VALIDATION → MONTE_CARLO → PROMOTED
KILLED / PARKED (any stage)
```

**CLAUDE.md Rule 10 updated:** GENERATE → ideas_log, VALIDATE → research_log

---

### Infrastructure Layer — 3 Confirmed + 5 Candidates

**Confirmed (in DB, role=infrastructure):**
| Code | Name | Status |
|---|---|---|
| HMM-001 | Hidden Markov Model - Regime Detection | promoted, in pipeline at HYPOTHESIS_SET |
| IV-001 | Implied Volatility Engine | promoted |
| MACRO-001 | Macro Regime Model | promoted |

**Key decisions made:**
- HMM = technical regime (what market IS doing). Daily TF. Lookback via BIC on [60,126,252] bars. Accept if transition matrix diagonal ≥ 0.75.
- IV Engine = GVZ-based. Outputs: IVR, VRP, vol regime. Options premium data = smart money read even without trading options directly.
- Macro Regime = fundamental regime (WHY market moves). 4 states: Goldilocks/Risk-Off/Reflation/Stagflation. Built as HMM on macro factors (FRED API, VIX, WGC). Advisory filter — tells you WHAT TO WATCH, not when to pull trigger.
- All 3 are multi-asset agnostic.

**5 new candidates (NOT yet discussed — next session mission):**
| Code | Name | Agent Flag |
|---|---|---|
| RISK-001 | Dynamic Position Sizing Engine | MOST URGENT — blocking live now |
| FILTER-001 | Signal Conditioning + Noise Filter | |
| FLOW-001 | Order Flow Imbalance Engine | |
| PORT-001 | Correlation + Portfolio Construction | Activate at asset #2 |
| STAT-001 | Statistical Arbitrage + Cointegration Scanner | |

---

### Strategy Ideas Inbox — 23 strategies across 3 families
- HMM-002 to HMM-008 (7 strategies)
- IV-002 to IV-008 (7 strategies)
- MACRO-002 to MACRO-010 (9 strategies)
- Total ideas in DB: 31

All `inbox`. None promoted until backtested with proven edge.

---

## Next Session Mission

**Dissect the 5 new infrastructure candidates:**
1. Start with RISK-001 — agent flagged as most urgent (blocking live improvement on $50 account)
2. Discuss what each one looks like, data constraints, what can be swapped
3. Spawn strategy children from each (same process as HMM/IV/MACRO)
4. Log everything to ideas_log

**Then:** Pick one strategy from the inbox to push into the research pipeline (HYPOTHESIS_SET → IS_DEVELOPMENT).

## Blockers
None.
