# Handover Memo: PRD v3 Pivot & Agentic Trading Architecture
**Date:** 2026-04-01 | **Context:** Sigma Brain Pivot from fully-autonomous unstructured trading to Hybrid Systematic Execution.

## 1. Work Completed
* **Strategic Pivot:** Conducted an honest review of the "fully autonomous hedgefund" objective. Decided to build an **Agentic Systematic Trading** system instead. This system uses deterministic algorithms (MT5 EA) to execute the core B2B edge, while AI Swarms handle macro reasoning, risk context, and instrument ranking. 
* **PRD Generated:** Authored `Braindump/PRD_baysix_ai_hedge_fund_v3.md` detailing the 6-phase rollout plan.
* **IP Protection Sorted:** Finalized plan to use **Cython** to compile the proprietary B2B `.py` source code into unreadable `.pyd` binaries to protect the edge from LLM prompt leakage.
* **Orchestration Matrix:** Reversed previous "no framework" instruction. Confirmed **LangGraph** will be used to orchestrate the research swarm because trading workflows cleanly map to LangGraph state machine designs.
* **Memory Updates:** Pushed Phase 0 and Phase 1 tasks into the `research_queue.md` and updated `strategy_state.md`.

## 2. Core Architectural Decisions
* **Cloud Infrastructure Budget:** $0 (Oracle Cloud ARM Free Tier + Groq Free API + Gemini Free API).
* **Communication Bus:** MT5 EA will not receive direct commands. The LangGraph swarm will deposit a `trading_context.json` into Supabase. The MT5 EA will poll Supabase to apply AI risk-multipliers and instrument blocking on top of its active B2B logic. 
* **The "Dead Man's Switch":** If the LangGraph orchestrator goes down for >24 hours, the `trading_context.json` is considered stale, and the MT5 EA will drop into defensive sizing automatically without waiting for an AI instruction.

## 3. Immediate Next Steps for Next LLM Session
The next session operator must NOT begin writing the LangGraph logic until the user provides clear answers to the **5 Open Environment Questions**:

1. **Sigma-crypto Source Location**: Where exactly is the B2B python logic stored in `workspace/sigma-crypto`? (Needed to design the Cython build).
2. **API Keys**: User must verify they possess and have configured `.env` keys for FRED, Groq, and Gemini. 
3. **VPS Constraints**: User must confirm their broker VPS supports HTTP `WebRequest()` commands to poll Supabase.
4. **Backtest File Formats**: User must clarify standard data formats (CSV/JSON/DB) outputted by their current Monte Carlo/OOS MT5 tests to allow the newly built `Validator` agent to read them.
5. **Python Versioning**: User needs to verify `>= Python 3.11` is running on the local and Oracle environments.

**Once these variables are cleared by the USER, immediately begin Phase 0 (LangGraph Skeleton) in `sigma-research`.**
