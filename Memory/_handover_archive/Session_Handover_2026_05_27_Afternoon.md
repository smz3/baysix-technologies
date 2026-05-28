# Handover — May 27, 2026 Afternoon

## State
Full arsenal review completed. 51 ideas in `research/ideas_log.db`. Two critical gaps identified and added: TCM-001 (Transaction Cost Model, inbox) and CUSUM-001 (Structural Break Detector, inbox, promoted from HMM-004). Three deferred nice-to-haves locked as parked: LIQ-001, ATTR-001, ALT-001. HMM-004 notes updated to reference CUSUM-001. [brokers/justmarkets.yaml](brokers/justmarkets.yaml) extended with standardized `tcm:` block (schema version 1.0). RISK-001 fully specified by quant-researcher (generate_calls row 8) — Quarter-Kelly at launch, 10% heat ceiling, 60% peak equity floor. Canonical build order: TCM-001 → CUSUM-001 → HMM-001 → FILTER-001 → IV-001 → FLOW-001 → RISK-001 → PORT-001 → STAT-001 → MACRO-001.

## Next
1. Answer 3 open RISK-001 design decisions before build: (a) is `sigma_trade` computed inside TCM-001 pipeline or lodged in strategy profile? (b) is `strategy_max_lot` fixed, % of equity, or equity-tier function? (c) is `allow_min_lot_override` always ON at $50?
2. Design TCM-001 build plan — wire `tcm:` block in justmarkets.yaml to Python math layer, write schema validator
3. B2B H1 cost rehabilitation — solve backwards algebra on z=+7.19 signal: what stop size / venue pushes ρ ≥ 0.50?

## Blockers
None.
