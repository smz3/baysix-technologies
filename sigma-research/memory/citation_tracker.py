"""
Citation tracking system for Baysix AI Hedge Fund.

Every data claim must carry a CitationRecord with source, URL, date, and confidence.
This is the foundation of the anti-hallucination protocol.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class CitationRecord(BaseModel):
    """A single verifiable claim linked to its data source."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    claim: str  # e.g., "DXY is at 103.2, ranging since Feb"
    source_name: str  # e.g., "FRED", "Yahoo Finance", "Binance API"
    source_url: str  # Direct URL to data
    retrieval_date: str = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    )
    data_date: str  # What date the data represents
    value: Any  # Actual data point
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    verified_by: list[str] = Field(default_factory=list)  # Agent names that verified

    def to_footnote(self) -> str:
        """Format as a report footnote."""
        return f"[{self.id}] {self.source_name} ({self.data_date}): {self.claim} — {self.source_url}"


class CitationStore:
    """In-memory citation store with optional JSON persistence."""

    def __init__(self, persist_path: Optional[Path] = None):
        self._citations: dict[str, CitationRecord] = {}
        self._persist_path = persist_path

    def add(self, citation: CitationRecord) -> str:
        """Add a citation and return its ID."""
        self._citations[citation.id] = citation
        return citation.id

    def get(self, citation_id: str) -> Optional[CitationRecord]:
        """Get a citation by ID."""
        return self._citations.get(citation_id)

    def get_by_source(self, source_name: str) -> list[CitationRecord]:
        """Get all citations from a specific source."""
        return [c for c in self._citations.values() if c.source_name == source_name]

    def get_by_claim(self, keyword: str) -> list[CitationRecord]:
        """Search citations by keyword in claim text."""
        keyword_lower = keyword.lower()
        return [
            c for c in self._citations.values() if keyword_lower in c.claim.lower()
        ]

    def verify(self, citation_id: str, agent_name: str) -> None:
        """Mark a citation as verified by an agent."""
        if citation_id in self._citations:
            if agent_name not in self._citations[citation_id].verified_by:
                self._citations[citation_id].verified_by.append(agent_name)

    def all(self) -> list[CitationRecord]:
        """Return all citations."""
        return list(self._citations.values())

    def to_markdown(self) -> str:
        """Format all citations as markdown footnotes for reports."""
        if not self._citations:
            return ""
        lines = ["## Sources\n"]
        for citation in self._citations.values():
            verified = (
                f" (verified by: {', '.join(citation.verified_by)})"
                if citation.verified_by
                else ""
            )
            lines.append(
                f"- **[{citation.id}]** {citation.source_name} ({citation.data_date}): "
                f"{citation.claim}{verified}\n  Source: {citation.source_url}"
            )
        return "\n".join(lines)

    def save(self, path: Optional[Path] = None) -> None:
        """Persist citations to JSON."""
        save_path = path or self._persist_path
        if save_path is None:
            return
        save_path.parent.mkdir(parents=True, exist_ok=True)
        data = [c.model_dump() for c in self._citations.values()]
        save_path.write_text(json.dumps(data, indent=2, default=str))

    def load(self, path: Optional[Path] = None) -> None:
        """Load citations from JSON."""
        load_path = path or self._persist_path
        if load_path is None or not load_path.exists():
            return
        data = json.loads(load_path.read_text())
        for item in data:
            citation = CitationRecord(**item)
            self._citations[citation.id] = citation

    def __len__(self) -> int:
        return len(self._citations)


# Convenience: create a citation from a data fetch
def cite(
    claim: str,
    source_name: str,
    source_url: str,
    data_date: str,
    value: Any,
    confidence: float = 1.0,
) -> CitationRecord:
    """Quick helper to create a CitationRecord."""
    return CitationRecord(
        claim=claim,
        source_name=source_name,
        source_url=source_url,
        data_date=data_date,
        value=value,
        confidence=confidence,
    )


if __name__ == "__main__":
    # Quick test
    store = CitationStore()

    c1 = cite(
        claim="DXY is at 104.2",
        source_name="FRED",
        source_url="https://fred.stlouisfed.org/series/DTWEXBGS",
        data_date="2026-03-25",
        value=104.2,
        confidence=1.0,
    )
    store.add(c1)

    c2 = cite(
        claim="VIX at 18.5, elevated but not panic",
        source_name="Yahoo Finance",
        source_url="https://finance.yahoo.com/quote/%5EVIX",
        data_date="2026-03-25",
        value=18.5,
        confidence=0.95,
    )
    store.add(c2)

    store.verify(c1.id, "macro-researcher")
    store.verify(c1.id, "mathematician")

    print(f"Citations stored: {len(store)}")
    print(store.to_markdown())
