from state.trading_state import TradingState

def manage_risk(state: TradingState) -> dict:
    """
    Node 4: Paul Tudor Jones Risk Manager.
    Aggregates positional inputs, micro probabilities, and macro regime constraints.
    Computes a strict scalar multiplier (0.0 to 1.5) and controls the Kill Switch.
    """
    print("-> RISK MANAGER: Evaluating global exposure limits...")
    
    regime = state.get("macro_regime", "UNKNOWN")
    probs = state.get("micro_probabilities", {})
    
    multiplier = 1.0
    kill_switch = False
    warnings = []
    
    # E.g., if there's an aggressive macro shock, downsize everything.
    if "Tightening" in regime:
        multiplier = 0.5
        warnings.append("Defensive posture active: Tightening regime detected.")
        
    # If the highest probability setup is still lower than 50%, kill trading for the day
    best_prob = max(probs.values()) if probs else 0.0
    if best_prob < 0.40:
        kill_switch = True
        warnings.append("Kill Switch Engaged: No statistical edge found > 40%.")
        
    state["global_risk_multiplier"] = multiplier
    state["kill_switch"] = kill_switch
    state["risk_warnings"] = warnings
    return state
