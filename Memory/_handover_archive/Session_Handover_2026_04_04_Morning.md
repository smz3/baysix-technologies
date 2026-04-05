# Session Handover — 2026-04-04 (Morning)

**Session duration:** ~2 hours
**Next session priority:** Phase 0 — baysix-backend repo creation + Supabase schema + PostgresSaver

---

## What We Accomplished This Session

1. **Major architecture reset** — Scrapped the two-app strategy (sigma-quant + baysix-platform). Consolidated into ONE unified product: **Baysix**, powered by the **Sigma** strategy engine.

2. **Branding locked:**
   - **Baysix** = the software product name
   - **Sigma** = the proprietary trading strategy inside Baysix
   - Tagline: *"Baysix — Powered by the Sigma Strategy Engine"*

3. **Infrastructure redesigned from scratch:**
   - Docker removed from local machine (Ollama native on Windows for GPU)
   - Docker used ONLY on OCI ARM (4 services: fastapi, qdrant, hyperliquid-adapter, ibkr-adapter)
   - RAGFlow removed — replaced by Docling (pip library, no Docker container)
   - Redis/Celery removed — replaced by APScheduler in FastAPI + Supabase triggers

4. **Multi-broker architecture designed:**
   - MT5 → Forex / XAUUSD (local machine, EA polls Supabase)
   - Hyperliquid → Crypto perpetuals (OCI ARM, Python SDK, always-on)
   - IBKR → Equities (paper account first, Client Portal API on OCI)
   - Universal pattern: LangGraph writes to Supabase. Broker adapters read from Supabase. Never direct.

5. **ML training architecture clarified:**
   - XGBoost zone scorer: trains on OCI ARM (CPU, fast enough), deployed on OCI
   - LSTM regime classifier: trains on local machine (GPU), inference on OCI ARM
   - Gemma LoRA fine-tune: trains on local machine (Unsloth + QLoRA), Phase 8+
   - ALL training artifacts write to Supabase Storage → visible in Baysix Learning Lab

6. **Three-tier access model finalized:**
   - Public (no auth): Home, Research Hub, Daily Brief
   - Authenticated: Intelligence Terminal, Sigma Engine, Learning Lab, Operations
   - Admin (you only): Command page (triggers, kill switch, retraining)

7. **Build order corrected:**
   - Phase 0: Foundation (FastAPI + PostgresSaver + Supabase schema)
   - Phase 2: DATA FLYWHEEL FIRST (zone outcome tracking before any agents)
   - Phase 8: Frontend LAST (UI built after system has real data)

8. **New build plan written:** `Braindump/BAYSIX_BUILD_PLAN_v3.md` — single source of truth

---

## Decisions Locked (Do Not Revisit)

- ONE app: Baysix (not two apps)
- sigma-quant stays live in parallel (Option C) — archived after Baysix Tier 0 launches
- Hyperliquid for crypto (not Binance)
- IBKR for equities (paper account first)
- Docker only on OCI ARM, not on local Windows machine
- Docling replaces RAGFlow
- APScheduler + Supabase triggers replaces Redis/Celery
- Data flywheel built at Phase 2, before any research agents
- Frontend built at Phase 8, after backend has real data
- `sigma-research` repo is superseded by `baysix-backend` — do not build on it further

---

## Current Project Status

| Project | Status |
|---|---|
| sigma-quant | Live, clean, running in parallel. Archive later. |
| sigma-brain | HQ, pushed to GitHub. Active. |
| sigma_core | Complete. Sealed binary. |
| sigma-research | Superseded. Do not develop further. |
| baysix-backend | Does not exist yet. Create at Phase 0. |
| baysix (frontend) | Does not exist yet. Create at Phase 8. |
| OCI ARM | Not yet set up. Required for Phase 0. |
| Ollama | Status unknown. Check: `ollama list` |
| Docker | Should NOT be on local machine. Will be on OCI ARM only. |

---

## Next Session — Start Here

1. Read `Braindump/BAYSIX_BUILD_PLAN_v3.md` in full
2. Check environment:
   ```powershell
   ollama --version
   ollama list
   ollama pull gemma3:9b   # if not pulled
   ```
3. Get Supabase direct DB URL (Settings → Database → Connection String → URI, NOT pooler)
4. Create `baysix-backend` repo with folder structure from Section 12 of v3 plan
5. Apply Supabase schema (all tables from Section 6 of v3 plan in one migration)
6. Wire PostgresSaver checkpointer (check: `pip show langgraph` version first)
7. Build FastAPI skeleton with `/health` and `/trigger`
8. Smoke test: trigger cycle → checkpoint written to Supabase

---

## Open Questions (Small, Not Blockers)

- What specific Gemma model tag is available on Ollama? (`ollama search gemma`)
- IBKR: paper account setup needed — have you created one yet?
- OCI ARM: is the instance already provisioned? If not, it needs to be set up before Phase 0 Docker deployment.
