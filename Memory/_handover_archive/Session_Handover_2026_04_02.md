# Session Handover — 2026-04-02

## Session Goal
Build MVP features for sigma-quant to support two job applications:
1. **AI Quantitative Developer** — Build AI/ML models, quant strategies, data pipelines, P&L analysis
2. **AI Market Analyst** — Real-time market monitoring, multi-asset analysis, macro indicators, market reports

## Key Decision: Build ON sigma-quant (NOT a new app)
We explored and rejected creating a new Vite app. sigma-quant already has:
- 60+ components, dark OLED theme, glass morphism, Inter + JetBrains Mono fonts
- Working auth (login: ADMIN / key: Quant2026!)
- Populated dashboard with real backtest data from Supabase
- Research Hub with SAMTC paper + 4 forensic audit cards
- Design system: CardHeader, HeroStats, StatCell, SwarmTerminal, EquityCurve, TradeTable

## Current App State (Verified via Browse)
- **Running on**: localhost:3001 (port 3000 was occupied)
- **Build status**: Dev mode works fine. Production build has a TypeScript error in ConsensusBreakdown.tsx:7 (missing `trades` type in database.ts) — 2-minute fix
- **.next cache**: Was corrupted, cleared successfully
- **Pages working**: Dashboard (/), Research Hub (/research)
- **Data source**: Supabase (populated with Multi-Symbol backtest data)

## What Needs to Be Built (Sprint)

### Page 1: "Intelligence" — AI Market Analyst (CRITICAL)
Add to sidebar as new nav item. This is the showcase for the Market Analyst JD.

**Components needed:**
- **MarketPulse grid** — 8 cards showing live data:
  - SPX, VIX, DXY, Gold (from Yahoo Finance chart API)
  - BTC/USDT, ETH/USDT, SOL/USDT (from Binance public API)
  - US 10Y Yield (from Yahoo Finance)
- **MarketAnalysis panel** — AI-generated macro report using Groq API (llama-3.3-70b-versatile, free tier)
  - Regime classification (Risk-On/Risk-Off/Inflationary-Tightening/Stagflation/etc.)
  - Confidence score + narrative citing specific numbers
  - Key drivers list + watch list
  - Risk multiplier recommendation
- **RegimeIndicator badge** — Color-coded regime status

**Data fetching approach:**
- Next.js API routes (src/app/api/) to proxy external APIs (avoids CORS)
- Yahoo Finance: `https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d`
- Binance: `https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=BTCUSDT`
- Groq: POST to `https://api.groq.com/openai/v1/chat/completions`
- FRED: `https://api.stlouisfed.org/fred/series/observations?series_id=CPIAUCSL&api_key=KEY`

**Prompt to reuse:** The exact macro prompt from `sigma-research/llm/prompts/macro_prompt.txt` (Dalio "Economic Machine" framework). The full prompt and expected JSON output schema are documented in sigma-research.

### Page 2: "Architecture" — Builder Showcase (MEDIUM)
- Agent pipeline flow diagram (Data → Macro → Micro → Risk → CIO → Execution)
- Tech stack grid (LangGraph, Groq, Ollama, Qdrant, Supabase, Cython, etc.)
- 6 agent role cards with descriptions

### Header Upgrade
- Add regime indicator badge to top bar (shows current macro regime)

## API Keys Available
- **Groq**: Check sigma-research/.env for GROQ_API_KEY
- **FRED**: Check sigma-research/.env for FRED_API_KEY
- **Supabase**: Already in sigma-quant/.env (working)
- **Binance public API**: No key needed
- **Yahoo Finance**: No key needed

## Key Files to Reference

### sigma-quant (the app being modified)
- `src/app/page.tsx` — Dashboard page (server component, async)
- `src/app/layout.tsx` — Root layout (Edge Runtime, auth gateway)
- `src/app/research/page.tsx` — Research Hub page
- `src/components/layout/Sidebar.tsx` — Navigation (add new items here)
- `src/components/metrics/HeroStats.tsx` — Reusable 10-cell metric grid
- `src/components/ui/CardHeader.tsx` — Section header with accent bar
- `src/components/dashboard/SwarmTerminal.tsx` — Agent activity feed pattern
- `src/components/dashboard/DashboardClient.tsx` — Client component pattern
- `src/app/globals.css` — Glass effects, dark theme tokens
- `tailwind.config.ts` — Color palette (base #09090B, win green #22C55E, loss red #EF4444)
- `src/types/database.ts` — FIX THIS: missing `trades` table type (blocks production build)
- `package.json` — Next.js 16.1.1, React 19, Tailwind 4, Recharts, Framer Motion

### sigma-research (analysis pipeline to replicate)
- `llm/prompts/macro_prompt.txt` — Dalio macro analysis system prompt
- `llm/groq_client.py` — Groq API call pattern (temperature 0.2, structured JSON)
- `nodes/ingest_data.py` — Data source URLs and caching logic
- `nodes/macro_analyzer.py` — Regime classification + fallback logic
- `state/trading_state.py` — Output schema (regime, confidence, narrative, drivers, multiplier)
- `nodes/cio_synthesizer.py` — Final JSON output structure

## Settings Updated
- `.claude/settings.json` simplified: `Bash(*)` wildcard + all tools auto-allowed
- Deny list reduced to only live trading order endpoints (Binance)
- No more approval popups for normal operations

## Deployment Plan (After Build)
1. Fix TypeScript build error (database.ts types)
2. `npm run build` — verify production build works
3. Deploy to Cloudflare Pages (need to add wrangler.toml + @cloudflare/next-on-pages)
4. API routes deploy as Cloudflare Functions automatically
5. Set environment variables in Cloudflare dashboard (GROQ_API_KEY, FRED_API_KEY, Supabase creds)

## Sprint Priority Order
1. Fix production build (TypeScript type error) — 5 min
2. Add API routes for market data + LLM analysis — 1 hour
3. Build Intelligence page with MarketPulse + MarketAnalysis — 2 hours
4. Build Architecture page — 1 hour
5. Update Sidebar navigation — 15 min
6. Add regime badge to header — 15 min
7. Deploy to Cloudflare — 30 min

## Context for Next Agent
The user is applying for jobs TODAY. Speed matters. The existing sigma-quant app is 80% there — it already proves quant strategy skills with real backtest data. The missing 20% is the **live market intelligence** piece that proves AI agent building + market analysis capabilities. That's what both JDs specifically ask for. Build the Intelligence page first, it's the highest-impact addition.
