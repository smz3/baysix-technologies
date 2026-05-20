# Moomoo / Webull — Execution Context

## What Is This

Retail brokers popular in the APAC region with Python API access.
Use case: APAC equities strategy deployment, particularly for the
Kenanga/Affin Hwang QR framing (Malaysia systematic shops).

## Moomoo vs Webull

| Feature | Moomoo | Webull |
|---------|--------|--------|
| API | Moomoo OpenAPI (Python) | Webull API (Python, limited) |
| Markets | US, HK, SG, AU, MY (expanding) | US, HK primarily |
| Fractional | Yes (US) | Yes (US) |
| Options | Yes | Yes |
| Malaysia access | Yes (Moomoo MY) | Limited |
| API quality | Better documented | More restricted |

## Why This Is Last Priority

- API capabilities are more limited than IKBR
- Primarily retail-grade execution (wider spreads, less liquidity)
- Better suited for APAC retail strategies, not institutional-grade alpha
- Only relevant if specifically targeting Malaysian equities (Kenanga framing)

## Connection Method

**Moomoo OpenAPI** (Python)
- `moomoo-openapi` Python package
- Real-time quotes, order placement, portfolio monitoring
- Requires Moomoo account and OpenAPI activation

**Webull API** (Python, community-maintained)
- Less official, more fragile
- Not recommended for production use

## Relevant Strategies

- Malaysian equities (Bursa Malaysia) — if building APAC adapter
- Singapore equities (SGX) — for APAC cross-sectional momentum
- HK equities — for regional stat arb

## Key Considerations

| Factor | Detail |
|--------|--------|
| Liquidity | Thin on Malaysian small-caps — model this in cost_registry |
| SC restrictions | Malaysian short selling limited to SC Approved Securities list |
| Stamp duty | 0.1% on Malaysian equity transactions (already in cost_registry: my_equity) |
| Data quality | APAC historical data harder to get than US — survivorship bias risk |
| API reliability | Less battle-tested than IBKR — monitor uptime |

## Build Dependencies

1. APAC equities adapter built in sigma-are (after US equities)
2. Survivorship-bias-free APAC price history sourced and stored in DuckDB
3. Factor model for APAC built (different factors than FF5 — use regional model)
4. Moomoo OpenAPI execution adapter built and paper-tested
5. Only build this if specifically targeting Malaysia firms in job search

## Status

FUTURE STATE. Low priority. Build after US equities and IKBR are operational.
