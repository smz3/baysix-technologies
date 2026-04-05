# Session Handover — 2026-04-04 (Evening)

**Session duration:** Full day (~8 hours across two sessions)
**Next session priority:** Phase 0 — Create baysix-backend repo, apply Supabase schema, wire PostgresSaver

---

## What We Decided Today (Full Day Summary)

### Morning Session
1. Scrapped two-app strategy. ONE product: Baysix, powered by Sigma strategy engine.
2. Confirmed branding: Baysix = product, Sigma = strategy, sigma_core = sealed binary.
3. Redesigned infrastructure: Docker on OCI ARM only, Ollama native on Windows.
4. Multi-broker architecture: MT5 (Forex/Gold), Hyperliquid (Crypto), IBKR (Equities).
5. Supabase as universal signal bus. LangGraph never calls broker APIs.
6. RAGFlow removed → Docling. Redis/Celery removed → APScheduler + Supabase triggers.
7. ML training: XGBoost on OCI ARM (CPU), LSTM on local GPU, LoRA on local GPU (Phase 9+).
8. Three-tier access: Public / Authenticated / Admin.

### Afternoon Session
9. Product philosophy locked: **Quant Centric**. Statistical rigour is the product, not the UI.
10. Quant capability framework documented (~100 capabilities across 9 pillars).
11. v4 build plan written: quant capabilities folded into every phase.
12. New tables added to schema: backtest_runs, monte_carlo_results, risk_metrics_daily, hypothesis_tests, regime_performance, model_explanations.
13. Hypothesis Board added as first-class feature (page + table).
14. Daily Brief upgraded to Quantitative Morning Report format (with p-values, CIs, n counts).
15. Two new deployment gates: permutation p < 0.05 AND Monte Carlo ruin probability < 1%.
16. Regime output must be a probability distribution, not just a label.
17. All point estimates must include confidence intervals — enforced across agents and UI.

---

## Source of Truth

**`Braindump/BAYSIX_BUILD_PLAN_v4.md`** — single source of truth, supersedes all prior versions.
**`Braindump/BAYSIX_QUANT_CAPABILITY_FRAMEWORK.md`** — detailed reference for all 9 quant pillars.

---

## Current Project Status

| Project | Status |
|---|---|
| sigma-quant | Live, running in parallel. Archive after Baysix Tier 0 launches. |
| sigma-brain | HQ, private GitHub. Active. |
| sigma_core | Complete. Sealed. |
| sigma-research | Superseded. Do not develop further. |
| baysix-backend | Does not exist yet. **Create at Phase 0.** |
| baysix (frontend) | Does not exist yet. Create at Phase 8 (after real data). |
| OCI ARM | Not yet set up. Needed before Phase 0 Docker deployment. |
| IBKR paper account | Not yet created. Needed for Phase 4. |

---

## Next Session — Exact Start Sequence

1. Read `Braindump/BAYSIX_BUILD_PLAN_v4.md` — source of truth
2. Check environment:
   ```powershell
   ollama --version && ollama list
   ollama pull gemma3:9b   # if not pulled
   ```
3. Get Supabase direct DB URL (Settings → Database → URI, NOT pooler)
4. Create `baysix-backend` repo with structure from Section 12 of v4 plan
5. Create `quant/metrics.py` first (Sharpe, Sortino, Calmar, VaR, CVaR as reusable functions)
6. Apply full Supabase schema from Section 7 of v4 plan as one migration
7. Wire PostgresSaver checkpointer
8. Build FastAPI skeleton
9. Phase 0 smoke test

---

## Three Things Still Needed Before Phase 0 Complete

1. **OCI ARM instance** — provision on Oracle Cloud (Always Free — 4 OCPUs, 24GB RAM)
2. **Supabase direct DB URL** — not the REST URL, not the pooler URL
3. **Ollama running with gemma3:9b** — confirm with `ollama list`
