---
name: 'vault-lint'
description: 'Sigma brain skill: vault-lint — check vault health and write report to health.md'
---

# Skill: vault-lint

Scan the vault for contradictions, orphan pages, broken links, stale content, and missing stubs. Write findings to `vault/wiki/meta/health.md`.

## Usage
```
/vault-lint
```

## Steps

1. **Load the page inventory**
   - Read `vault/wiki/meta/index.md` — this is the list of all expected pages
   - List all actual `.md` files under `vault/wiki/`
   - Compute: files in index but not on disk (MISSING), files on disk but not in index (ORPHAN)

2. **Check each existing page**
   
   For each wiki page file found on disk:
   
   a. **Frontmatter completeness** — does it have: type, status, tags, related, last_updated, maintained_by, ai_summary?
   
   b. **Link resolution** — for each `[[page-name]]` in the file, check if `vault/wiki/**/{page-name}.md` exists
   
   c. **ai_summary drift** — read the page body and compare to the ai_summary. Do they still match? Flag if they diverge significantly.
   
   d. **Stub inflation** — is `status: stub` but the page has substantive content (>200 words)? Suggest upgrading to draft or stable.
   
   e. **Staleness** — if `last_updated` is > 30 days ago AND the page has `source_files`, check if those source files exist and note they may have changed since

3. **Check for contradictions**
   
   Key contradiction pairs to check explicitly:
   
   | Pair | Contradicting claim |
   |------|---------------------|
   | b2b-invalidation + b2b-zone-lifecycle | Both must say: 1 close beyond L2 = INVALIDATED (not 2) |
   | b2b-invalidation + b2b-touch-depth | T3 = wick to L2 = VALID; close beyond L2 = INVALID |
   | b2b-timeframe-hierarchy + b2b-russian-doll | M15/M30 = CONTROL, not Sniper; Sniper = M5/M1 only |
   | samtc-overview + sigma-engine-map | sigma_core is sealed — source never in LLM context |
   | b2b-overview + mt5-ea-architecture | L1 selection: BUY = HIGHEST L1, SELL = LOWEST L1 |

4. **Write health.md**
   
   Overwrite `vault/wiki/meta/health.md` with:
   
   ```markdown
   # Vault Health Report
   Last lint: YYYY-MM-DD
   
   ## Summary
   | Check | Count | Status |
   ...
   
   ## Issues
   [CONTRADICTION] page-a vs page-b: description
   [ORPHAN] page-name: not linked from anywhere
   [MISSING] page-name: in index but not on disk
   [STALE] page-name: last_updated X days ago
   [BROKEN_LINK] page-a → [[page-b]]: page-b not found
   [STUB_INFLATE] page-name: status stub but >200 words
   
   ## Passed Checks
   ✅ No contradictions in [list]
   ✅ All links resolve in [list]
   ...
   ```

5. **Append to ingest log**
   ```
   YYYY-MM-DDTHH:MMZ | source: VAULT_LINT | wiki_pages_updated: health | [N issues found, M pages clean]
   ```

6. **Report summary to user**
   ```
   ## Lint Complete
   **Issues found**: N
   **Pages clean**: M
   **Critical (CONTRADICTION)**: [list or "none"]
   **Report**: vault/wiki/meta/health.md
   ```

## Rules
- Lint never modifies wiki content pages — only health.md
- Contradictions must be surfaced to Syafiq, not resolved autonomously
- The health.md report is always a full overwrite (not append) — it reflects current state
- Run lint after any major ingest session or before showing the vault to an external AI
