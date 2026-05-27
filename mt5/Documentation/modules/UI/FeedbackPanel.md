# FeedbackPanel.mqh

## Purpose
The "B2B Command Centre" — an in-chart dashboard that displays real-time EA state without needing to open the MT5 journal or external tools. Shows account health, open zones per TF, active positions, and system status in a structured panel rendered directly on the chart. Designed for at-a-glance monitoring during live trading.

## Layer
UI

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `CFeedbackPanel` | Class | Full dashboard renderer |
| `Initialize(corner, font)` | Method | Setup panel position, font, and initial object creation |
| `Cleanup()` | Method | Remove all panel chart objects |
| `Update(account, zones[], positions[])` | Method | **Core (call periodically)**: Refresh all 6 panel sections with current data |
| `Show()` / `Hide()` | Methods | Toggle panel visibility |
| `Minimize()` / `Restore()` | Methods | Collapse panel to header-only / expand back |
| `OnChartEvent(id, lparam, dparam, sparam)` | Method | Handle click events (minimize button, etc.) |

## Panel Sections (6)

| # | Section | Contents |
|---|---------|----------|
| 1 | **Header** | EA name ("SIGMA V5.0"), status indicator, minimize button |
| 2 | **Account** | Account name, ID, broker name, account type, symbol, last update time |
| 3 | **Balance** | Equity, Balance, Margin %, P&L, Max Drawdown |
| 4 | **Timeline** | Per-TF SIGMA indicator row (active zones count, detection status) |
| 5 | **Zones** | Table: TF, Zone ID short form, Status (fresh/touched/used), Direction, 2nd Barrier price |
| 6 | **Positions** | Table: Ticket, Entry Price, SL, TP, Current P&L |

## Display Limits

| Section | Max Rows |
|---------|----------|
| Zones | 9 (one per TF) |
| Positions | 5 |

## Inputs / Outputs
- **`Update`**: Takes account snapshot, zones array, open positions array → redraws text objects in-place
- No return value

## Dependencies
- `Defines.mqh`, `Utils.mqh`, `Structures.mqh`, `TradingParameters.mqh`

## Python Equivalent
No equivalent — the sigma-quant Intelligence Centre (`syafiqmzin-sigma-quant.pages.dev`) is the web-based equivalent: real-time zone display, account status, and AI briefs. The MT5 panel is for in-platform monitoring; the web dashboard is for remote monitoring.

## Notes
- The panel is rendered using MT5's `OBJ_LABEL` chart objects — each data cell is a separate labelled object positioned with pixel offsets
- `Minimize()` hides all sections except the header row — useful when the panel obscures chart price action
- Colors, fonts, and panel position (top-left corner vs top-right) are configurable via `TradingParameters.mqh` display settings
- `Update()` should be called on a timer (e.g., every 1 second) not on every tick — refreshing 60 chart objects per tick is expensive and unnecessary
- The `MAX_ZONE_ROWS = 9` limit matches `TOTAL_TIMEFRAMES` — one row per TF in the worst case
