# UniversalSymbolManager.mqh

## Purpose
Makes the EA symbol-agnostic. Detects what kind of instrument is loaded (forex major, JPY pair, metal, crypto, index, energy) and derives the correct pip size, tick value, and lot constraints for that symbol. Without this, every lot size calculation would need hardcoded symbol-specific values.

## Layer
Common

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `ENUM_SYMBOL_TYPE` | Enum | `FOREX_MAJOR`, `JPY`, `EXOTIC`, `METAL`, `CRYPTO`, `INDEX`, `ENERGY`, `UNKNOWN` |
| `SymbolInfo` | Struct | Holds `pip_size`, `tick_value`, `min_lot`, `max_lot`, `lot_step` for current symbol |
| `Initialize(symbol)` | Method | Detect symbol type and populate `SymbolInfo` |
| `GetPipSize()` | Method | Returns instrument-correct pip size |
| `NormalizeLotSize(lots)` | Method | Rounds lot to broker's `lot_step`, clamps to min/max |
| `GetTickValue()` | Method | Returns tick value in account currency |

## Inputs / Outputs
- **`Initialize`**: Takes symbol name string; queries MT5 symbol info API
- **`NormalizeLotSize`**: Takes raw calculated lot, returns broker-compliant lot
- **`GetPipSize`**: Returns double (pip size varies: 0.0001 for majors, 0.01 for JPY, 0.1 for XAUUSD)

## Dependencies
- `TradingParameters.mqh`

## Python Equivalent
In sigma-crypto, symbol handling is abstracted in `core/risk/sizing.py` — the `RiskCalculator` receives pip size and tick value as parameters rather than auto-detecting them. No equivalent auto-detection class exists; sigma-crypto targets crypto pairs (Binance) where pip size is not a concern.

## Notes
- XAUUSD (the primary live trading instrument) is classified as `METAL` with pip size 0.1
- When adding a new market (futures, equity), this is the file to extend with the new `ENUM_SYMBOL_TYPE` and its pip/lot logic
- MT5 broker differences (e.g., 3-digit vs 5-digit brokers) are handled here, not in trading logic
