from state.trading_state import TradingState

def predict_micro_probabilities(state: TradingState) -> dict:
    """
    Node 3: Point72 Micro Layer (The Statistical AI Model).
    Reads the 'macro_regime' and raw price data. Applies ML classification 
    against known B2B deterministic setups to output a survivability probability.
    """
    print("-> MICRO ANALYZER: Predicting B2B Zone survivability...")
    
    regime = state.get("macro_regime", "UNKNOWN")
    
    # Mock ML Prediction Engine outputs
    probabilities = {}
    
    if "Inflation" in regime:
        # In this mocked regime, long EURUSD fails historically, short BTC wins
        probabilities["EURUSD_Long_Zone_1.08"] = 0.35  # 35% win probability
        probabilities["BTC_Short_Zone_71k"] = 0.68     # 68% win probability
    else:
        probabilities["EURUSD_Long_Zone_1.08"] = 0.65
        probabilities["BTC_Short_Zone_71k"] = 0.45
        
    state["micro_probabilities"] = probabilities
    return state
