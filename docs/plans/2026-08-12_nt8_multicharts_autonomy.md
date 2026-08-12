# Autonomous build + test loop on NinjaTrader 8 and MultiCharts

**Date:** 2026-08-12 · **Status:** research only, nothing built · **Author:** Claude Code (web research session)

Question asked: can the MQL5 autonomous loop (agent writes strategy → compiles → backtests →
reads a fitness number → logs → mutates) be reproduced on NinjaTrader 8 and on MultiCharts?

Every claim below is tagged **CITED** (source in the link list), **DERIVED** (my inference from a
cited fact), or **ASSUMED** (untested judgement). Nothing here is MEASURED — no platform was
installed or run in this session.

---

## 1. The loop, as five verbs

The MQL5 factory already implements these. Any new platform is just a new adapter:

| Verb | MQL5 today |
|---|---|
| `write_source` | write `.mq5` to `mt5/Experts/` |
| `compile` | MetaEditor CLI |
| `run_test` | Strategy Tester, headless launch |
| `read_fitness` | `OnTester()` returns one number |
| `read_results` | per-trade CSV → `research.db` |

A platform is automatable exactly to the degree that all five have a non-GUI entry point.
Score below: **NT8 = 4.5/5, MultiCharts = 2.5/5.**

---

## 2. NinjaTrader 8

### 2.1 write_source — works
Strategies are plain C# files under `Documents\NinjaTrader 8\bin\Custom\Strategies\*.cs`. An agent
writes the file directly; nothing GUI about it. **CITED.**

### 2.2 compile — works, with a caveat
- NT keeps an MSBuild project at `Documents\NinjaTrader 8\bin\Custom\NinjaTrader.Custom.csproj`. **CITED.**
- Saving a script from any external editor while the NinjaScript Editor is open **triggers NT to
  compile it itself**. That is the officially blessed external-editor workflow. **CITED.**
- NinjaTrader's own guidance: do *not* compile with an external toolchain; treat Visual Studio as a
  text editor only. Compiling `NinjaTrader.Custom.csproj` yourself with msbuild is technically
  possible but unsupported and risks the platform loading a DLL it did not build. **CITED.**
- **DERIVED:** the reliable agent path is "write file → NT's own watcher compiles → read the
  compile-error log", i.e. the same shape as MC's watcher, not an external msbuild call.
- Third-party proof that in-process compilation is reachable programmatically: CrossTrade's add-on
  exposes `CompileNinjaScript(in_memory: true)` for syntax validation before writing to disk. **CITED.**

### 2.3 run_test — works, but undocumented
`NinjaTrader.exe` accepts backtest switches, reported by users and reproduced in the NT forums:

```
NinjaTrader.exe /backtest <StrategyName>
                /template "C:\Users\<user>\Documents\NinjaTrader 8\templates\Strategy\<Strategy>\<Template>.xml"
                /instrument ES JUN24
                /fromdate 03/07/2024 /todate 03/08/2024
                /starttime 06:36 /endtime 7:09
                /output "C:\Backtests\<Strategy><Template>.txt"
                /displaylogs /exporttrades /headless
```
**CITED** (community-reported, verbatim from the forum thread).

**The catch, stated plainly:** NinjaTrader staff's position is that there is *no documented or
supported way* to automate backtests. These switches are undocumented surface. **CITED.**
**DERIVED:** they can vanish or change on any minor release, so the adapter must self-verify (run a
known strategy, assert a known result) at the top of every session rather than trust them.

Parameters travel via the `/template` XML, which is a plain file — so an agent mutates parameters by
writing a template, not by clicking. **DERIVED.**

### 2.4 read_fitness — works, and is the strongest part
NT8 exposes **custom OptimizationFitness** as a first-class NinjaScript type:
- File lives in `Documents\NinjaTrader 8\bin\Custom\OptimizationFitnesses`. **CITED.**
- Inherit `OptimizationFitness`, override `OnCalculatePerformanceValue`, set `Value`. **CITED.**
- The optimizer always **maximises** `Value`; minimise by inverting. **CITED.**
- Custom **Optimizers** and custom **Performance Metrics** are also supported NinjaScript
  categories, per the official developer docs. **CITED.**

**DERIVED:** this is a direct analogue of MQL5 `OnTester()`. The GRW barrier objective
(P(target before floor) on a fixed stake) ports across as a custom OptimizationFitness with no
change of shape — the objective is *not* a platform lock-in.

### 2.5 read_results — works
`/output` writes a summary file and `/exporttrades` dumps trades. **CITED.** Better and more
portable: have the strategy itself write per-trade CSV/SQLite from `OnTermination`, exactly as the
MT5 side already does — then the ingest layer is platform-agnostic. **DERIVED.**

### 2.6 Data in
- The instrument must already exist in NT before importing. **CITED.**
- Tick import format is `yyyyMMdd HHmmss;price;volume`, semicolon-separated, imported through the
  Historical Data window; timezone must be set explicitly at import. **CITED.**
- **DERIVED:** Arctic → NT text is a thin adapter (~50 lines). The GUI import step is the only
  hand-operated bit, and it is one-off per data refresh, not per backtest — acceptable.

### 2.7 The buy option: CrossTrade MCP
An MCP server already does most of this and is worth pricing against build effort. **CITED:**
- Tools: `LookupNinjaScriptSymbol`, `GetNinjaScriptHelp`, `CompileNinjaScript(in_memory)`,
  `RunStrategyBacktest`, `optimization.parameters_sweep` over 41 fitness functions,
  `DeployStrategy`, `GetDeployedStrategyState`.
- Architecture: cloud-hosted MCP ↔ a CrossTrade add-on inside the NT8 desktop (v1.13.0+).
- Claimed fidelity: backtest results "bit-identical" to the NT8 UI, checked on SampleMACrossOver
  (NetProfit $800, ProfitFactor 1.14, 264 trades). **Vendor's own number, not independently verified.**
- Price: Elite plan, $99/month.
- Stated limits: cartesian sweeps only (no genetic), numeric parameters only (bools/enums must be
  fixed), NT8 must be running, jobs are async and expire after 30 minutes.

**ASSUMED:** the numeric-only parameter limit is the binding constraint for us — a strategy factory
mutates structure and boolean switches, not just numbers. So CrossTrade covers the *test* stage well
and the *search* stage poorly.

### 2.8 Verdict on NT8
Automatable end to end today, with one supported seam (custom fitness), two semi-supported seams
(file-drop codegen, watcher compile), and one unsupported seam (`/headless` CLI). The unsupported
seam is the only real fragility, and it has a fallback (drive Strategy Analyzer from a custom AddOn —
which CrossTrade demonstrably does, though the Strategy Analyzer API is not public and the forum
feature request for one is still open). **CITED** for the open request; **DERIVED** for the fallback.

---

## 3. MultiCharts

### 3.1 write_source + compile — best of the three platforms
MultiCharts .NET **watches its own source folder and compiles on save**:
- Path: `%allusersprofile%\Application Data\TS Support\MultiCharts .NET64\StudyServer\Techniques\CS\`. **CITED.**
- Filename encodes name and type: `_TPO_.Indicator.CS`. **CITED.**
- Editing a `.cs`/`.vb` file outside the PowerLanguage .NET Editor is detected and compiled
  automatically; a study already on a chart is recreated after a successful compile. **CITED.**
- One constraint: external assembly references must be added through the PowerLanguage .NET Editor,
  not by hand. **CITED.**

**DERIVED:** an agent gets compiled MultiCharts strategies by writing a file — no GUI, no CLI needed.
This seam is cleaner than NT8's.

### 3.2 read_fitness — works
Two routes, both documented: `SetCustomFitnessValue` inside the signal, or a JavaScript custom
criterion in the Optimization Settings window. 18 built-in criteria otherwise. **CITED.**
**DERIVED:** the barrier objective is expressible here too.

### 3.3 run_test — this is where it breaks
- **No optimization API.** The public MultiCharts issue tracker still lists *"Optimization API in
  MultiCharts please!"* (MC-1655) as **OPEN**, with the requested use case being exactly ours —
  staged optimization across strategies and symbols running completely unattended. **CITED.**
- Command line is thin: opening a workspace, plus in-app dot-commands like `.at_toggle` to toggle
  auto-trading on a chart. `.at_toggle` still raises the legal pop-up when enabling, so it is useful
  as a kill-switch and near-useless as a starter. **CITED.**
- **Portfolio Trader has no command line at all** beyond opening a workspace, and does not accept
  the in-script `CommandLine` keyword. **CITED.**
- MultiCharts' stated reason for not adding some of this: it would nullify legally required
  confirmation pop-ups. **CITED.** **DERIVED:** that is a policy blocker, not a technical one, so
  waiting for it to change is a bad plan.

### 3.4 Data in — also GUI-bound
QuoteManager handles ASCII import through its menus. A command-line import is an **OPEN feature
request (MC-1445)**, not a feature. **CITED.** An ASCII *Export* Scheduler exists for getting data
out on a schedule. **CITED.** The heavy alternative is writing a plugin against the MultiCharts Data
API SDK (they hand it out on request, or sell the integration as custom dev) — that would let the
Arctic store feed MultiCharts directly as a "data source". **CITED** for the SDK's existence;
**ASSUMED** that this is weeks of work, not days.

### 3.5 Adjacent feature worth knowing
**Self-Adaptive Trading:** MultiCharts can periodically re-optimize a live strategy on new data and
adopt the new inputs, with trading continuing on the old parameters while the optimization runs.
**CITED.** **DERIVED:** this is automatic *re-fitting*, not automatic *discovery* — it re-tunes a
strategy you already chose. Useful later, irrelevant to a discovery loop, and it is an overfitting
hazard if adopted without an out-of-sample gate.

### 3.6 Verdict on MultiCharts
Codegen is excellent, objective function is fine, and the test stage has no headless entry point.
The only ways to close it are UI automation (AutoHotkey / Windows UIAutomation driving the
Optimization window) or paying MultiCharts for custom development. **DERIVED:** UI automation is
achievable but brittle in exactly the way that silently corrupts a research loop — a mis-clicked
setting produces a *plausible wrong number*, not an error, which is the worst failure mode we have.

---

## 4. Recommendation

1. **If a second platform is wanted, it is NinjaTrader 8.** It is the only one of the two with a
   non-GUI path through all five verbs today.
2. **Build the adapter, don't rewrite the loop.** Keep generate → mutate → log → gate in Python
   against `research.db`. Give it a platform interface of the five verbs. MQL5 is adapter #1; NT8
   would be adapter #2. That also makes the "does the edge survive a different execution engine?"
   test cheap, which is a genuine robustness check we cannot currently run at all.
3. **Trial CrossTrade before building NT8 plumbing.** $99/month against a week of reverse-engineering
   is a good trade for the *test* stage; expect to still write our own search/mutation layer because
   of the numeric-only parameter limit.
4. **Port the objective first, not last.** Rewriting the barrier objective as a custom
   `OptimizationFitness` is a half-day, needs no CLI, and it is the single piece that proves the
   mission is portable at all.
5. **MultiCharts: park it** unless there is a broker or data reason that only MultiCharts satisfies.
   Revisit if MC-1655 ever closes.

## 5. The concern to settle before any of this is worth doing

The live mandate is a fixed-stake XAUUSD barrier run at JustMarkets, and the execution venue for that
is MT5. **ASSUMED, needs Syafiq's answer:** NinjaTrader's home turf is futures, and neither NT8 nor
MultiCharts connects to a JustMarkets MT5 account. So this work pays off if the driver is *prop-firm
futures* or *engine-independence as a robustness test*, and pays off very little if the goal is a
better XAUUSD spot loop — in that case the existing MQL5 factory is already the right tool and the
effort is better spent on it.

---

## 6. Addendum — sim account, Strategy Analyzer, and the data reality (added same day)

Follow-up question: does NT8 have a demo account and an MT5-Strategy-Tester equivalent, for futures
and ETF work on real (or synthetic) data?

**Yes to both, and the tester is better than MT5's.** All **CITED** unless marked.

- **Free forever** for charting, backtesting and simulation. You pay only to trade live. **CITED.**
- **Sim101** is the built-in simulated account — tracks cash, P&L and margin like a live one, no
  expiry, tied to the install. Extra sim accounts need Multi-Provider mode enabled in Options. **CITED.**
- **Strategy Analyzer** = the Strategy Tester equivalent: trade-by-trade reports, parameter
  optimization (exhaustive and genetic), and **walk-forward analysis built in**, including anchored
  mode. MT5 has no native WFO. **CITED.**
- **Market Replay / Playback** replays stored tick data in real time — closer to a live dry-run than
  MT5's visual mode. **CITED.**

**The binding constraint is data, not the platform.** **CITED** for each figure:

| Source | What you get free |
|---|---|
| Market Replay (NT servers) | ~90 days of tick replay, popular instruments only |
| Kinetick free | End-of-day (daily) only — stocks, futures, FX |
| Kinetick paid | 180 days of tick |
| Continuum | ~1 year of historical tick |
| NT demo trial | 14 days of live streaming data; afterwards live is simulated/delayed, historical still real |
| Simulated Data Feed | no historical data at all — chart starts building from now |

Multi-year intraday/tick for futures is a paid purchase (Portara, FirstRate Data). **CITED.**

**DERIVED — the practical route:** NT8 imports arbitrary CSV as a custom instrument
(`yyyyMMdd HHmmss;price;volume`), so bring-your-own-data sidesteps the whole feed question, works
identically for synthetic series, and reuses the Arctic-style store we already run. Buy or generate
once, import, backtest offline forever.

**ASSUMED, flag before trusting a number:** Strategy Analyzer fills against bar data by default.
Given the standing real-ticks-only rule, any NT8 result must be run with **Tick Replay** (or a tick
data series) enabled, otherwise it flatters the edge the same way MT5 open-prices mode does. Verify
this setting exists and is on before logging a single result.

**DERIVED:** futures over ETFs is the right instinct for a first build — one exchange licence,
continuous sessions, cleaner contract-level cost modelling, and no free intraday equity data anyway
(Kinetick free is daily-only for stocks/ETFs).

## 7. Addendum — StrategyQuant QuantDataManager as the data pipe (added same day)

Question: can QuantDataManager (QDM) feed this?

**Right pipe, wrong reservoir for futures.**

### What it does well — **CITED**
- Free; Pro is **$49 lifetime** and buys download speed (10–15× CDN), verified downloads and no ads.
  The data itself is free either way.
- **Exports NinjaTrader tick format and NinjaTrader bar format natively**, alongside MT4/MT5 FXT/HST,
  Amibroker, Tradestation, Forex Tester, and generic comma/tab CSV. Direct pipe into NT8, no adapter.
- **Has a command line**: `QDataManager_console.exe`, with add/edit/delete symbols (`-a`/`-e`/`-d`),
  instruments (`-ia`/`-ie`/`-il`), import (`-di`), export (`-de`), clone with timezone and
  weekend-removal (`-dc`), and update-all (`-u`). Example:
  ```
  QDataManager_console.exe -a symbols=EURUSD,GBPUSD datasource=dukascopy datatype=TICK
  QDataManager_console.exe -de symbols=EURUSD_M1 timeframe=M1 datefrom=2018.01.01 dateto=2018.12.31
  ```
  **Caveat:** that doc page states it covers builds **prior to 119** — re-verify the flags against the
  installed build before wiring anything to them.
- Free sources: Dukascopy (forex, metals, CFDs — tick and minute), Yahoo (stocks), Darwinex,
  Binance / Bitfinex / Coinbase / Poloniex (crypto), plus a flexible importer for arbitrary CSV.

### Where it fails for futures — **CITED unless marked**
- StrategyQuant's own page: *"Commodity data are paid, there is no free source available."*
- There is **no real CME futures source**. The nearest thing is Dukascopy's `USA500.IDX`, a CFD whose
  price correlates with the front-month S&P futures contract.
- **DERIVED:** a CFD is not a futures contract — no contract months, no roll, no exchange volume, and
  broker-specific spreads. Every one of those matters to the strategies we would build.
- StrategyQuant's own forum, on using Dukascopy index data to trade index products: *"every broker
  using different specs and most probably your backtest will be a lie"*, contrasting CFD spreads with
  micro-futures spreads of ~1–2 ticks.
- Some Dukascopy symbols (bond CFDs, some stock CFDs, parts of the crypto/ETF/indices lists) are
  missing from QDM's downloadable list. **CITED.**
- **DERIVED:** Yahoo covers ETFs but as daily bars — it does not solve intraday ETF work either.

### Call
- **Use QDM** for FX/metals tick (including XAUUSD) and as the general CSV pipe into NT8. Its CLI makes
  the acquire-and-export step scriptable, which fits the loop.
- **Do not use it to source futures data.** For the futures build, start on NT8's own free Market
  Replay (~90 days) and Continuum (~1 year tick) to get a first credible run, then decide whether
  multi-year CME tick is worth buying (Databento / FirstRate Data / Portara). **ASSUMED** that ~1 year
  of tick is enough for a first honest read, not enough for a regime-robustness claim.

## 8. Addendum — solving the futures/ETF data bottleneck (added same day)

Question: where do we actually get historical GC (COMEX gold futures) or gold-ETF data good enough to
build and test on?

### 8.1 The reframe that comes first — **DERIVED**
We already hold **511M XAUUSD ticks, 2016→2026, in Arctic**. Spot gold and GC futures are the same
underlying. So the bottleneck is not "data to *build* on" — it is "a clean futures sample to *check*
the logic survives the venue change". That turns a four-figure data purchase into a small one.

What changes when porting spot gold logic to GC (**DERIVED**, each must be handled explicitly):
- contract months and rolls (spot has none)
- session shape — Globex ~23h with a daily break, vs 24/5 spot
- costs become commission + exchange fee **per contract**, not spread
- tick size $0.10 = $10/contract on GC, $1 on MGC
- **real exchange volume exists** — that is an upgrade, a signal class spot never gave us

### 8.2 Ranked sources — all prices **CITED**

**1. Databento — best fit, start here.**
- CME Globex MDP 3.0 (`GLBX.MDP3`): all futures and options on CME, CBOT, NYMEX, COMEX, 650k+ symbols.
- **History back to 2010-06-06.** Pre-2017 is capped at MBP-10 granularity (legacy FIX/FAST carried no
  full MBO).
- Covers `GC`, `MGC` (micro), `QO` (e-mini), `1OZ`.
- **$0.50/GB usage-based, plus $125 free credits on signup.**
- **ASSUMED — must be measured, not trusted:** trades/OHLCV-1m for one metal over ~15 years is small
  relative to $125 of credit; MBO/MBP-10 is not. Pull the cheap schemas first and check the invoice
  before scaling up.
- Python API — drops straight into the existing Arctic stack, and re-exports to NT8's CSV format.

**2. Kibot — one-time purchase, no subscription.**
- Top-10 continuous futures: **1-min $220 · tick + bid/ask $800**
- Top-25 continuous futures: **1-min $330 · tick + bid/ask $1,200**
- All futures, continuous + individual contracts (9,600+): **1-min $820 · tick + bid/ask $3,750**
- Top-50 ETFs: **1-min $450 · tick + bid/ask $1,350** · All ETFs: **1-min $1,200 · tick $3,600**
- Continuous series built **without back-adjustment**, so we apply our own roll method — good.
- Free samples exist but are stocks/ETFs only; futures samples on request.

**3. FirstRate Data — cheapest broad coverage, bars not ticks for GC.**
- GC: **1-min/5-min/30-min/1-hour/1-day, 31-Jan-2008 → present**; individual contracts from `GCZ08`
  plus continuous in unadjusted / absolute-adjusted / ratio-adjusted flavours; zipped CSV.
- No tick tier shown for GC on that page. Updates are **$99.95/yr** after the first free month.
- Purchase price is not printed on the instrument page — check the bundle pages. One 2021 forum report
  cites ~€200 for 70 futures back to 2006; **treat as indicative and stale, not a quote.**
- GLD ETF: ~21 years of 1-min available.

**4. Free options, and their real limits.**
- **NinjaTrader itself**: ~90 days Market Replay, ~1 year Continuum tick. Enough for a first honest
  run; not enough for a regime claim.
- **Interactive Brokers API**: free with an account, but **expired futures data older than two years
  past expiry is unavailable**, plus pacing limits (60 requests/10 min, 50 concurrent). **DERIVED:**
  the 2-year rule makes IB unusable for multi-year individual-contract backtests. Fine for recent data.
- **CME DataMine**: the official source, priced accordingly.
- **TradingView**: CME real-time from $7/month — a viewing subscription, not a bulk download.

### 8.3 Recommended sequence — **DERIVED**
1. Sign up to Databento, spend the **free $125** on `GC` + `MGC`: OHLCV-1m for 2010→now, plus trades
   for the most recent 2–3 years. Measure the actual cost before going wider.
2. Land it in Arctic beside XAUUSD; reuse the existing loaders.
3. Export to NT8 tick/bar CSV for the platform work (QDM or a 50-line writer both do this).
4. Buy breadth (Kibot top-10 tick at $800, or a FirstRate bundle) **only after** the loop has produced
   one result worth widening.

### 8.4 The honest flag — **DERIVED**
Futures carry a hard minimum capital that the live $20 barrier mandate cannot meet: one MGC contract
needs margin in the thousands, not tens. So this is a **separate research track**, justified as
engine-and-venue independence plus access to real volume — **not** a route to the GRW mission. Worth
saying out loud before any money is spent on data.

## 9. Addendum — project shape: paper-trade POC, then prop firms (added same day)

**Syafiq's call, 2026-08-12: this is a separate project. It must not touch the MT5 $20 XAUUSD
mission.** Recorded here so a future session cannot quietly merge them.

### 9.1 Separation — **DERIVED from rule 4a (namespace discipline)**
Give it its own repo at Desktop level with its own remote, the way `sigma-quant` / `sigma-research`
are decoupled. Not a subfolder of `baysix-technologies`. Reasons: a shared `research.db` would let
futures results surface in GRW/FOB gate queries, and column names collide across systems by accident.
Shared assets are copied deliberately (the barrier objective, the Arctic loaders), never imported by
proximity.

### 9.2 Phase 1 — paper-trade proof of concept, cost $0
NT8 is free for charting, backtesting and simulation, and `Sim101` never expires (§6). So the whole
ideation loop — generate → compile → backtest → score → forward-test on sim — can be proven end to
end without paying anyone. **DERIVED:** prove the loop before buying data breadth or an evaluation.
Data for this phase = Databento free credit (§8.3).

### 9.3 Phase 2 — prop firms, and why they fit
**DERIVED, and this is the interesting part:** a futures prop evaluation *is* a barrier problem.
Topstep's 50K: **$3,000 profit target against a $2,000 max loss** — hit the target before the floor.
That is the same objective family as the GRW mandate, so the barrier fitness function ports across
almost unchanged. One genuine escalation: prop drawdown **trails**. A $50K account with a $2,500
trailing drawdown that grows to $52,000 has its floor move up to $49,500. So the floor is a function
of the equity high-water mark, not a constant — a strictly harder and more interesting objective than
the fixed floor we solve today. **All figures CITED, but from review sites — reconfirm on the firm's
own rulebook before encoding any of them.**

Cost of entry is small: Topstep 50K evaluation **$109 one-time**; Apex evaluations nominally
$147–$517 but frequently discounted to ~$35 with promotions, and Apex moved from recurring to
one-time fees in 2026. **CITED, same caveat.**

### 9.4 The rules that constrain the autonomy — **CITED, verify per firm before building**
- **Apex:** allows bots during evaluation, but on funded Performance Accounts fully automated
  "set and forget" is **prohibited** — active human management is required. HFT and certain
  arbitrage strategies banned.
- **Topstep:** among the more automation-friendly; offers API access via TopstepX (ProjectX). But
  **every automated strategy needs prior written approval from their risk team**, with strategy
  details submitted. HFT, abusive exchange messaging and latency arbitrage are prohibited.
- **MyFundedFutures** is also named as permitting algorithmic trading.
- Platforms across the sector: Tradovate, Rithmic, NinjaTrader, ProjectX.

**DERIVED:** so the honest design target is an **autonomous researcher with a supervised trader** —
the loop discovers and validates strategies unattended, and a human stays in the loop on the funded
account because the rules require it. Building for fully hands-off funded trading would be building
something we are not allowed to run.

### 9.5 First three moves
1. Stand up the separate repo; copy in the barrier objective and the Arctic loader, nothing else.
2. Databento free credit → GC/MGC into Arctic → NT8 import → one manual backtest of a trivial
   strategy, to verify the whole chain end to end (including Tick Replay, §6).
3. Only then automate: custom `OptimizationFitness` first (§2.4), CLI/AddOn driving second.

## Sources

- [Automating Compilation and Backtesting of NinjaScript Code — NT forum](https://forum.ninjatrader.com/forum/ninjatrader-8/add-on-development/1261077-automating-compilation-and-backtesting-of-ninjascript-code)
- [Automating Backtests in NinjaTrader or Python — NT forum](https://forum.ninjatrader.com/forum/ninjatrader-8/add-on-development/1261076-automating-backtests-in-ninjatrader-or-python)
- [NinjaScript Overview — NinjaTrader Developer Docs](https://docs.ninjatrader.com/ninjascript)
- [Strategy Analyzer API request — NT forum](https://forum.ninjatrader.com/forum/suggestions-and-feedback/suggestions-and-feedback-aa/83864-strategy-analyzer-api)
- [Custom Optimization Fitness Metric NT8 — NT forum](https://forum.ninjatrader.com/forum/ninjatrader-8/platform-technical-support-aa/1091480-custom-optimization-fitness-metric-nt8)
- [Create a Custom Fitness Function for NinjaTrader 8](https://newsletter.huntgathertrade.com/p/create-a-custom-fitness-function)
- [Importing Historical Data — NT8 help guide](https://ninjatrader.com/support/helpGuides/nt8/importing.htm)
- [CrossTrade MCP for NinjaTrader 8](https://crosstrade.io/mcp-trading)
- [MultiCharts .NET — Integration with Microsoft Visual Studio](https://www.multicharts.com/trading-software/index.php?title=Integration_with_Microsoft_Visual_Studio)
- [Compiling MultiCharts .NET scripts — TradingCode](https://www.tradingcode.net/multicharts-net/net-editor/compile-scripts/)
- [Optimization API in MultiCharts please! — MC-1655, OPEN](https://www.multicharts.com/pm/public/multicharts/issues/MC-1655)
- [Import ASCII files with command line — MC-1445, OPEN](https://www.multicharts.com/pm/public/multicharts/issues/MC-1445)
- [MultiCharts Command Line](https://www.multicharts.com/trading-software/index.php?title=Command_Line)
- [Toggle MultiCharts .NET auto-trading — TradingCode](https://www.tradingcode.net/multicharts-net/command-line/toggle-auto-trading/)
- [Custom Criteria Optimization — MultiCharts help](https://www.multicharts.com/trading-software/index.php?title=Custom_Criteria_Optimization)
- [Self-Adaptive Trading — MultiCharts help](https://www.multicharts.com/trading-software/index.php?title=Self-Adaptive_Trading)
- [Portfolio Trader command line options — MultiCharts forum](https://www.multicharts.com/discussion/viewtopic.php?t=50270)
- [MultiCharts SDK / Data API](https://www.multicharts.com/features/sdk/)
- [NinjaTrader Trading Simulator](https://ninjatrader.com/trading-platform/trading-simulator/)
- [Operations > Simulator — NT8 help guide](https://ninjatrader.com/support/helpguides/nt8/simulation.htm)
- [Backtest a Strategy — NT8 help guide](https://ninjatrader.com/support/helpguides/nt8/backtest_a_strategy.htm)
- [Operations > Playback Connection — NT8 help guide](https://ninjatrader.com/support/helpguides/nt8/playback.htm)
- [Historical Data by Provider — NT8 help guide](https://ninjatrader.com/support/helpguides/nt8/data_by_provider.htm)
- [Kinetick free end-of-day data for NinjaTrader](https://kinetick.com/NinjaTrader)
- [How far back Market Replay goes — NT forum](https://forum.ninjatrader.com/forum/ninjatrader-8/platform-technical-support-aa/1336348-how-can-i-get-market-replay-data-from-3-months-ago)
- [QuantDataManager — StrategyQuant](https://strategyquant.com/quantdatamanager/)
- [QuantDataManager command line interface help](https://strategyquant.com/doc/quantdatamanager/quant-data-manager-command-line-interface-help/)
- [Export tick data to CSV for NinjaTrader — SQ forum](https://strategyquant.com/forum/topic/export-tick-data-to-csv-file-for-ninjatrader/)
- [Data for CFD trading strategies — SQ forum](https://strategyquant.com/forum/topic/data-for-cfd-trading-strategies/)
- [Dukascopy tick data missing symbols — SQ forum](https://strategyquant.com/forum/topic/dukascopy-tick-data-missing-symbols/)
- [Dukascopy S&P 500 Index CFD](https://www.dukascopy.com/swiss/english/cfd/range-of-markets/sp-500-index/)
- [Databento CME Globex MDP 3.0 dataset](https://databento.com/datasets/GLBX.MDP3)
- [Databento — CME history extended to 2010](https://databento.com/blog/CME-history-extended-to-2010)
- [Databento — CME Gold Futures (GC)](https://databento.com/datasets/GLBX.MDP3/futures/GC)
- [Kibot data packages and pricing](https://www.kibot.com/buy.html)
- [Kibot free historical intraday samples](https://www.kibot.com/free-historical-intraday-data.html)
- [FirstRate Data — Gold Futures (GC)](https://firstratedata.com/i/futures/GC)
- [FirstRate Data — GLD ETF](https://firstratedata.com/i/etf/GLD)
- [IBKR TWS API historical data limitations](https://interactivebrokers.github.io/tws-api/historical_limitations.html)
- [CME DataMine](https://www.cmegroup.com/datamine.html)
- [Where to get free or cheap historical futures data — QuantVPS](https://www.quantvps.com/blog/cme-historical-data-complete-guide)
- [Algo trading on futures prop firms: what's allowed in 2026](https://propfirmplus.com/algo-trading-on-futures-prop-firms-whats-actually-allowed-in-2026/)
- [Futures prop firms that allow automated trading (2026)](https://propfirmpinescripts.com/guides/prop-firms-that-allow-automated-trading.html)
- [Apex vs Topstep 2026 comparison](https://phidiaspropfirm.com/education/apex-vs-topstep)
- [Futures prop firm evaluation rules: drawdown, daily loss, consistency (2026)](https://godloveuniversity.com/futures-prop-firm-evaluation-rules/)
