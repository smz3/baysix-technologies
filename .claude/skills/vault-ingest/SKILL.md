---
name: 'vault-ingest'
description: 'Sigma brain skill: vault-ingest — update vault/wiki pages from a source document'
---

# Skill: vault-ingest

Update one or more `vault/wiki/` pages from a source document that has changed. Captures new decisions, backtest results, architecture changes, or strategy updates into the knowledge base.

## Usage
```
/vault-ingest [source file path or description of what changed]
```

## Steps

1. **Identify the source**
   - If a file path was given, read that file
   - If a description was given, identify which source file applies:
     - Strategy decisions → `workspace/sigma-mt5/Documentation/B2B_STRATEGY_DECISIONS.md`
     - Detection system → `workspace/sigma-mt5/Documentation/B2B_DETECTION_SYSTEM.md`
     - Cluster fix → `workspace/sigma-mt5/Documentation/B2B_CLUSTER_FIX_PLAN.md`
     - Backtest results → `Memory/strategy_state.md`
     - SAMTC logic → `workspace/sigma-crypto/core/strategy/orchestrator.py`

2. **Read `vault/wiki/meta/index.md`**
   - Identify which wiki page(s) the source content should update
   - Check `ai_summary` fields in those pages — are they still accurate?

3. **Read the target wiki page(s)**
   - Compare source content to current wiki content
   - Identify what has changed, been added, or been corrected

4. **Update the wiki page(s)**
   - Edit the relevant section(s) with new content
   - Update `last_updated` frontmatter to today's date (YYYY-MM-DD)
   - Update `ai_summary` if the page's core meaning changed
   - Add new `source_files` entry if a new source was used
   - Mark superseded content with ~~strikethrough~~ and a date rather than deleting

5. **Handle decisions specifically**
   - New locked decisions get `> [!DECISION]` callout blocks
   - Decisions that were REVERSED need the old callout marked ~~old~~ and a new one added with the reversal date
   - Never silently change a `[!DECISION]` block — flag it

6. **Append to ingest log**
   ```
   YYYY-MM-DDTHH:MMZ | source: [path] | wiki_pages_updated: [comma-separated pages] | [one-line summary]
   ```
   File: `vault/raw/ingest.log`

7. **Check index.md status**
   - If a stub page is now fully written → change status to `stable` or `draft`
   - If a new page was created → add it to the appropriate table in `index.md`

8. **Report back**
   ```
   ## Ingest Complete
   **Source**: [file]
   **Pages updated**: [list]
   **Changes**: [brief summary of what changed]
   **Open questions flagged**: [any decisions that still need Syafiq input]
   ```

## Rules
- Never delete wiki content — supersede with strikethrough + date
- Never silently change a `[!DECISION]` callout — flag to Syafiq
- `ai_summary` must be a single self-contained sentence that reads correctly out of context
- If a source contradicts an existing wiki decision, surface the contradiction to Syafiq rather than resolving it yourself
- Log every ingest — even minor ones
