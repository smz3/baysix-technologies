# sigma-research — Research Infrastructure

## What This Project Does

sigma-research is the Python research engine for Baysix AI Hedge Fund. It provides:
- **Data pipelines** — fetch macro, micro, and cross-asset market data from free APIs
- **Vector memory** — Qdrant-based semantic search over all research and citations
- **Local LLM integration** — Ollama (qwen2.5:7b, mistral:7b) for sentiment, summarization, verification
- **Analysis modules** — Dalio (macro regime), Point72 (instrument selection), PTJ (risk management)
- **Citation tracking** — every data claim carries a CitationRecord with source, date, and confidence
- **Report generation** — Jinja2 + WeasyPrint PDF reports
- **B2B Zone Detection** — shared, instrument-agnostic strategy engine

## How Agents Use This

sigma-brain agents (macro-researcher, micro-researcher, etc.) invoke scripts in this project:
```bash
# Activate venv first
source .venv/Scripts/activate  # or .venv\Scripts\activate on Windows

# Data fetching
python data/pipelines/fred_fetcher.py
python data/pipelines/yahoo_finance.py
python data/pipelines/crypto_data.py

# Analysis (future)
python scripts/daily_macro_brief.py
python scripts/research_pipeline.py

# Tests
pytest tests/
```

## Conventions

- **Config**: YAML files in `config/` — no hardcoded values
- **Data storage**: Parquet files in `data/raw/` and `data/processed/`
- **Secrets**: `.env` file (never committed), loaded via `python-dotenv`
- **Schemas**: Pydantic models for all structured data
- **Caching**: `requests-cache` to avoid duplicate API calls
- **Logging**: Print-based for now (structured logging later)
- **Testing**: Pytest in `tests/`

## Key Environment Variables

```
FRED_API_KEY=your_key_here
```

## Infrastructure Dependencies

- **Qdrant**: localhost:6333 (local binary)
- **Ollama**: localhost:11434 (local, GPU-accelerated)
- Both are optional — code gracefully handles when services are unavailable
