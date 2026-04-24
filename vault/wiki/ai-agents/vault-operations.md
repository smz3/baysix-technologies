---
type: wiki
domain: ai-agents
status: stable
tags:
  - vault
  - meta
  - agents
related:
  - "[[index]]"
  - "[[schema]]"
  - "[[agent-roster]]"
source_files: []
last_updated: 2026-04-14
maintained_by: ai
ai_summary: "The vault has three operations: Ingest (source docs → wiki pages), Query (AI reads vault to answer questions), and Lint (detect contradictions, orphans, stale pages). Index.md is the entry point for every session."
---

# Vault Operations

> This page explains how to use the sigma-brain vault as an AI knowledge system. Read this before orchestrating any multi-agent vault task.

---

## The Three Operations

```
┌─────────────────────────────────────────────────────────────────┐
│  INGEST   ─── Source doc → vault/wiki/ pages                    │
│  "A source of truth changed. Update the vault."                  │
├─────────────────────────────────────────────────────────────────┤
│  QUERY    ─── vault/wiki/ → answer a question                    │
│  "What does the vault know about X?"                             │
├─────────────────────────────────────────────────────────────────┤
│  LINT     ─── vault/wiki/ → health report                        │
│  "Are there contradictions, orphans, or stale pages?"            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. INGEST — `/vault-ingest`

### When to run
- A source document has changed (e.g., `B2B_STRATEGY_DECISIONS.md` was updated)
- A new decision was made and needs to be captured in the wiki
- A backtest completed and results need to be recorded
- A new .mqh module was created and needs a doc entry

### What it does
1. AI reads the source document (from `workspace/sigma-mt5/Documentation/` or `Memory/`)
2. AI identifies which wiki page(s) are affected
3. AI updates the wiki page(s) with new information
4. AI appends an entry to `vault/raw/ingest.log`
5. AI checks if `wiki/meta/index.md` needs updating (new page counts, etc.)

### Ingest log format
```
vault/raw/ingest.log — append only, never edit past entries

YYYY-MM-DD | SOURCE_FILE | Pages updated | Summary
```

### Rules
- **Never delete wiki content without a reason** — superseded info gets a strikethrough and a date, not deletion
- **ai_summary frontmatter must update** when page content changes significantly — this is what feeds index.md
- **Source files frontmatter** must list every source doc the page was built from
- The `[!DECISION]` callout marks locked decisions — do not silently change these, flag to Syafiq first

---

## 2. QUERY — `/vault-query`

### When to run
Any time an AI session needs to answer a strategy question, understand architecture, or prepare context for a task.

### Standard query flow
```
1. Read vault/wiki/meta/index.md       ← START HERE EVERY TIME
2. Identify which page(s) answer the question
3. Read those pages (and their [[related]] links if needed)
4. Answer the question — cite the page name and relevant section
```

### index.md is the contract
Every session starts with `vault/wiki/meta/index.md`. The Quick Reference table maps question categories to specific wiki pages. Use it — do not randomly grep the vault.

### Query rules
- **Do not trust memory** — always read the current wiki page, not a recalled summary
- **Check ai_summary first** — if the one-sentence summary answers the question, you may not need the full page
- **Follow [[related]] links** — wiki pages are designed to cross-reference. A question about invalidation likely needs both `b2b-invalidation` and `b2b-zone-lifecycle`
- **Escalate contradictions** — if two pages say different things, report it as a lint issue rather than guessing

---

## 3. LINT — `/vault-lint`

### When to run
- Before a major session (check vault health first)
- After a large ingest (did the update create new orphans?)
- Monthly maintenance (catch drift between source docs and wiki)

### What it checks

| Check | Description |
|-------|-------------|
| **Contradictions** | Two pages that say different things about the same fact |
| **Orphans** | Wiki pages with no `[[related]]` links pointing to them — unreachable |
| **Stale pages** | `last_updated` > 30 days old AND a source file has changed since |
| **Missing stubs** | Pages listed in index.md that don't exist on disk |
| **Broken links** | `[[page-name]]` links to a page that doesn't exist |
| **Empty stubs** | Pages with `status: stub` that have no substantive content |
| **ai_summary drift** | Page content changed but ai_summary wasn't updated |

### Output format
Lint writes its findings to `vault/wiki/meta/health.md`. Each issue is tagged:
- `[CONTRADICTION]` — must resolve before next ingest
- `[ORPHAN]` — low priority, fix by adding a related link somewhere
- `[STALE]` — medium priority, schedule ingest
- `[MISSING]` — create the page or remove the reference
- `[OK]` — passing check

---

## Vault File Layout Reference

```
sigma-brain/vault/
├── raw/
│   └── ingest.log          ← append-only record of all ingests
├── schema/
│   ├── vault-config.md     ← paths, AI stack, sealed boundary
│   └── templates/
│       ├── wiki-page.md    ← standard wiki page template
│       ├── backtest-result.md ← backtest note template
│       └── hypothesis.md   ← hypothesis board entry template
└── wiki/
    ├── meta/
    │   ├── index.md        ← START HERE — master content catalog
    │   ├── schema.md       ← frontmatter contract
    │   └── health.md       ← latest lint report
    ├── strategy/           ← B2B and SAMTC knowledge
    ├── systems/            ← Technical architecture
    ├── research/           ← Backtest results, hypotheses
    └── ai-agents/          ← This folder — AI usage docs
```

---

## Skills Reference

| Skill | Trigger | What it does |
|-------|---------|--------------|
| `/vault-ingest` | Source doc changed | Reads source, updates wiki page(s), logs to ingest.log |
| `/vault-query` | Strategy question | Reads index.md → relevant pages → answers with citations |
| `/vault-lint` | Maintenance | Checks vault health, writes report to health.md |
| `/handover` | End of session | Updates Memory/ files with session state |
| `/update-memory` | Memory update needed | Updates Memory/ operational state (NOT the vault) |

> [!NOTE]
> Memory/ and vault/ serve different purposes:
> - **Memory/** = RAM — session-to-session operational state (what's in progress, current blockers)
> - **vault/wiki/** = Disk — durable knowledge base (strategy rules, architecture, backtest results)
>
> The `/update-memory` skill updates Memory/. The `/vault-ingest` skill updates vault/wiki/.
> Do not mix them — they have different retention expectations.

---

## AI Session Checklist

When starting a session involving vault content:

1. **Read `vault/wiki/meta/index.md`** — understand what pages exist and their status
2. **Check `vault/wiki/meta/health.md`** — any open contradictions or missing pages?
3. **Read only the pages relevant to your task** — don't load the whole vault
4. **After making strategy decisions:** run `/vault-ingest` to capture them
5. **End of session:** run `/handover` to update Memory/

---

## Related Pages

- [[index]] — Master content catalog (start here for any query)
- [[schema]] — Frontmatter contract for wiki pages
- [[health]] — Latest lint report
- [[agent-roster]] — Which agents do what in multi-agent sessions
