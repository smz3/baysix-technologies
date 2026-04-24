# SIGMA INTELLIGENCE CENTRE — Master Product Spec
_Last updated: 2026-04-24_

---

## Vision

A viewport-locked, Bloomberg-style trading terminal that serves two goals simultaneously:
1. **Daily trading desk** — actionable signals for XAUUSD + BTC B2B zone trading
2. **Portfolio showcase** — demonstrates full-stack AI quant capability for job applications

The AI synthesis layer is the moat. Bloomberg shows data. This terminal **understands** it.

---

## Architecture: 4 Named Views, One Terminal

Every view shares a persistent function bar + moving ticker tape. The view area below is fully swapped on click.

```
┌─ SIGMA INTELLIGENCE ─── [ TERMINAL ] [ MICRO ] [ MAP ] [ AI.DESK ] ─── RISK-ON 84% ──┐
├─►► BTC 94,200 ▲+1.2%  ·  ETH 3,140 ▼-0.4%  ·  GOLD 2,341 ▲+0.1%  ·  DXY 103.2 ▼  ─►┤
│                                                                                          │
│   [ Active view fills this space — viewport-locked, panels scroll internally ]          │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

### Persistent elements (all views)
- **Function bar** (h-8): `SIGMA INTELLIGENCE` label · view switcher tabs · regime + confidence · refresh countdown + FETCH button
- **Moving ticker tape** (h-9): CSS marquee, 25 symbols, green/red colour-coded, pause-on-hover

### Design system (locked, no changes)
- Viewport-locked — `h-[calc(100vh-48px)]`, no page scroll, panels scroll internally
- Dark base, monospace (JetBrains Mono) throughout
- `text-win` (green) = bullish · `text-loss` (red) = bearish · `text-warning` (amber) = neutral
- No rounded corners, no card shadows — `border-subtle` (1px) dividers only
- Panel headers: `PANEL.CODE` in `text-[9px] font-mono font-bold text-muted uppercase tracking-[0.15em]`

---

## Moving Ticker Tape — 25 Symbols

CSS marquee animation. Loops continuously. Pauses on hover. Single row.

```
►► BTC 94,200 ▲+1.2%  ·  ETH 3,140 ▼-0.4%  ·  SOL 182 ▲+2.1%  ·  BNB 598 ▲+0.8%  ·  XRP 0.52 ▲
   NVDA 876 ▲+2.4%  ·  SMH 218 ▲+1.8%  ·  SOXX 214 ▲+1.6%  ·  QQQ 441 ▲+0.9%  ·  SPY 521 ▲+0.4%
   GOLD 2,341 ▲+0.1%  ·  SILVER 29.4 ▲+0.3%  ·  COPPER 4.42 ▼-0.2%  ·  OIL 82.3 ▼-0.8%
   US10Y 4.32% ▼  ·  US2Y 4.81% ▼  ·  DXY 103.2 ▼-0.3%  ·  VIX 18.2 ▼  ·  HYG 79.4 ▲+0.1%
```

### Symbol list by category

| Category | Symbols | Data source |
|----------|---------|-------------|
| Crypto core | BTC, ETH, SOL, BNB, XRP | Binance public API (no key) |
| AI infrastructure | NVDA, SMH, SOXX, MSFT | Yahoo Finance (server-side) |
| Equity indices | SPY (SPX), QQQ (NDX), IWM (RUT) | Yahoo Finance |
| Commodities | GOLD (GC=F), SILVER (SI=F), COPPER (HG=F), OIL (CL=F) | Yahoo Finance |
| Yields | US10Y (^TNX), US2Y (^IRX) | FRED API (already integrated) |
| FX | DXY, EURUSD, USDJPY | FRED API |
| Volatility + credit | VIX (^VIX), HYG | Yahoo Finance |
| Emerging | EEM | Yahoo Finance |

### API route
`GET /api/market-data` — expand existing endpoint. Fetch crypto from Binance, everything else from Yahoo Finance (`https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d`). Cache 5 min server-side. Returns `{ symbol, price, changePct }[]`.

### Ticker component
```
src/components/intelligence/TickerTape.tsx
```
- `overflow: hidden` container, `width: 100%`
- Inner `div` with `animation: marquee linear infinite` — CSS keyframe `translateX(0) → translateX(-50%)`
- Content duplicated so the loop is seamless
- `hover: [animation-play-state: paused]`
- Colour: `changePct >= 0 ? text-win : text-loss`

---

## View 1: TERMINAL
**Status: ✅ SHIPPED (basic)**

The existing Bloomberg layout — already live. Needs one upgrade: replace static `TickerStrip` with the moving `TickerTape` component.

```
┌─ SIGMA INTELLIGENCE ─── [ TERMINAL* ] [ MICRO ] [ MAP ] [ AI.DESK ] ─── RISK-ON 84% ─┐
├─►► BTC 94,200 ▲+1.2%  ·  ETH 3,140 ▼-0.4%  ·  GOLD 2,341 ▲+0.1% ···················─►┤
├──────────────┬──────────────────────────────────────────┬──────────────────────────────┤
│ MACRO.1      │ AI.BRIEF                                 │ RISK.3                        │
│ ──────────── │ ──────────────────────────────────────── │ ────────────────────────────  │
│ FEDFUNDS     │ BULLISH  CONF 84%                        │ 3 HIGH                        │
│  5.33%  ↓ NEU│ ──────────────────────────────────────── │ ──────────────────────────── │
│ CPI YOY      │ BTC rallying on softer CPI data. Macro   │ SOLAR STORM    HIGH  APR 24  │
│  3.1%   ↑ BUL│ supports risk-on. DXY weakness at 103.  │ TARIFF PAUSE   MED   APR 25  │
│ T10Y2Y       │ KEY RISK: Fed speakers Friday 25 Apr.    │ TYPHOON PHL    HIGH  APR 24  │
│ -0.45%  ↑ BUL│                                         │                               │
│ UMICH S      │                                         │                               │
│  67.5   ↓ BEA│                                         │                               │
├──────────────┴──────────────────────────────────────────┴──────────────────────────────┤
│ NEWS.CRYPTO  BUL H/M/L  │  NEWS.MACRO  BUL H/M/L  │  NEWS.RISK  BUL H/M/L             │
│ (text rows, scrollable) │  (text rows, scrollable) │  (text rows, scrollable)          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

**Remaining work for TERMINAL:**
- Swap `TickerStrip` → `TickerTape` (new marquee component)
- Add view switcher tabs to function bar

---

## View 2: MICRO
**Status: 🔲 NOT STARTED**

Two-panel layout. Left: crypto on-chain metrics. Right: equity research (sector rotation + earnings + company deep-dive).

```
┌─ MICRO ─────────────────────────────────────────────────────────────────────────────────┐
│ CRYPTO.ONCHAIN                      │  EQUITY.RESEARCH                                  │
│ ──────────────────────────────────  │  ─────────────────────────────────────────────── │
│ Fear & Greed    72  GREED  BUL      │  SECTOR ROTATION (today)                          │
│ Exchange Inflow  +12.4k BTC  BEA   │  ─────────────────────────────────────            │
│ Exchange Outflow -18.2k BTC  BUL   │  Technology    +1.82%   BUL                        │
│ Funding (perp)   +0.021%    BUL    │  Energy        +0.44%   BUL                        │
│ Open Interest    $18.2B      NEU   │  Financials    -0.21%   BEA                        │
│ Long/Short       1.24        BUL   │  Healthcare    -0.08%   BEA                        │
│ BTC Dominance    52.3%       NEU   │  Utilities     -0.31%   BEA                        │
│ ─────────────────────────────────  │  Consumer Disc +0.88%   BUL                        │
│ Liq Long  $88,200               │  ─────────────────────────────────────            │
│ Liq Short $101,400              │  EARNINGS THIS WEEK                               │
│ ─────────────────────────────────  │  ─────────────────────────────────────            │
│ ETH Gas     12 gwei   BUL         │  Apr 24  TSLA  After  EPS est $0.43              │
│ Active Addr  890k     BUL         │  Apr 25  META  After  EPS est $4.68              │
│ SOPR         1.04     BUL         │  Apr 28  GOOGL Before EPS est $2.01              │
│ MVRV Z-Score  2.3     NEU         │  Apr 29  MSFT  After  EPS est $3.22              │
│                                    │  ─────────────────────────────────────            │
│                                    │  DEEP DIVE — [ AAPL            ]  [GO]            │
│                                    │  ─────────────────────────────────────            │
│                                    │  AAPL  $192.40  PE 28.4  Beta 1.12  MktCap $2.9T │
│                                    │  Rev   $119B  ▲+5.1%   NI $28.4B  ▲+7.2%        │
│                                    │  Debt/Eq 1.82  FCF $89.2B  ROE 147%             │
│                                    │  Next Earnings: Jul 31                            │
└────────────────────────────────────┴──────────────────────────────────────────────────┘
```

### Crypto on-chain data sources

| Metric | Source | Auth |
|--------|---------|------|
| Fear & Greed Index | `https://api.alternative.me/fng/` | None |
| Exchange inflow/outflow | CoinGecko `/coins/{id}/market_chart` + Binance | None |
| Funding rate (perpetual) | Binance `GET /fapi/v1/fundingRate` | None |
| Open interest | Binance `GET /fapi/v1/openInterest` | None |
| Long/short ratio | Binance `GET /futures/data/globalLongShortAccountRatio` | None |
| BTC dominance | CoinGecko `/global` | None |
| Liquidation levels | Binance `GET /fapi/v1/allForceOrders` (approx) | None |
| ETH gas | Etherscan `gastracker` module | Free key |
| Active addresses, SOPR, MVRV | Glassnode free tier OR CryptoQuant free | Free key |

### Equity data sources (Financial Modeling Prep)

| Data | FMP endpoint | Req cost |
|------|-------------|----------|
| Sector performance | `/api/v3/sectors-performance` | 1 req |
| Earnings calendar | `/api/v3/earning_calendar?from=X&to=Y` | 1 req |
| Company quote | `/api/v3/quote/{symbol}` | 1 req |
| Income statement | `/api/v3/income-statement/{symbol}?limit=1` | 1 req |
| Company profile | `/api/v3/profile/{symbol}` | 1 req |

**Free tier:** 250 req/day. Cache sector + earnings for 4h. Company deep-dive cached per symbol for 1h.

### Backup / fallback

| If FMP is down | Use |
|---------------|-----|
| Financial statements | SEC EDGAR: `https://data.sec.gov/api/xbrl/companyfacts/CIK{id}.json` — free, unlimited, official |
| Stock prices + basic info | Yahoo Finance: `https://query1.finance.yahoo.com/v8/finance/chart/{symbol}` — no key |
| Earnings (informal) | Yahoo Finance `https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}?modules=calendarEvents` |

### New API routes

```
GET  /api/micro/crypto          — Fear&Greed + Binance (funding, OI, L/S) + CoinGecko (dominance)
GET  /api/micro/equity          — FMP sector performance + earnings calendar (next 14 days)
GET  /api/micro/equity/[ticker] — FMP company deep dive (quote + income + profile)
```

### New component files

```
src/components/intelligence/views/MicroView.tsx       — orchestrator
src/components/intelligence/micro/CryptoOnChain.tsx   — left panel
src/components/intelligence/micro/SectorRotation.tsx  — right top
src/components/intelligence/micro/EarningsCalendar.tsx — right middle
src/components/intelligence/micro/CompanyDeepDive.tsx — right bottom (search input)
```

---

## View 3: MAP
**Status: 🔲 NOT STARTED**

Full-viewport interactive risk map. Static 2D (Leaflet.js, dark tiles). Live event pins. Right sidebar with event list + chokepoint status.

```
┌─ MAP.RISK ──────────────────────────────────────────────────────────┬──────────────────┐
│                                                                      │ ACTIVE EVENTS    │
│  [Leaflet.js — CartoDB Dark Matter tile layer]                      │ ──────────────── │
│                                                                      │ 🔴 M6.2 Japan    │
│  [Pins on map:]                                                      │    APR 24  HIGH  │
│  🔴 = Earthquake   HIGH  — USGS magnitude 5+                        │ 🟠 Wildfire CA   │
│  🟠 = Fire / Storm MED   — NASA EONET                               │    APR 23  MED   │
│  🟡 = Shipping     MED   — manual chokepoint overlays               │ 🟡 Suez Delay    │
│  🔵 = Geopolitical LOW   — parsed from news.risk feed               │    APR 22  MED   │
│                                                                      │ 🔴 Typhoon PHL   │
│  [Click pin → popup: title, type, severity, date, affected assets]  │    APR 24  HIGH  │
│                                                                      │ ──────────────── │
│                                                                      │ CHOKEPOINTS      │
│                                                                      │ ──────────────── │
│                                                                      │ Hormuz  ELEVATED │
│                                                                      │ Suez    NORMAL   │
│                                                                      │ Malacca NORMAL   │
│                                                                      │ Taiwan  ELEVATED │
│                                                                      │ Dover   NORMAL   │
└─────────────────────────────────────────────────────────────────────┴──────────────────┘
```

### Data sources

| Event type | Source | API | Refresh |
|-----------|---------|-----|---------|
| Earthquakes (M4.5+) | USGS GeoJSON feed | `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson` | None, free |
| Fires, storms, floods, volcanic | NASA EONET | **Already integrated** — `/api/intelligence/news` → risk feed | Already fetched |
| Shipping chokepoints | Static JSON (hardcoded 8 chokepoints with lat/lon + status) | None | Manual update |
| Geopolitical events | AI-parsed from `news.risk` items — extract lat/lon from title/description using regex + known location map | None (existing data) | With news refresh |

### Chokepoints static data (hardcoded)
```json
[
  { "name": "Strait of Hormuz",  "lat": 26.57, "lon": 56.45, "status": "ELEVATED" },
  { "name": "Suez Canal",        "lat": 30.42, "lon": 32.35, "status": "NORMAL"   },
  { "name": "Strait of Malacca", "lat": 1.25,  "lon": 103.82,"status": "NORMAL"   },
  { "name": "Taiwan Strait",     "lat": 24.5,  "lon": 119.5, "status": "ELEVATED" },
  { "name": "Strait of Dover",   "lat": 51.1,  "lon": 1.4,   "status": "NORMAL"   },
  { "name": "Bosphorus",         "lat": 41.1,  "lon": 29.05, "status": "NORMAL"   },
  { "name": "Panama Canal",      "lat": 9.0,   "lon": -79.5, "status": "NORMAL"   },
  { "name": "Cape of Good Hope", "lat": -34.35,"lon": 18.47, "status": "NORMAL"   }
]
```

### New API routes
```
GET /api/map/events   — USGS earthquakes + NASA EONET (already fetched, reuse) + geo-parsed risk news
```

### New component files
```
src/components/intelligence/views/MapView.tsx         — orchestrator + Leaflet init
src/components/intelligence/map/EventSidebar.tsx      — right panel list + chokepoints
src/components/intelligence/map/EventPin.tsx          — custom Leaflet marker
```

**Library:** `leaflet` + `react-leaflet` (lightweight, MIT, dark tiles from CartoDB: `https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`)

---

## View 4: AI.DESK
**Status: 🔲 NOT STARTED**

Full-viewport AI chat. Left panel: live context snapshot (what the AI can see). Right panel: chat interface with quick-prompt suggestions.

```
┌─ AI.DESK ───────────────────────────────────────────────────────────────────────────────┐
│ CONTEXT.SNAPSHOT              │  SIGMA AI — LLAMA 3.3 70B                               │
│ ────────────────────────────  │  ──────────────────────────────────────────────────────│
│ REGIME: RISK-ON  84%          │                                                         │
│ MULT: ×1.2                    │  QUICK PROMPTS                                          │
│                               │  ────────────────────────────────────                  │
│ MARKET                        │  [ Key risk today ]                                     │
│ BTC  +1.2%  ETH  -0.4%       │  [ Is this a good setup for GOLD long? ]                │
│ GOLD +0.1%  DXY  -0.3%       │  [ Macro summary in 3 bullets ]                         │
│ NVDA +2.4%  VIX   18.2       │  [ What to watch this week ]                            │
│                               │  [ Crypto regime: risk-on or risk-off? ]               │
│ TOP SIGNALS                   │  ──────────────────────────────────────────────────────│
│ • BTC ETF inflows surge       │                                                         │
│ • Fed speak hawkish Tues      │  You: does this CPI print change anything for GOLD?    │
│ • Tariff pause announced      │                                                         │
│ • NVDA earnings beat          │  AI: CPI at 3.1% vs 3.3% consensus — soft print.      │
│                               │  Combined with DXY weakness at 103.2 and current       │
│ MACRO PULSE                   │  Risk-On regime (84%), GOLD thesis is intact.          │
│ FEDFUNDS  5.33%  ↓  NEU      │  Macro is supportive. The only invalidation is if      │
│ CPI YOY   3.1%   ↑  BUL      │  Fed speakers on Friday turn hawkish — watch 104.2     │
│ T10Y2Y   -0.45%  ↑  BUL      │  DXY as the line in the sand.                          │
│                               │                                                         │
│ ────────────────────────────  │  ──────────────────────────────────────────────────────│
│ CONTEXT: ACTIVE ✓             │  [_______________________________________________] SEND │
│ Groq Llama 3.3 70B            │                                                         │
│ ~2,400 tokens context         │                                                         │
└───────────────────────────────┴─────────────────────────────────────────────────────────┘
```

### How context is assembled (on every question)
```
system: You are SIGMA AI, an expert macro-quant analyst for a professional trader.
        Current date: {date}
        
        MARKET REGIME: {regime} — Confidence {conf}% — Risk multiplier {mult}x
        
        MARKET DATA:
        {ticker list with prices and % change}
        
        MACRO INDICATORS:
        {MacroIndicator rows}
        
        TOP NEWS (last fetch):
        CRYPTO: {top 5 headlines}
        MACRO:  {top 5 headlines}
        RISK:   {top 4 headlines}
        
        AI BRIEF SUMMARY: {brief.brief}
        KEY RISK: {brief.key_risk}

user: {question}
```

Context is ~2,000-2,500 tokens. Well within Llama 3.3 70B's 128k context window. Fast response (~1-2s via Groq).

### Chat history
- React `useState` — session only, no database
- `[{ role: 'user' | 'assistant', content: string, timestamp: number }]`
- Max 20 messages kept in context window (older ones dropped)
- Clear history button

### New API routes
```
POST /api/intelligence/chat   — { question, context } → Groq stream → SSE response
```

### New component files
```
src/components/intelligence/views/AIDeskView.tsx      — orchestrator
src/components/intelligence/ai/ContextSnapshot.tsx    — left panel (live data summary)
src/components/intelligence/ai/ChatInterface.tsx      — right panel (chat + quick prompts)
src/components/intelligence/ai/ChatMessage.tsx        — individual message row
```

---

## Scaffold Changes (all views share these)

### Multi-view wrapper
```
src/components/intelligence/IntelligenceClient.tsx    — REPLACE with view-switcher wrapper
src/components/intelligence/views/TerminalView.tsx    — extract current TERMINAL layout here
```

`IntelligenceClient` becomes:
```tsx
type IntelView = 'terminal' | 'micro' | 'map' | 'ai';
const [view, setView] = useState<IntelView>('terminal');
```

### Function bar + tab switcher
```tsx
<FunctionBar view={view} onViewChange={setView} regime={...} countdown={...} onFetch={...} />
```

Tab labels: `TERMINAL` · `MICRO` · `MAP` · `AI.DESK`
Active tab: `text-primary border-b border-primary` (2px bottom border, no background fill)

### TickerTape component (replaces TickerStrip)
```
src/components/intelligence/TickerTape.tsx
```

---

## Full Data Source Registry

| Data | Source URL | Key needed? | Refresh |
|------|-----------|-------------|---------|
| Crypto prices (BTC, ETH, SOL, BNB, XRP) | Binance public REST | None | 5 min |
| Stock/ETF prices (NVDA, SPY, QQQ, etc.) | Yahoo Finance (server-side) | None | 5 min |
| Yields (US10Y, US2Y, DXY, EURUSD) | FRED API | **Already have** | 5 min |
| Macro indicators (CPI, FEDFUNDS, etc.) | FRED API | Already have | 5 min |
| News: crypto, macro, risk | RSS feeds (existing) | None | 5 min |
| AI brief + regime | Groq / Llama 3.3 70B (existing) | Already have | On demand |
| Vector search | Qdrant Cloud (existing) | Already have | On demand |
| Fear & Greed | alternative.me/fng | None | 1h |
| Funding rate, OI, L/S ratio | Binance futures API | None | 5 min |
| BTC dominance | CoinGecko `/global` | None | 15 min |
| ETH gas | Etherscan `gastracker` | **Free key needed** | 5 min |
| On-chain (SOPR, MVRV, active addr) | Glassnode free OR CryptoQuant free | **Free key needed** | 1h |
| Earthquakes | USGS GeoJSON feed | None | 5 min |
| Fires, storms, floods | NASA EONET (existing) | Already have | 5 min |
| Sector performance | FMP `/sectors-performance` | **FMP key needed** | 1h |
| Earnings calendar | FMP `/earning_calendar` | FMP key needed | 4h |
| Company financials | FMP `/income-statement`, `/profile` | FMP key needed | 1h |
| FMP fallback | SEC EDGAR + Yahoo Finance | None | On demand |

### Environment variables to add to `.env.local`
```
FMP_API_KEY=your_key_here
ETHERSCAN_API_KEY=your_key_here
GLASSNODE_API_KEY=your_key_here   # optional — has free fallbacks
```

---

## Build Sequence

### Phase 0 — Already shipped ✅
- Basic Bloomberg Terminal layout (TERMINAL view)
- MacroPulse dense rows, NewsFeed text rows, AIBrief center panel
- Default route → `/intelligence`

### Phase 1 — Scaffold + Ticker Tape (next session)
1. Create `TickerTape.tsx` — CSS marquee, 25 symbols, Yahoo Finance + Binance + FRED
2. Expand `/api/market-data` to return all 25 symbols
3. Refactor `IntelligenceClient` → multi-view wrapper + `TerminalView`
4. Add view switcher tabs to function bar (non-functional tabs for MICRO/MAP/AI)
5. Wire moving tape into all views

### Phase 2 — MAP view (1 session)
1. Install `leaflet` + `react-leaflet`
2. `GET /api/map/events` — USGS + EONET reuse + chokepoints JSON
3. `MapView.tsx` — Leaflet init, CartoDB dark tiles, event pins
4. `EventSidebar.tsx` — right panel list + chokepoint table
5. Wire MAP tab

### Phase 3 — AI.DESK view (1 session)
1. `POST /api/intelligence/chat` — Groq with assembled context
2. `AIDeskView.tsx` + `ContextSnapshot.tsx` + `ChatInterface.tsx`
3. Quick prompts, chat history state, streaming response
4. Wire AI.DESK tab

### Phase 4 — MICRO view (1-2 sessions)
**Requires:** FMP key, optional Etherscan + Glassnode keys
1. `GET /api/micro/crypto` — Fear&Greed + Binance futures + CoinGecko
2. `GET /api/micro/equity` — FMP sector + earnings
3. `GET /api/micro/equity/[ticker]` — FMP company deep dive
4. `MicroView.tsx` + `CryptoOnChain.tsx` + `SectorRotation.tsx` + `EarningsCalendar.tsx` + `CompanyDeepDive.tsx`
5. Wire MICRO tab

---

# PLAN B — Quant Lab (merged, LEAN CLI wired)
**Status: 🔲 NOT STARTED — begins after Phase 1 Intelligence scaffold**

## Context
The Backtest Lab has good infrastructure but a clunky tab layout. The Strategy Builder has Playground (useful), Composer (ambitious), and Learn (Syafiq wants to keep). Merge everything into `/quant-lab` with two top-level modes: `[LAB]` and `[LEARN]`. LAB mode wires directly to LEAN CLI in `workspace/sigma-lean/`.

## Design decisions (locked)
- One route `/quant-lab` — old routes redirect
- Two modes: `[LAB]` (3-panel + LEAN console) · `[LEARN]` (topic sidebar + content)
- LEAN CLI wired — RUN button triggers `lean backtest "B2BZoneStrategy"`, streams stdout, parses JSON results
- Same viewport-locked approach

## Layout — LAB mode

```
┌─ QUANT LAB ─── [ LAB ] [ LEARN ] ──────────────── B2BZoneStrategy ─── LEAN v3 ──────┐
├──────────────┬──────────────────────────────────────────┬───────────────────────────┤
│ STRATEGY.DEF │ CHART.VIEW                               │ PERFORMANCE.OUT           │
│ ──────────── │ ──────────────────────────────────────── │ ─────────────────────     │
│ Symbol       │                                          │ Sharpe    1.16            │
│  BTCUSDT  ▾  │  [Lightweight-charts candlestick +       │ Calmar    3.90            │
│ Resolution   │   B2B zone rectangle overlays]           │ MaxDD     8.4%            │
│  H1       ▾  │                                          │ WinRate   42%             │
│ Start Date   │ ─── [ CHART ] [ EQUITY ] [ DRAWDOWN ]   │ CAGR      28.3%           │
│  2024-01-01  │                                          │ Trades    130             │
│ End Date     │  [Tab-switched sub-chart]                │ ─────────────────────     │
│  2024-03-31  │                                          │ [Trade log table]         │
│ Capital      │                                          │ time / dir / entry / R    │
│  $100,000    │                                          │ ─────────────────────     │
│ Risk %       │                                          │ [Run history dropdown]    │
│  1.0%        │                                          │  ▾ 2026-04-15 14:42       │
│ [▶ RUN]      │                                          │                           │
├──────────────┴──────────────────────────────────────────┴───────────────────────────┤
│ LEAN.ENGINE  [▶ RUN]  ██████████░░  78%  ETA 12s  STATUS: RUNNING                  │
│ > Loading 35,064 bars BTCUSDT H1 Binance                                             │
│ > OnData... 2024-02-15 — LONG @ 52,340                                               │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

## Layout — LEARN mode

```
┌─ QUANT LAB ─── [ LAB ] [ LEARN ] ──────────────────────────────────────────────────┐
├─────────────────────┬──────────────────────────────────────────────────────────────┤
│ TOPICS               │ Sharpe Ratio                                                │
│ ───────────────────  │ ──────────────────────────────────────────────────────────  │
│ > Sharpe Ratio       │ Measures risk-adjusted return: excess return / std dev.     │
│   Calmar Ratio       │                                                             │
│   Sortino Ratio      │   S = (R_p - R_f) / σ_p                                    │
│   Max Drawdown       │                                                             │
│   Win Rate           │ A Sharpe > 1.0 is acceptable. > 2.0 is strong.             │
│   R-Multiple         │ Your Test 13A: 1.16.  Test 10C (Sortino): 3.06.            │
│   B2B Zone Logic     │                                                             │
│   Entry/Exit Rules   │                                                             │
└─────────────────────┴─────────────────────────────────────────────────────────────┘
```

## New files to create

| File | Purpose |
|------|---------|
| `src/app/quant-lab/page.tsx` | Server component — run history SSR |
| `src/components/quant-lab/QuantLabClient.tsx` | Mode switch orchestrator |
| `src/components/quant-lab/StrategyDefPanel.tsx` | Left config panel |
| `src/components/quant-lab/ChartPanel.tsx` | Center chart + zone overlays |
| `src/components/quant-lab/PerformancePanel.tsx` | Right metrics + trade log |
| `src/components/quant-lab/LeanConsole.tsx` | Bottom execution console |
| `src/components/quant-lab/LearnPanel.tsx` | LEARN mode (reuse strategy-builder LearnTab) |
| `src/app/api/lean/run/route.ts` | POST — spawn lean backtest, return jobId |
| `src/app/api/lean/status/[jobId]/route.ts` | GET SSE — stream lean stdout |
| `src/app/api/lean/results/route.ts` | GET — parse latest backtest JSON |

## Files to modify
| File | Change |
|------|--------|
| `src/app/backtest-lab/page.tsx` | `redirect('/quant-lab')` |
| `src/app/strategy-builder/page.tsx` | `redirect('/quant-lab')` |
| `src/components/layout/Sidebar.tsx` | Remove BACKTEST LAB + STRATEGY; add QUANT LAB |

## LEAN prerequisite (manual — do before first UI run)
```bash
cd workspace/sigma-lean
rm -rf data/crypto
python scripts/parquet_to_lean.py
lean backtest "B2BZoneStrategy"
```
Validate: fill prices in $40k–$70k range (Jan–Mar 2024 BTC). If correct, LEAN is healthy.

---

## Overall Build Status

| Item | Status |
|------|--------|
| Default route → `/intelligence` | ✅ Done |
| Intelligence TERMINAL layout (basic) | ✅ Done |
| MacroPulse dense rows | ✅ Done |
| NewsFeed text rows | ✅ Done |
| AIBrief center panel | ✅ Done |
| Moving ticker tape (25 symbols) | 🔲 Phase 1 |
| Multi-view scaffold + tab switcher | 🔲 Phase 1 |
| MAP view (Leaflet + USGS + EONET) | 🔲 Phase 2 |
| AI.DESK view (chat + context) | 🔲 Phase 3 |
| MICRO view (on-chain + equity FMP) | 🔲 Phase 4 — needs FMP key |
| Quant Lab (LEAN CLI wired) | 🔲 Plan B |

**Immediate blocker for Phase 4:** FMP API key. Get free key at `financialmodelingprep.com`.
**Immediate blocker for LEAN:** Data rebuild (one CLI command above).
