from typing import Any, Dict, List

from typing_extensions import TypedDict


class TradingState(TypedDict):
    """Shared state dictionary for the Baysix LangGraph Swarm."""

    # Node 1 — Data Ingestion
    raw_data: Dict[str, Any]
    data_sources_used: List[str]

    # Node 2 — Macro Researcher (Dalio Layer)
    macro_regime: str
    macro_confidence: float
    macro_synthesis: str
    macro_key_drivers: List[str]
    macro_risk_suggestion: float

    # Node 3 — Micro Researcher (Point72 Layer)
    micro_probabilities: Dict[str, float]

    # Node 4 — Risk Manager (PTJ Layer)
    global_risk_multiplier: float
    kill_switch: bool
    risk_warnings: List[str]

    # Node 5 — CIO Output
    trading_context_json: str
    generated_at_unix: int
