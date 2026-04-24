---
name: 'vault-query'
description: 'Sigma brain skill: vault-query — answer a strategy or architecture question from the vault'
---

# Skill: vault-query

Answer a question about B2B strategy, SAMTC, MT5 architecture, or research results using the vault as the source of truth. Always reads current wiki content — never relies on session memory alone.

## Usage
```
/vault-query [question]
```

## Steps

1. **Read `vault/wiki/meta/index.md`**
   - Find the Quick Reference table
   - Identify which page(s) answer the question
   - Note the status of those pages (stable = authoritative, draft = may be incomplete, stub = placeholder only)

2. **Read the relevant wiki page(s)**
   - Start with the primary page identified in step 1
   - Follow `related` links if the question spans multiple concepts

3. **Check for contradictions**
   - If two pages say different things about the same fact, do NOT guess which is correct
   - Report the contradiction and which pages it appears in
   - Suggest running `/vault-lint` to log it formally

4. **Formulate the answer**
   - Lead with the direct answer
   - Cite the page(s) used: `(Source: [[page-name]])`
   - If the page is a draft or stub, caveat: "This page is a draft — verify against source docs"
   - If the answer isn't in the vault, say so explicitly rather than guessing

5. **Report back**
   ```
   ## Query: [question]
   
   [Direct answer]
   
   **Source**: [[page-name]] — [section title]
   **Page status**: stable / draft / stub
   **Related**: [[page-a]], [[page-b]]
   ```

## Quick Reference Mapping

| Question category | Primary page |
|-------------------|-------------|
| What is a B2B zone? | [[b2b-overview]] |
| Zone lifecycle states | [[b2b-zone-lifecycle]] |
| Which TF does what | [[b2b-timeframe-hierarchy]] |
| Nesting / Russian Doll | [[b2b-russian-doll]] |
| Touch depth T0/T1/T2/T3 | [[b2b-touch-depth]] |
| Invalidation rules | [[b2b-invalidation]] |
| Open bugs / decisions | [[b2b-open-questions]] |
| How sigma_core, sigma-crypto, sigma-mt5 relate | [[sigma-engine-map]] |
| SAMTC strategy internals | [[samtc-overview]] |
| MT5 EA module breakdown | [[mt5-ea-architecture]] |
| Backtest results | [[backtest-results]] |
| How to use the vault | [[vault-operations]] |

## Rules
- Always read the current file — do not answer from memory alone
- Never assume a stub page has full content — check before citing
- Contradictions = surface, never resolve unilaterally
- If multiple pages conflict, cite both and flag to Syafiq
