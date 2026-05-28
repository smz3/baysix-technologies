# Handover — May 28, 2026 Evening

## State
Major research infrastructure upgrade: QR agent now has 3 gears (GENERATE, DISSECT, VALIDATE). DISSECT gear is fully specced — section-anchored citations, 3-tier confidence (full-text/abstract/unavailable), mandatory Context Fit block (asset-agnostic, replaces old xauusd_translation). Migrations 004 + 005 applied to `research/db/agent_log.db`: `papers_consulted` table live (normalized, replaces JSON blob), `baysix_applicability` dropped. 5 HMM-001 papers pulled and sitting at `dissected=0`. Streamlit dashboard updated: CUSUM-001 tab renamed to Model Outputs, Papers tab added (metrics, filters, detail cards), Agent Calls tab fixed (applymap→map, try/except per tab). All tabs error-free. Agent Step 0 now queries `papers_consulted` to avoid re-reading known papers. Agent hard-rule added: never write to DB (Claude writes only).

## Next
1. Run DISSECT gear (Sonnet) on arXiv:2007.14874 (Oelschläger & Adam — hierarchical HMM) — verify Papers tab populates `key_equations`, `empirical_findings`, `context_fit`, `limitations` and `dissected` flips to 1
2. GENERATE brief (Sonnet) to lock 3 HMM-001 architecture decisions: K selection method, emission feature set (raw returns vs multivariate), stickiness mechanism
3. Build `research/models/hmm/` — HMM-001 foundational model (Gaussian emissions, 2–4 states, IS daily log returns 2016–2024-05-02)

## Blockers
None — all infra clean, dashboard live at localhost:8501, migrations 001–005 applied.
