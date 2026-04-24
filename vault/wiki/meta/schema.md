---
type: meta
status: stable
last_updated: 2026-04-14
maintained_by: human
ai_summary: "Frontmatter contract for all vault notes. Read before creating any wiki page."
---

# Vault Schema — Frontmatter Contract

Every file in `wiki/` must have a YAML frontmatter block. `raw/` uses a minimal version. `schema/` has none.

---

## Standard Wiki Page

```yaml
---
type: wiki                        # Always "wiki" for wiki/ pages
domain: strategy                  # strategy | systems | research | ai-agents | meta
status: stub                      # stub | draft | stable | deprecated
tags:
  - b2b                           # lowercase, hyphenated
related:
  - "[[page-name]]"               # Obsidian wikilinks (no path, just filename)
source_files:
  - "workspace/sigma-mt5/Documentation/B2B_DETECTION_SYSTEM.md"
last_updated: 2026-04-14          # ISO date, update on every meaningful change
maintained_by: ai                 # ai | human | both
ai_summary: "One sentence. Used in INDEX.md table. Must be self-contained — no 'this page covers...'"
---
```

### Status Definitions

| Status | Meaning |
|--------|---------|
| `stub` | Page exists but content is placeholder |
| `draft` | Substantial content, not yet reviewed or confirmed stable |
| `stable` | Content verified against source, cross-links confirmed |
| `deprecated` | Superseded — link to the replacement page in the body |

### ai_summary Rules

- Maximum 2 sentences
- Written as a fact, not a description ("B2B zones form when..." not "This page explains...")
- Must include enough specificity to distinguish this page from adjacent pages
- This is what any AI reads to decide if this page is relevant — make it count

---

## Raw Source Note

```yaml
---
type: raw
source_path: "workspace/sigma-mt5/Documentation/B2B_STRATEGY_DECISIONS.md"
ingested: 2026-04-14
spawned_wiki_pages:
  - "[[b2b-zone-lifecycle]]"
  - "[[b2b-invalidation]]"
do_not_edit: true
---
```

Raw notes are immutable source snapshots. Claude adds frontmatter during Ingest. Never edit the body after ingestion.

---

## Backtest Result (inside backtest-results.md)

Each test is a H3 block using Dataview inline fields:

```markdown
### Test 13A — OOS Alpha Sentinel (2024-2025)

test_id:: 13A
strategy:: SAMTC
phase:: OOS
instrument:: crypto
period:: 2024-2025
sharpe:: 1.16
calmar:: null
payoff:: 1.65
skew:: 3.43
status:: awaiting-production-approval
report_path:: workspace/sigma-crypto/research/reports/OOS/Test_13A/
```

---

## Hypothesis Entry (inside hypothesis-board.md)

```yaml
---
type: hypothesis
hypothesis_id: "HYP-001"
statement: ""
status: open                      # open | confirmed | rejected | inconclusive
p_value: null
evidence_for: []
evidence_against: []
spawned_from: "[[]]"
opened: 2026-04-14
closed: null
---
```

---

## Tag Taxonomy

| Tag | Use For |
|-----|---------|
| `b2b` | Anything about B2B zone detection strategy |
| `samtc` | SAMTC crypto strategy |
| `zone-detection` | Detection algorithms and logic |
| `timeframes` | TF hierarchy, multi-TF concepts |
| `execution` | Trade execution, order management |
| `risk` | Risk management, position sizing, invalidation |
| `backtesting` | Backtest methodology and results |
| `ml` | Machine learning, Kronos, feature engineering |
| `python` | Python-specific implementation |
| `mt5` | MT5/MQL5-specific implementation |
| `architecture` | System design, module relationships |
| `infra` | Infrastructure — APIs, databases, servers |
| `research` | Open questions, hypotheses |
| `core` | sigma_core, sealed components |
| `ip` | Intellectual property, sealed boundary |
| `wip` | Work in progress — check before referencing |

---

## Obsidian Callout Types (Use These)

```markdown
> [!SEALED]
> sigma_core content. Never include implementation details.

> [!CAUTION]
> Known edge case or bug. Reference the fix plan.

> [!DECISION]
> An agreed strategic decision. Should match B2B_STRATEGY_DECISIONS.md.

> [!RESEARCH]
> Open question. Should have a corresponding entry in hypothesis-board.md.

> [!DEPRECATED]
> Old approach replaced. Link to new page.
```
