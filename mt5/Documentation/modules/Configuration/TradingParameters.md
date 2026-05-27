# TradingParameters.mqh

## Purpose
Centralized input parameter hub for the entire EA. Every configurable value — from B2B detection thresholds to risk percentages and display fonts — is declared here as an MQL5 `input` variable. All other modules read from this file rather than declaring their own inputs. This single-file approach makes it impossible to scatter conflicting parameter declarations across the codebase.

## Layer
Configuration

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `ENUM_EXECUTION_PROFILE` | Enum | Predefined parameter bundles (e.g., `PROFILE_INTRADAY_M15`, `PROFILE_FULL_MANUAL`) |

## Parameter Groups

| Group | Contents |
|-------|----------|
| Strategy & Physics Kernel | Execution profile selector |
| General Settings | Magic number, slippage, historical bars to scan |
| B2B Detection | Window size, zone depth tolerance, min/max zone age |
| Trade Signal | Direction filters, entry trigger type (T1/T2/T3), zone touch requirements |
| Intraday Strategy | Session UTC hours, intraday mode toggle |
| Risk Engine | Risk % per trade, max concurrent positions, daily loss limit |
| Timeframe Control | Per-TF toggles: show zones, detect zones, allow trading |
| Display Settings | Font faces, font sizes, zone color palette, label visibility |

## Inputs / Outputs
- **Inputs:** None — this file IS the input declaration layer
- **Outputs:** Global `input` variables accessible by every module that `#include`s this file

## Dependencies
None — this is a root-level file with no includes.

## Python Equivalent
No direct equivalent. In sigma-crypto, parameters are passed via `DetectionConfig` dataclass (`sigma_core/sigma_core/b2b/models/structures.py`) and strategy config dicts in `core/strategy/orchestrator.py`. There is no single centralized input file; configs are injected at runtime.

## Notes
- Must be the **first** include in the main `.mq5` file — all other modules depend on it
- Execution profiles allow quick switching between pre-tuned parameter sets without manual editing
- Adding a new configurable value should always go here, never in a module-specific file
