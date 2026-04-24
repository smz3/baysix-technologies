# Vault Configuration

## Paths

| Resource | Path |
|----------|------|
| Vault root | `sigma-brain/vault/` |
| MT5 module docs | `sigma-brain/workspace/sigma-mt5/Documentation/modules/` |
| MT5 strategy docs | `sigma-brain/workspace/sigma-mt5/Documentation/` |
| sigma-crypto | `sigma-brain/workspace/sigma-crypto/` |
| sigma_core (SEALED) | `sigma-brain/workspace/sigma_core/` |
| Session memory | `sigma-brain/Memory/` |
| Braindump | `sigma-brain/Braindump/` |

## AI Stack

| Model | Endpoint | Use |
|-------|----------|-----|
| Gemma 4 31B | `ollama run gemma4-baysix` | Content drafting for Ingest ops |
| Gemma 4 8B | `ollama run gemma4:latest` | Quick classification only |
| Claude Sonnet 4.6 | Claude Code CLI | Orchestration, file writes, vault ops |

## External Services

| Service | Purpose | Collection/DB |
|---------|---------|---------------|
| Qdrant Cloud | Vector search (future) | `sigma_market` (245 docs), `sigma_vault` (TBD) |
| Supabase | Trade + zone data | `sigma_trades`, `sigma_zones` tables |
| Groq (Llama 3.3 70B) | AI market briefs | Via sigma-research FastAPI |

## Vault Operations

| Operation | Skill | Frequency |
|-----------|-------|-----------|
| Ingest | `/vault-ingest [path]` | On demand |
| Query | `/vault-query [question]` | On demand |
| Lint | `/vault-lint` | Weekly |

## Qdrant Indexing Policy

Not active until vault exceeds 400K words. Current estimated size at full buildout: ~80K words.
When enabled: index `wiki/` pages only. Each page = 1 document. Payload = frontmatter fields.
Embedding source = `ai_summary` + first 500 words of page body.
New collection: `sigma_vault`.

## Sealed Boundary

`sigma_core` is compiled IP. Never include its source code, internal function names, or implementation details in any vault page. Reference it only by capability ("sealed B2B detection engine, compiled .pyd").
See `wiki/strategy/sigma-engine-map.md` for the boundary definition.
