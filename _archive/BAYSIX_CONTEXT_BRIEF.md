# Baysix Technologies — Sigma Trading System
## Context Brief for CV & Cover Letter Assistance

---

## What Is Baysix?

**Baysix** is a personal AI-powered mini hedge fund and quantitative research operation built and run by Syafiq M. Zin. It is not a registered fund — it is a full-stack systematic trading infrastructure built as both a live trading operation and a professional portfolio showcase for AI Quantitative Developer and AI Market Analyst roles.

The system combines a proprietary algorithmic trading edge (B2B zone detection) with an AI agent swarm for research, risk management, and decision support. Everything is built from scratch by Syafiq, primarily using Python, TypeScript, and modern AI development tools.

---

## The Core Strategy — B2B Zones + SAMTC

**B2B (Base-to-Base) Zone Detection** is Syafiq's proprietary trading edge. It identifies high-probability structural price zones on charts — areas where institutional order flow has previously stacked — using a deterministic geometric algorithm. This is the "alpha engine" of the system. Key facts:

- Written as a compiled Python binary (`.pyd`) called `sigma_core` — source code is never exposed to AI agents or shared publicly
- Operates across XAUUSD (Gold/USD), crypto perpetuals (Binance Futures), and Forex via MT5
- Has been live-tested on a $100K funded account at Alpha Capital Group

**SAMTC (State Aware Multi Temporal Consensus)** is the quantitative research framework built on top of B2B zones. It converts multi-timeframe structural analysis into rule-based, mathematically testable trading signals. Syafiq authored a full research paper on SAMTC, validated through:
- Walk Forward Optimization (WFO)
- Consecutive drawdown stress testing
- Three distinct market regimes tested (in-sample / out-of-sample)
- Multiple backtest environments (accessible via the sigma-quant dashboard)

---

## What Has Been Built

### 1. sigma-quant — Live Analytics Terminal
- **Stack:** Next.js 15, TypeScript, Supabase (PostgreSQL + realtime), Recharts, lightweight-charts
- **What it does:** Real-time web dashboard for monitoring backtests, live trades, and agent activity
- **Features:** Equity curve visualization, trade forensics and attribution, monthly heatmaps, win/loss distribution charts, performance metrics (Sharpe, max drawdown, profit factor, avg R-multiple), AI regime badge, agent swarm activity terminal
- **Auth:** Supabase Auth (login-gated)
- **Research Hub:** Hosts the SAMTC research paper PDF, forensic audit trail cards for completed backtests, and a strategy explorer for comparing multiple backtest environments side by side
- **Live URL:** syafiqmzin-sigma-quant.pages.dev (deployed on Cloudflare Pages)
- **GitHub:** github.com/smz3/SIGMA-Quant (public)

### 2. sigma-research — Python Research Infrastructure
- **Stack:** Python, LangGraph, Qdrant (vector database), Groq API, Gemini API, Ollama (local LLMs)
- **What it does:** Data ingestion, macro analysis, and quantitative research pipeline
- **Data sources:** FRED API (economic data), yfinance (equity/index prices), CCXT (crypto live data), NLP news scraping
- **AI components:**
  - Groq `llama-3.3-70b` — fast structured JSON agent outputs
  - Google Gemini 1.5 Flash — large context, research report generation
  - Ollama (local) — offline testing with qwen2.5:7b and mistral:7b
  - Qdrant — vector search over research findings, citations, and alpha insights

### 3. sigma-brain — HQ Orchestration Layer
- **What it is:** The central brain of the operation — orchestrates all agents, holds all memory, stores PRDs and strategy state
- **Stack:** LangGraph StateGraph (multi-agent orchestration), Supabase (shared IPC bus), markdown-based memory files
- **Agent Roster (8 specialized agents):**
  - **CIO** — strategic priority and capital allocation decisions
  - **Quant Researcher** — orchestrates the full research pipeline
  - **Quant Developer** — code changes, backtests, build tasks
  - **Quant Trader** — signal monitoring and trade review (read-only)
  - **Risk Manager** — drawdown monitoring, kill switch, position limits
  - **Memory Curator** — synthesizes session findings into persistent memory files
  - **Macro Researcher** — Ray Dalio layer (regime detection via DXY, yields, liquidity, cross-asset)
  - **Micro Researcher** — Point72 layer (zone statistics, instrument edge, entry precision)
- **Quality Gates:** Code Reviewer (all code must be APPROVED before execution), Peer Reviewer (all research must be APPROVED before reaching CIO)
- **Research Philosophy:** Hybrid three-layer framework — Ray Dalio (macro regime) → Point72 (instrument selection) → Paul Tudor Jones (risk management)
- **GitHub:** github.com/smz3/sigma-brain (private)

### 4. sigma-crypto — Python SAMTC Engine
- **What it does:** Python backtesting and live signal engine for crypto perpetuals on Binance Futures
- **Uses:** The compiled `sigma_core` binary for B2B zone detection, CCXT for live data

### 5. sigma-mt5 — MQL5 Expert Advisor
- **What it does:** MetaTrader 5 Expert Advisor (EA) implementing B2B zone detection for live Forex trading
- **Instruments:** XAUUSD (primary), Forex pairs via MT5
- **Status:** In live deployment

### 6. ML Models (Built, In-Pipeline)
- **XGBoost Classifier** — trained on historical zone outcome data (win/loss + R-multiple) to score trade quality pre-entry. Features include zone age, touch count, cascade score, ATR, session, time-of-day
- **LSTM Regime Classifier** — classifies macro regime (Risk-On, Risk-Off, Stagflation, Inflationary-Tightening, Deflationary, Stable-Expansionary) from cross-asset time-series inputs
- **Groq LLM Macro Regime Classifier** — live, in production. Uses Llama 3.3 70B with structured JSON output to classify regime from raw market snapshot data

---

## What Is Currently Being Built

1. **Intelligence Page (sigma-quant)** — Redesigning the hero page of the analytics terminal to function as a mini Bloomberg terminal: live candlestick chart (lightweight-charts), multi-asset watchlist (SPX, BTC, Gold, DXY, ETH, SOL, US10Y, VIX), AI regime badge panel, and live agent swarm activity feed
2. **Operations Page (sigma-quant)** — Paperclip-inspired task board showing live agent tasks, agent roster status, and activity feed from Supabase tables
3. **sigma-research full activation** — Completing the LangGraph research pipeline for autonomous macro + micro research cycles
4. **ML pipeline productionization** — Moving XGBoost zone scorer from prototype to live scoring on every new B2B zone signal

---

## Technology Stack Summary

| Layer | Technologies |
|---|---|
| AI Orchestration | LangGraph StateGraph, multi-agent swarm |
| LLMs | Groq (Llama 3.3 70B), Google Gemini 1.5 Flash, Ollama (local) |
| ML | XGBoost, LSTM, scikit-learn |
| Backend / Data | Python, Supabase (PostgreSQL + realtime), Qdrant |
| Data Sources | FRED, yfinance, CCXT, NLP scrapers |
| Frontend | Next.js 15, TypeScript, React, Recharts, lightweight-charts |
| Trading Execution | MT5 (MQL5 EA), Binance Futures (CCXT) |
| Dev Tools | Google Antigravity IDE, Claude Code |
| Deployment | Cloudflare Pages (sigma-quant), local machine → OCI ARM (planned) |

---

## How to Use This for CV / Cover Letter Work

Syafiq's experience as a **quant developer is approximately 1 year** (Oct 2025 – Present), primarily through building Baysix. He has **7 years of institutional and independent market experience** (Affin Hwang Asset Management, Kenanga Investment Bank, Inserge Sdn Bhd, Alpha Capital Group). When writing his CV for developer roles, lead with Baysix as the primary experience block and frame the market experience as domain depth, not programming depth.
