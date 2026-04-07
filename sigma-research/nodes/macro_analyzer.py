"""
Node 2: Dalio Macro Layer.

Classifies macroeconomic regime from real market data using LLM reasoning.
Provider chain: Groq (fast) → Ollama (local fallback) → deterministic rules (final fallback).
"""

import json
import time
from pathlib import Path

from state.trading_state import TradingState

_PROMPT_PATH = Path(__file__).parent.parent / "llm" / "prompts" / "macro_prompt.txt"


def analyze_macro_regime(state: TradingState) -> dict:
    print("-> MACRO ANALYZER: Classifying regime with LLM...")
    t0 = time.time()

    raw = state.get("raw_data", {})
    system_prompt = _PROMPT_PATH.read_text(encoding="utf-8")
    user_prompt = f"Current market data:\n\n{json.dumps(raw, indent=2, default=str)}"

    result = _call_llm(system_prompt, user_prompt)
    elapsed_ms = int((time.time() - t0) * 1000)

    regime = result.get("regime", "UNKNOWN")
    confidence = float(result.get("confidence", 0.5))

    print(
        f"-> MACRO ANALYZER: Regime={regime} | "
        f"Confidence={confidence:.0%} | {elapsed_ms}ms"
    )

    state["macro_regime"] = regime
    state["macro_confidence"] = confidence
    state["macro_synthesis"] = result.get("narrative", "")
    state["macro_key_drivers"] = result.get("key_drivers", [])
    state["macro_risk_suggestion"] = float(result.get("risk_multiplier_suggestion", 1.0))
    return state


def _call_llm(system: str, user: str) -> dict:
    # 1. Try Groq (fast cloud inference)
    try:
        from llm.groq_client import GroqClient
        groq = GroqClient()
        if groq.is_available:
            return groq.structured_json(system=system, user=user)
        print("   [Groq] API key not configured — trying Ollama...")
    except Exception as e:
        print(f"   [Groq] Failed: {e} — trying Ollama...")

    # 2. Fallback: Ollama (local, no key required)
    try:
        from llm.ollama_client import OllamaClient
        ollama = OllamaClient()
        if ollama.is_available():
            raw = ollama.generate(prompt=user, system=system)
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(cleaned)
        print("   [Ollama] Not running — using deterministic fallback")
    except Exception as e:
        print(f"   [Ollama] Failed: {e} — using deterministic fallback")

    # 3. Final fallback: deterministic rule-based regime
    return _deterministic_fallback(user)


def _deterministic_fallback(user_prompt: str) -> dict:
    """Rule-based regime classification when no LLM is available."""
    regime = "Stable-Expansionary"
    risk_mult = 1.0

    try:
        data_str = user_prompt.split("Current market data:\n\n", 1)[1]
        data = json.loads(data_str)

        cpi = _get_nested(data, ["fred", "cpi_yoy", "value"])
        vix = _get_nested(data, ["yfinance", "vix", "price"])
        yield_spread = _get_nested(data, ["fred", "yield_spread_10y2y", "value"])

        if vix and vix > 30:
            regime = "Risk-Off"
            risk_mult = 0.5
        elif cpi and cpi > 3.5:
            if yield_spread and yield_spread < 0:
                regime = "Inflationary-Tightening"
                risk_mult = 0.75
            else:
                regime = "Inflationary-Tightening"
                risk_mult = 0.75
        elif vix and vix < 15:
            regime = "Risk-On"
            risk_mult = 1.25
    except Exception:
        pass

    return {
        "regime": regime,
        "confidence": 0.5,
        "narrative": (
            "Deterministic fallback active — LLM provider unavailable. "
            "Regime classified via rule-based logic from available market data."
        ),
        "key_drivers": ["LLM unavailable — rule-based classification"],
        "risk_multiplier_suggestion": risk_mult,
        "watch_list": ["Restore LLM connectivity (Groq or Ollama)"],
    }


def _get_nested(data: dict, keys: list) -> float | None:
    try:
        val = data
        for k in keys:
            val = val[k]
        return float(val)
    except (KeyError, TypeError, ValueError):
        return None
