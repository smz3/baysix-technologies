# QuantTypes.mqh

## Purpose
Defines the `QuantTradeExport` struct — a flat data record that matches the Supabase `trades` table schema column-for-column. When a trade closes, all relevant metadata is packed into this struct and written to CSV by `QuantLogger`. A separate Python loader then reads the CSV and pushes rows to Supabase for data science analysis.

## Layer
Data

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `QuantTradeExport` | Struct | Complete trade record for data export — 35+ fields covering trade metadata, entry/exit details, risk metrics, zone linkage, confluence scores, and session context |

## Field Groups — QuantTradeExport

| Group | Fields |
|-------|--------|
| Trade Identity | `ticket`, `symbol`, `direction` |
| Timing | `open_time`, `close_time`, `session`, `day_of_week`, `hour_of_day` |
| Entry/Exit | `entry_price`, `exit_price`, `exit_reason`, `lot_size` |
| Risk | `sl_price`, `tp_price`, `rr_planned`, `atr_at_entry` |
| Outcome | `pnl`, `commission`, `swap`, `edge_ratio` |
| Excursion | `mae` (max adverse excursion), `mfe` (max favorable excursion) |
| Zone Linkage | `zone_id`, `zone_tf`, `zone_age_bars`, `zone_touch_num` |
| Confluence | `cascade_score`, `vector_signature`, `d1_aligned` |
| God Data | `fractal_depth`, `tf_dominance` |

## Inputs / Outputs
- **Inputs:** None — pure data definition
- **Outputs:** `QuantTradeExport` struct type, used by `QuantLogger` and `OrderManager`

## Dependencies
None — standalone struct definition file.

## Python Equivalent
Maps directly to the Supabase `trades` table schema. In sigma-crypto, trade records are stored as Python dicts or dataclasses in `core/execution/trade_manager.py` and pushed to Supabase via `scripts/supabase_push.py`. The field names in this MQL5 struct are kept in sync with the Python push script's column mapping.

## Notes
- **Edge Ratio** = MFE ÷ MAE — a key metric for evaluating whether entries are structurally sound
- `vector_signature` is a bitmask encoding which timeframes contributed to the trade decision — useful for cluster analysis
- `fractal_depth` and `tf_dominance` are the "God Data" fields — designed for future ML feature engineering
- All fields use basic MQL5 types (string, double, int, datetime) so the CSV serialization in `QuantLogger` is straightforward
