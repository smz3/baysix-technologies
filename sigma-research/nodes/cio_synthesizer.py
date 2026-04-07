"""
Node 5: Chief Investment Officer.

Compresses the full pipeline state into the trading_context JSON payload.
Writes to:
  1. output/baysix_context.json  — local file for direct Python consumption
  2. Supabase trading_context    — IPC bus for MT5 EA and sigma-quant dashboard
"""

import json
import os
import time

from db.supabase_client import SupabaseClient
from state.trading_state import TradingState

_supabase = SupabaseClient()


def synthesize_final_context(state: TradingState) -> dict:
    print("-> CIO SYNTHESIZER: Compiling trading context JSON...")
    t0 = time.time()

    unix_now = int(time.time())
    regime = state.get("macro_regime", "UNKNOWN")

    payload = {
        "generated_at_unix": unix_now,
        "macro_regime": regime,
        "macro_confidence": state.get("macro_confidence", 0.0),
        "macro_narrative": state.get("macro_synthesis", ""),
        "macro_key_drivers": state.get("macro_key_drivers", []),
        "global_risk_multiplier": state.get("global_risk_multiplier", 1.0),
        "kill_switch": state.get("kill_switch", False),
        "risk_warnings": state.get("risk_warnings", []),
        "micro_probabilities": state.get("micro_probabilities", {}),
        "data_sources_used": state.get("data_sources_used", []),
    }

    json_str = json.dumps(payload, indent=2)
    state["trading_context_json"] = json_str
    state["generated_at_unix"] = unix_now

    # 1. Write local file
    os.makedirs("output", exist_ok=True)
    with open("output/baysix_context.json", "w") as f:
        f.write(json_str)

    # 2. Push to Supabase IPC bus
    elapsed_ms = int((time.time() - t0) * 1000)
    pushed = _supabase.upsert_trading_context(payload)
    _supabase.log_agent_run(
        agent_name="CIO_Synthesizer",
        status="SUCCESS",
        output_snippet=(
            f"Regime={regime} | "
            f"kill_switch={payload['kill_switch']} | "
            f"risk_mult={payload['global_risk_multiplier']}"
        ),
        run_duration_ms=elapsed_ms,
        regime=regime,
    )

    supabase_status = "pushed to Supabase" if pushed else "local-only (Supabase not configured)"
    print(
        f"** CIO Output: output/baysix_context.json | "
        f"{supabase_status} | {elapsed_ms}ms **"
    )
    return state
