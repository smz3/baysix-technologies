# PRD: Baysix Agentic Systematic Trading Architecture (v3)

**Status:** APPROVED
**Date:** 2026-04-01
**Revision:** v3.0 (Pivot to Hybrid Algorithmic + AI Reasoning)

---

## 1. Executive Summary & Philosophy

Baysix is transitioning from a traditional automated trading operation to an **Agentic Systematic Trading** shop.

**The Core Philosophy:**
AI LLM Agents do NOT discover strategies, nor do they execute trades via textual reasoning. Instead, the AI Swarm acts as an intelligent overlay that **validates, contextualizes, and scales** an existing, mathematically proven algorithmic edge.

*   **The Algo Layer (Deterministic):** Handles B2B Zone detection, SAMTC consensus filtering, position sizing math, and order routing.
*   **The AI Layer (Reasoning):** Handles macro regime synthesis, yield curve contextualization, cross-asset correlation warnings, instrument ranking, and continuous performance self-diagnosis.

**Strategic Goals:**
1.  **Job Acquisition:** Demonstrate institutional-grade infrastructure, rigorous statistical backtesting, and novel AI workflow orchestration.
2.  **Live Trading P&L:** Execute reliably under a zero-cost cloud budget across MT5 (Forex) and Binance (Crypto), protected by hard kill switches.

---

## 2. Infrastructure & Budget Bounds

The system must operate continuously on a **$0 budget** using a blend of local hardware, free cloud tiers, and free APIs.

*   **Orchestration Environment:** Oracle Cloud (OCI) ARM Free Tier (4 OCPU, 24GB RAM).
*   **LLM Intelligence:**
    *   *Groq (llama-3.3-70b-versatile):* High-speed, structured JSON outputs.
    *   *Google Gemini 1.5 Flash:* Large context windows for parsing Fed minutes and generating text reports.
    *   *Local Ollama:* Used purely for local development and offline testing (no GPU on OCI).
*   **Data APIs:** FRED (Macro, Free), Yahoo Finance (Equities/Indices, Free), CCXT (Crypto, Free).
*   **Execution Environment:** Free Windows VPS provided by broker (running MT5 Terminal).
*   **Database / IPC Bus:** Supabase Free Tier (used to pass `trading_context.json` between OCI and Windows VPS).

---

## 3. The Architecture Stack

The system is organized into a Hub-and-Spoke model centered around a LangGraph orchestrator.

### 3.1 Orchestrator (sigma-research)
A Python LangGraph `StateGraph` running on OCI ARM. It runs scheduled cycles (e.g., 6:00 UTC) and event-driven updates. It manages state transitions between data ingestion, algo execution, and LLM reasoning nodes.

### 3.2 The Sealed Signal Core (IP Protection)
The "Secret Sauce" (B2B geometric detection logic and SAMTC logic) must NEVER be exposed to LLM context windows to prevent prompt injection or IP leakage.
*   **Crypto (Python):** B2B core compiled via Cython into a binary `.pyd` module. Agents import an API but cannot inspect source logic.
*   **Forex (MT5):** Logic remains compiled inside the `.ex5` Expert Advisor running on the VPS.

### 3.3 Execution Integrations (sigma-mt5 & sigma-crypto)
The Execution Layer remains independent of the Research Swarm.
*   The MT5 EA routinely polls Supabase for the latest `trading_context.json`.
*   The EA evaluates local B2B setups *against* the AI's macro regime, permitted instruments list, and dynamic position risk multiplier.

---

## 4. Agent Swarm Definitions

Each "Agent" is a defined Node within the LangGraph orchestrator.

| Agent Identity | Role & Function | Output Contribution |
| :--- | :--- | :--- |
| **Data Ingestion** | (Algo) Pulls FRED macros, CCXT crypto data, and YFinance markets. | Populates raw data state. |
| **Macro Researcher** | Computes GDP/NFP/CPI trends, Liquidity, and Yield Curve. Uses LLM to synthesize narrative. | `regime`, `yield_curve_status`, `macro_narrative` |
| **Micro Researcher**| Ingests raw B2B zones from Sealed Core. Ranks them using statistical hit-rates under current regime. | `filtered_zones`, `instrument_rankings` |
| **Risk Manager** | Aggregates current exposure and open PnL. Flags correlations or structural drawdown risks. | `risk_assessment`, modifies `max_risk_pct` |
| **CIO (Synthesizer)** | Assembles all node outputs into the final JSON payload. | Completes `trading_context.json` |
| **Validator** | (Weekly Cycle) Runs Permutation/Bootstrap CI tests on backtest vs live equity curve. | Validation Markdown Reports |

---

## 5. Risk & Governance (Hard Rules)

1.  **No LLM Execution:** An LLM cannot execute an API call to a broker. It generates context; pure Python/MQL5 executes.
2.  **Double Kill Switch:** The EA has local hard drawdown limits (e.g., daily 5%). The AI Risk Manager can also flag a global `kill_switch: true` via the JSON context. If either triggers, trading halts.
3.  **Position Limits:** AI can adjust sizing multipliers (0.5x to 1.5x) based on regime confidence, but the base risk calculation remains mathematically fixed to equity.

---

## 6. Development Roadmap

1.  **Phase 0:** Establish LangGraph skeleton, connect Groq/Gemini clients.
2.  **Phase 1:** Cython compilation of Sigma-Crypto B2B components (IP protection).
3.  **Phase 2:** Validation Swarm (Bootstrap, Permutation tests).
4.  **Phase 3:** Dalio Macro Layer (Regime & Yield analysis).
5.  **Phase 4:** Point72 Micro Layer (Instrument Ranking & Sizing).
6.  **Phase 5:** MT5 Integration via Supabase Webhooks.
7.  **Phase 6:** Next.js Dashboard wiring for job showcase.
