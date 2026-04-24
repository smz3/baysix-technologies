---
type: meta
status: stable
last_updated: 2026-04-14
maintained_by: ai
ai_summary: "Master content catalog for the Baysix second brain vault. Every AI reads this file first before touching anything else."
---

# Baysix Vault — Master Content Index

> **START HERE.** Read this file first. Then read only the pages relevant to your task.
>
> Vault root: `sigma-brain/vault/`
> MT5 module docs: `../workspace/sigma-mt5/Documentation/modules/` (26 files — link, don't duplicate)
> **SEALED:** `sigma_core` source is never in vault context. See [[sigma-engine-map]] for the boundary.

---

## Quick Reference

| If you need to know... | Read this first |
|------------------------|-----------------|
| What B2B zones are and how they form | [[b2b-overview]] |
| Zone lifecycle: detected → active → invalidated | [[b2b-zone-lifecycle]] |
| Which timeframes do what (Narrative/Control/Sniper) | [[b2b-timeframe-hierarchy]] |
| Russian Doll nesting and confluence | [[b2b-russian-doll]] |
| T0/T1/T2/T3 touch system | [[b2b-touch-depth]] |
| How zones get invalidated (rules + cascade) | [[b2b-invalidation]] |
| Known bugs and open strategy questions | [[b2b-open-questions]] |
| MT5 EA module map (all 26 files) | [[mt5-ea-architecture]] |
| All backtest results (9G, 10C, 13A) | [[backtest-results]] |
| How to use this vault (Ingest/Query/Lint) | [[vault-operations]] |
| How sigma_core relates to the Python and MQL5 systems | [[sigma-engine-map]] |

---

## STRATEGY LAYER — `wiki/strategy/`

*Core B2B and SAMTC knowledge. Start here for any strategy question.*

| Page | Description | Tags | Status |
|------|-------------|------|--------|
| [[b2b-overview]] | B2B zone concept: what it is, why it works, 5-pointer engine, L1/L2/50% geometry | b2b, core | stable |
| [[b2b-zone-lifecycle]] | Full lifecycle: DETECTED → ACTIVE (L1 crossed) → INVALIDATED (L2 close). Exit-first rule. | b2b, zones | stable |
| [[b2b-timeframe-hierarchy]] | Narrative (MN1/W1/D1) / Control (H4/H1/M30/M15) / Sniper (M5/M1) — roles and rules | b2b, timeframes | stable |
| [[b2b-russian-doll]] | TF nesting, parent-child visibility rules, cascade invalidation, confluence scoring, fallback hierarchy | b2b, confluence | stable |
| [[b2b-touch-depth]] | T0/T1/T2/T3 touch tracking system, exit-first rule, position sizing intelligence | b2b, tracking | stable |
| [[b2b-invalidation]] | Invalidation triggers (1 close beyond L2 per TF), cascade rules, Dec 18 2025 corrections | b2b, risk | stable |
| [[b2b-open-questions]] | Cluster fix options A/B/C (OQ-001), cascade gap (OQ-002), slippage impact (OQ-003) | b2b, wip | draft |
| [[samtc-overview]] | SAMTC V6.7: Generals/Officers, FlowState, Storyline Latches, 3 trade gates (Fader/Inertial/Discovery) | samtc, crypto | stable |
| [[sigma-engine-map]] | How B2B (MQL5) + SAMTC (Python) + sigma_core (sealed .pyd) relate. IP boundary defined here. | core, ip | stable |

---

## SYSTEMS LAYER — `wiki/systems/`

*Technical architecture. Start here for any implementation question.*

| Page | Description | Tags | Status |
|------|-------------|------|--------|
| [[mt5-ea-architecture]] | All 26 modules, dependency tree, detection and execution pipelines (links to module docs) | mt5, architecture | stable |
| [[mt5-detection-pipeline]] | SwingPoint → RawBreakout → B2BDetector → Confluence → ZoneStatus data flow | mt5, detection | stub |
| [[mt5-execution-pipeline]] | TradeSignalGenerator → 3-Gate → Risk → OrderManager → TrailingStop flow | mt5, execution | stub |
| [[mt5-data-pipeline]] | QuantLogger → CSV → Supabase pipeline, zone lifecycle logging | mt5, data | stub |
| [[sigma-crypto-architecture]] | Python SAMTC stack: core/detectors, strategy, execution, risk, simulation | samtc, python | stub |
| [[kronos-integration]] | Kronos (AAAI 2026) zone survival prediction model, 72.7% PoC result, B2B fusion plan | kronos, ml | stub |
| [[baysix-platform-map]] | sigma-quant (live), sigma-research backend (blocked), baysix future platform | platform | stub |
| [[infrastructure]] | Qdrant Cloud, Supabase, Groq, Ollama (Gemma 4 31B), Just Markets MT5 | infra | stub |

---

## RESEARCH LAYER — `wiki/research/`

*Quantitative findings. Live data — these pages update frequently.*

| Page | Description | Tags | Status |
|------|-------------|------|--------|
| [[backtest-results]] | ALL test results: 9G (IS), 10C (governance), 13A (OOS) — Dataview table | backtesting | stable |
| [[hypothesis-board]] | Open hypotheses with evidence status — HYP-001: slippage impact on OOS | research, hypothesis | draft |
| [[alpha-insights]] | Confirmed structural edges from research | alpha | stub |
| [[research-queue]] | Active research tasks (mirrors Memory/research_queue.md) | research | stub |

---

## AI AGENTS LAYER — `wiki/ai-agents/`

*The AI stack. Read before orchestrating any multi-agent task.*

| Page | Description | Tags | Status |
|------|-------------|------|--------|
| [[vault-operations]] | How to run Ingest/Query/Lint on this vault — the 3 operations explained | vault, meta | stable |
| [[agent-roster]] | All agents and their roles: Claude, Gemma 4, quant-researcher, risk-manager, etc. | agents | stub |
| [[gemma4-capabilities]] | Gemma 4 31B: params (temp=1.0, top_p=0.95, top_k=64, ctx=262144), capabilities | gemma4 | stub |
| [[claude-skills]] | All /skill commands: run-backtest, vault-ingest, vault-query, vault-lint, handover, etc. | claude, skills | stub |

---

## META — `wiki/meta/`

| Page | Description |
|------|-------------|
| [[index]] | This file. Master content catalog. |
| [[schema]] | Frontmatter contract — read before creating any wiki page |
| [[health]] | Latest Lint report — contradictions, orphans, stale pages |

---

## Ingest Log Summary

*Last 5 ingests — see `raw/ingest.log` for full history.*

| Date | Source | Pages Updated |
|------|--------|---------------|
| 2026-04-14 | VAULT_INIT | All Phase 1 files |
| 2026-04-14 | B2B_DETECTION_SYSTEM.md | b2b-overview, b2b-zone-lifecycle, b2b-invalidation |
| 2026-04-14 | B2B_STRATEGY_DECISIONS.md | b2b-timeframe-hierarchy, b2b-touch-depth |
| 2026-04-14 | Memory/strategy_state.md | backtest-results |
| 2026-04-14 | modules/INDEX.md | mt5-ea-architecture |

---

## Vault Stats

| Metric | Value |
|--------|-------|
| Total wiki pages | 26 |
| Stable | 7 |
| Draft | 2 |
| Stub | 17 |
| Last lint | Never — run `/vault-lint` |
| Estimated word count | ~25,000 |
| Qdrant indexing | Not active (threshold: 400K words) |
