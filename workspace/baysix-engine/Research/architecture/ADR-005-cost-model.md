# ADR-005: Transaction Cost Model

**Date:** 2026-05-13  
**Status:** Active  
**Component:** `adapters/*/costs.py`

---

## Decision

**Full cost model — all components required. No partial implementation.**

```
Total cost per round-trip trade =
    bid-ask spread
  + market impact (Almgren square-root)
  + borrow cost (short-side positions)
  + stamp duty / transaction tax (market-specific)
  + financing cost (leveraged positions only)
  + implementation shortfall estimate

Net IC = Gross IC − (total_cost_bps × annual_turnover_pct / 10000)
```

**Default cost parameters by market:**

| Component                 | US ETFs    | ASEAN ETFs  | Bursa Malaysia stocks |
|-----------                |---------   |------------ |----------------------|
| Bid-ask spread            | 2 bps      | 8 bps       | 15 bps               |
| Market impact             | Almgren √(participation_rate) | Almgren √(participation_rate) | Almgren — higher λ   |
| Borrow cost               | 0.3%/yr    | 0.5%/yr     | 1.0%/yr              |
| Stamp duty                | 0% (ETFs exempt) | 0% (ETFs)   | 0.1% per trade       |
| Financing (leveraged)     | SOFR + 150 bps | Regional rate + 200 bps | OPR + 200 bps |
| Implementation shortfall  | 50% of spread | 50% of spread | 75% of spread |

**Market impact (Almgren-Chriss):**
```
impact_bps = λ × σ_daily × √(trade_size / ADV)
λ = 0.1 (liquid ETFs) to 0.3 (less liquid)
```

**Malaysia-specific rule (hard-coded warning):**  
Bursa stamp duty = 0.1% per trade = 0.2% round-trip. Any signal on Bursa stocks with holding period < 10 days must generate > 0.2% gross return per trade to be economically viable. Engine raises a warning automatically when net IC turns negative due to stamp duty.

---

## Why

**Almgren square-root impact:**
Market impact grows sub-linearly with trade size — doubling the trade size does not double the impact. The square-root relationship is empirically verified across markets and is the theoretical result of Almgren & Chriss (2001) optimal execution model. It is the academic and practitioner standard for pre-trade impact estimation.

**Full cost model (not just spread):**
Partial cost models are worse than no cost model — they give false confidence. A signal that looks profitable after 5 bps spread may be deeply unprofitable after borrow costs, stamp duty, and implementation shortfall. All components must be included, even if estimated.

**Borrow cost:**
Short-side of any long-short signal incurs borrow fees. For liquid US ETFs this is 0.3%/yr. For less liquid ASEAN ETFs or Bursa stocks, borrow can exceed 1%/yr and is sometimes unavailable entirely. If borrow is unavailable, the short side cannot be executed — the signal effectively becomes long-only, which changes its IC profile materially.

**Stamp duty:**
Most backtests ignore transaction taxes. For Malaysia, the 0.1% Bursa stamp duty is real capital destruction on every round-trip. A VWAP mean-reversion signal that looks excellent on paper (IC = 0.04, ICIR = 1.2) has its net IC destroyed if it rebalances daily — stamp duty alone exceeds gross alpha at high turnover.

**Implementation shortfall:**
The difference between the paper signal's entry price and the actual executed price. Every backtest fills at the close price. In reality you execute after the signal fires and move the market. 50% of spread is a conservative estimate for liquid ETFs. This widens for less liquid markets.

---

## Alternatives Considered

| Alternative | Description | Why not chosen |
|-------------|-------------|----------------|
| **Linear impact model** | Impact ∝ size/ADV linearly | Simpler but overestimates impact for small trades, underestimates for large. Square-root is empirically correct |
| **Kyle Lambda model** | Theoretical impact from informed trading — requires tick data | Most theoretically grounded but requires tick-level order book data not available via yfinance |
| **Amihud illiquidity ratio** | \|return\| / dollar_volume — proxy for market impact | Useful proxy when tick data is unavailable. Use as a cross-check against Almgren, not instead of it |
| **Grinold-Kahn (BARRA) cost model** | Institutional standard, part of BARRA risk model | Requires BARRA subscription. Consistent with the BARRA factor model — defer alongside BARRA upgrade (ADR-001 Upgrade 3) |
| **Spread only (no impact)** | Just charge half-spread per trade | Never sufficient. Misses all other cost components. Only valid for positions < 0.1% of ADV |
| **Empirical impact (from live fills)** | Measure actual implementation shortfall from live execution data | Most accurate. Trigger: 6+ months of live execution data available |
| **VWAP cost model** | Cost relative to VWAP benchmark | Appropriate for VWAP execution algorithms. Relevant post-deployment when we know our execution algo |

---

## Registry Architecture (Implemented 2026-05-14)

All cost parameters live in one file: `alpha_engine/core/cost_registry.py`.
No adapter hardcodes cost numbers — every `adapters/*/costs.py` imports from the registry.

### Structure

```python
COST_REGISTRY: dict[str, CostProfile]   # 8 asset class profiles
INVESTOR_PROFILES: dict[str, InvestorProfile]  # 2 investor types
```

### 8 Asset Classes

| Key | Description | WHT | Short restricted |
|-----|-------------|-----|-----------------|
| `us_etf` | US-domiciled SPDR ETFs | 30% (MY individual) | No |
| `europe_etf` | Ireland-domiciled ETFs (CSPX, IWDA) | 0% (structural advantage) | No |
| `asia_etf` | US-domiciled ASEAN ETFs (EWM, EWJ…) | 30% (US-domiciled) | No |
| `my_equity` | Bursa Malaysia equities | 0% (single-tier) | **Yes — SC list** |
| `us_equity` | US individual equities | 30% (MY individual) | No |
| `futures` | CME futures (ES, NQ, GC, CL) | 0% | No |
| `spot_fx` | Spot FX — G10 and EM pairs | 0% | No |
| `cfd_gold` | CFD XAUUSD — live MT5 product | 0% | No |

### 2 Investor Profiles

| Key | Context | WHT | Commission |
|-----|---------|-----|-----------|
| `individual_my` | Malaysian individual, IBKR | 30% on US dividends | Asset class default |
| `institutional_my` | Kenanga / Affin Hwang | 0% (fund-level) | 8 bps override |

### How adapters use the registry

```python
# adapters/equities/costs.py
from alpha_engine.core.cost_registry import (
    COST_REGISTRY, INVESTOR_PROFILES, net_ic_after_costs
)

profile  = COST_REGISTRY['us_etf']
investor = INVESTOR_PROFILES['individual_my']
result   = net_ic_after_costs(gross_ic=0.05, profile=profile, investor=investor,
                               annual_turnover_pct=100, dividend_yield_annual=0.018)
# result['passes_gate'] is the Layer 4 gate — must be True
```

### New cost components added (vs original ADR)

Three components missing from the original cost table are now in the registry:

| Component | Where it matters most | How captured |
|-----------|----------------------|--------------|
| **Dividend WHT** | US ETFs for MY individual (30% × yield) | `dividend_withholding_rate` + `investor.applies_dividend_wht` |
| **Broker commission** | All asset classes | `commission_bps` (overridable per investor) |
| **FX conversion** | Cross-currency positions | `fx_conversion_bps` + `investor.applies_fx_conversion` |
| **Overnight financing** | CFD gold (3-5%/yr), spot FX carry | `overnight_financing_annual` |

---

## Deferred Upgrades

### Upgrade 1: Static defaults → Dynamic spread estimation

**What it is:** Instead of fixed 5 bps for US ETFs, estimate bid-ask spread from daily OHLCV using Roll (1984) spread estimator: `spread = 2 × √(-cov(ΔP_t, ΔP_{t-1}))`.

**Trigger condition:** Spread assumption is found to be consistently wrong vs observed spreads. Also trigger when ASEAN ETF universe expands to less liquid names where 8 bps default underestimates true spread.

### Upgrade 2: Almgren → Full Implementation Shortfall (IS) Model

**What it is:** IS model decomposes total execution cost into: delay cost (signal fires, you wait to execute) + market impact (you move the price) + timing risk (price moves against you while executing) + commission.

**Trigger condition:** Live execution data is available (6+ months). IS model requires empirical calibration from actual fills.

### Upgrade 3: Estimated borrow → Live borrow rate feed

**Trigger condition:** Short-selling is material to the portfolio. Connect to Interactive Brokers or similar API to get live stock borrow availability and rate before computing net IC on any short-side signal.

### Upgrade 4: Static CostProfile defaults → Per-ticker parameter overrides

**What it is:** `COST_REGISTRY` stores asset-class-level defaults. Individual tickers deviate: XLU spread differs from XLK spread, hard-to-borrow small caps have 5%+ borrow. Add a `override` layer on top of the registry per ticker.

**Trigger condition:** Universe expands beyond the 17 ETFs (>50 names) where per-ticker spread and borrow heterogeneity materially affects net IC rank ordering across the cross-section.

---

## Turnover-Cost Interaction

The cost model is incomplete without turnover. High gross IC with high turnover is often worse than lower gross IC with low turnover:

```python
# In costs.py
def net_ic_after_costs(gross_ic, annual_turnover_pct, cost_per_trade_bps):
    """
    annual_turnover_pct: % of portfolio turned over per year (e.g., 200% = 2× per year)
    cost_per_trade_bps: full round-trip cost including all components
    """
    annual_cost_drag = (annual_turnover_pct / 100) * (cost_per_trade_bps / 10000)
    # Convert gross IC (dimensionless) to approximate return via IC × vol
    # Then subtract cost drag
    return gross_ic - annual_cost_drag  # simplified — full version adjusts for vol scaling
```

Signals must be evaluated on NET IC after this adjustment. A signal with IC = 0.08 and 500% annual turnover may have lower net IC than a signal with IC = 0.04 and 50% turnover.

---

## Interview Defence

> "We run a full cost model across eight asset classes — spread, Almgren square-root market impact, broker commission, borrow costs on the short side, stamp duty, clearing fees, overnight financing, dividend withholding tax, and implementation shortfall. Every parameter lives in a central cost registry so we can switch from US ETFs to Bursa Malaysia equities to CFD gold with one argument change. For a Malaysian individual investor running US ETFs, the 30% dividend withholding tax adds 18-90 bps/yr drag depending on the ETF's yield — most backtests ignore this entirely. For Bursa Malaysia stocks, the 0.1% stamp duty is 0.2% round-trip — any short-horizon signal must generate more than 0.2% gross alpha per trade just to break even on transaction tax. The engine flags both automatically. The Layer 4 gate is binary: net IC after the full cost model must be positive, or the signal does not advance."
