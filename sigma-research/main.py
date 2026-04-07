import time

from langgraph.graph import StateGraph, END

from state.trading_state import TradingState
from nodes.ingest_data import ingest_market_data
from nodes.macro_analyzer import analyze_macro_regime
from nodes.micro_analyzer import predict_micro_probabilities
from nodes.risk_manager import manage_risk
from nodes.cio_synthesizer import synthesize_final_context


def build_baysix_graph():
    """
    Constructs the Baysix Agentic System as a LangGraph StateGraph.

    Pipeline:
      Ingest → Macro (Dalio) → Micro (Point72) → Risk (PTJ) → CIO → Supabase
    """
    workflow = StateGraph(TradingState)

    workflow.add_node("Data_Ingestion",   ingest_market_data)
    workflow.add_node("Macro_Researcher", analyze_macro_regime)
    workflow.add_node("Micro_Researcher", predict_micro_probabilities)
    workflow.add_node("Risk_Manager",     manage_risk)
    workflow.add_node("CIO_Synthesizer",  synthesize_final_context)

    workflow.set_entry_point("Data_Ingestion")
    workflow.add_edge("Data_Ingestion",   "Macro_Researcher")
    workflow.add_edge("Macro_Researcher", "Micro_Researcher")
    workflow.add_edge("Micro_Researcher", "Risk_Manager")
    workflow.add_edge("Risk_Manager",     "CIO_Synthesizer")
    workflow.add_edge("CIO_Synthesizer",  END)

    return workflow.compile()


if __name__ == "__main__":
    print("=" * 60)
    print("Baysix LangGraph Orchestrator — Starting")
    print("=" * 60)

    app = build_baysix_graph()

    initial_state: TradingState = {
        "raw_data": {},
        "data_sources_used": [],
        "macro_regime": "UNKNOWN",
        "macro_confidence": 0.0,
        "macro_synthesis": "",
        "macro_key_drivers": [],
        "macro_risk_suggestion": 1.0,
        "micro_probabilities": {},
        "global_risk_multiplier": 1.0,
        "kill_switch": False,
        "risk_warnings": [],
        "trading_context_json": "",
        "generated_at_unix": int(time.time()),
    }

    print("\nExecuting pipeline...\n")
    t0 = time.time()

    try:
        result = app.invoke(initial_state)
        elapsed = round(time.time() - t0, 2)
        print(f"\n{'=' * 60}")
        print(f"Pipeline complete in {elapsed}s")
        print(f"Regime: {result.get('macro_regime')} ({result.get('macro_confidence', 0):.0%} confidence)")
        print(f"Risk Multiplier: {result.get('global_risk_multiplier')}x")
        print(f"Kill Switch: {result.get('kill_switch')}")
        print(f"Narrative: {result.get('macro_synthesis', '')[:200]}")
        print(f"{'=' * 60}")
    except Exception as e:
        print(f"\nPipeline failed: {e}")
        raise
