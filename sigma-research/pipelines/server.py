"""
Sigma-Quant Intelligence Centre — Search API Server
====================================================
FastAPI service that exposes semantic search over the sigma_market Qdrant collection.

Usage:
    uvicorn pipelines.server:app --port 8080 --reload

Endpoints:
    GET  /health   — liveness + collection stats
    POST /search   — semantic search over embedded market documents
"""

import logging
import os
import sys

# ---------------------------------------------------------------------------
# Load .env before anything reads environment variables
# ---------------------------------------------------------------------------
from dotenv import load_dotenv, find_dotenv

_env_path = find_dotenv(filename=".env", raise_error_if_not_found=False, usecwd=True)
if not _env_path:
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
load_dotenv(_env_path, override=False)

# ---------------------------------------------------------------------------
# FastAPI app setup
# ---------------------------------------------------------------------------
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("server")

app = FastAPI(
    title="Sigma-Quant Search API",
    description="Semantic search over macro, crypto, equity, and news documents.",
    version="1.0.0",
)

# Allow requests from local dev frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# ---------------------------------------------------------------------------
# Lazy Qdrant client — initialised on first request
# ---------------------------------------------------------------------------
_qdrant_client = None
COLLECTION = "sigma_market"


def _get_qdrant():
    """Return the cached Qdrant client, or raise HTTPException 503 if unavailable."""
    global _qdrant_client
    if _qdrant_client is None:
        try:
            from pipelines.store.qdrant_store import get_client
            _qdrant_client = get_client()
            # Verify the connection is live
            _qdrant_client.get_collections()
        except Exception as e:
            _qdrant_client = None
            logger.error(f"Cannot connect to Qdrant: {e}")
            raise HTTPException(
                status_code=503,
                detail="Qdrant is not reachable. Ensure it is running and QDRANT_URL is set correctly.",
            )
    return _qdrant_client


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

_VALID_CATEGORIES = {"MACRO", "CRYPTO", "EQUITY", "NEWS"}


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Natural language search query")
    limit: int = Field(default=5, ge=1, le=50, description="Number of results to return")
    category: str | None = Field(default=None, description="Optional filter: MACRO | CRYPTO | EQUITY | NEWS")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        if v is not None and v.upper() not in _VALID_CATEGORIES:
            raise ValueError(f"category must be one of {sorted(_VALID_CATEGORIES)}")
        return v.upper() if v else v


class SearchResult(BaseModel):
    text: str
    source: str
    category: str
    date: str
    url: str
    score: float


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query: str
    count: int


class HealthResponse(BaseModel):
    status: str
    collection: str
    docs: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, summary="Liveness check + collection stats")
def health() -> HealthResponse:
    """
    Returns service status and current document count in sigma_market.
    Returns 503 if Qdrant is not reachable.
    """
    client = _get_qdrant()

    try:
        info = client.get_collection(COLLECTION)
        doc_count = info.points_count or 0
    except Exception:
        doc_count = 0

    return HealthResponse(
        status="ok",
        collection=COLLECTION,
        docs=doc_count,
    )


@app.post("/search", response_model=SearchResponse, summary="Semantic search over market documents")
def search(request: SearchRequest) -> SearchResponse:
    """
    Embeds the query using all-MiniLM-L6-v2 and performs approximate nearest-neighbour
    search against the sigma_market Qdrant collection.

    Optionally filter by category (MACRO | CRYPTO | EQUITY | NEWS).
    """
    client = _get_qdrant()

    # Embed the query
    try:
        from pipelines.embed.embedder import get_model
        model = get_model()
        query_vector = model.encode(request.query, convert_to_numpy=True).tolist()
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding error: {e}")

    # Build optional category filter
    query_filter = None
    if request.category:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="category",
                    match=MatchValue(value=request.category.upper()),
                )
            ]
        )

    # Hybrid search: semantic + macro/FRED keyword boosting
    try:
        # Pass 1: Semantic search across all documents
        response_all = client.query_points(
            collection_name=COLLECTION,
            query=query_vector,
            limit=request.limit * 2,  # Get more to account for dedup
            query_filter=query_filter,
            with_payload=True,
        )
        hits_all = response_all.points

        # Pass 2: Semantic search filtered to MACRO category (includes FRED data)
        # This ensures FRED data surfaces even if it's not in top semantic results
        macro_filter = None
        if not query_filter:  # Only add if no existing filter
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            macro_filter = Filter(
                must=[
                    FieldCondition(
                        key="category",
                        match=MatchValue(value="MACRO"),
                    )
                ]
            )

        hits_macro = []
        if macro_filter:
            response_macro = client.query_points(
                collection_name=COLLECTION,
                query=query_vector,
                limit=request.limit,
                query_filter=macro_filter,
                with_payload=True,
            )
            hits_macro = response_macro.points

        # Merge: dedupe and prioritize macro results
        seen_ids = set()
        merged_hits = []

        # Add macro results first (boosted)
        for hit in hits_macro:
            merged_hits.append(hit)
            seen_ids.add(hit.id)

        # Then add semantic results (avoiding dupes)
        for hit in hits_all:
            if hit.id not in seen_ids:
                merged_hits.append(hit)
                seen_ids.add(hit.id)
                if len(merged_hits) >= request.limit:
                    break

        hits = merged_hits[:request.limit]
    except Exception as e:
        logger.error(f"Qdrant search failed: {e}")
        raise HTTPException(status_code=503, detail="Search failed. Check server logs.")

    results = [
        SearchResult(
            text=hit.payload.get("text", ""),
            source=hit.payload.get("source", ""),
            category=hit.payload.get("category", ""),
            date=hit.payload.get("date", ""),
            url=hit.payload.get("url", ""),
            score=round(hit.score, 6),
        )
        for hit in hits
    ]

    return SearchResponse(
        results=results,
        query=request.query,
        count=len(results),
    )


# ---------------------------------------------------------------------------
# Dev entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("pipelines.server:app", host="0.0.0.0", port=8080, reload=True)
