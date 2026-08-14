# MetricCalculator.mqh

## Purpose
Computes "God Data" metrics — advanced quantitative scores attached to each zone for AI pattern recognition and data science analysis. Currently implements Fractal Depth (V11.3), which scores how deeply nested a zone is within the HTF hierarchy. These scores are exported via `QuantLogger` to Supabase for ML feature engineering.

## Layer
Analysis

## Key Classes & Functions

| Name | Type | Description |
|------|------|-------------|
| `CMetricCalculator` | Class | All-static God Data metric calculator |
| `CalculateFractalDepth(zone, all_tf_zones[])` | Static | Counts how many HTF parent zones contain this zone. Returns score 0–4. Higher = more HTF confluence. |
| `GetTFRank(tf)` | Static | Helper: returns rank of a TF in the hierarchy (mirrors `CB2BConfluence::GetTFRank`) |

## Fractal Depth Scoring

| Score | Meaning |
|-------|---------|
| 0 | Zone has no HTF parent zones — isolated signal |
| 1 | Zone sits inside 1 HTF zone (e.g., D1) |
| 2 | Zone sits inside 2 HTF zones (e.g., D1 + H4) |
| 3 | Zone sits inside 3 HTF zones (e.g., W1 + D1 + H4) |
| 4 | Zone sits inside 4 HTF parent zones — maximum Russian Doll nesting |

HTF parents counted: H1, H4, D1, W1 (4 levels above M30 and below).

## Inputs / Outputs
- **`CalculateFractalDepth`**:
  - Input: the zone to score, plus the full cross-TF zone array for parent lookup
  - Output: int score 0–4
- Stored in `B2BZoneInfo.fractal_depth` field

## Dependencies
- `Structures.mqh`
- `Defines.mqh`

## Python Equivalent
Logic is implemented inline in `simulation/engine/vectorized_backtester.py` — fractal depth is computed as a post-processing step after zone detection. In the Python pipeline it is stored in the trade record DataFrame rather than on the zone object. No standalone `MetricCalculator` class exists in sigma-crypto.

## Notes
- "God Data" is Syafiq's internal name for the suite of advanced metrics designed to feed ML models — these are not used in real-time trading decisions, only in post-trade analysis
- V11.3 "repurposed" this field — it previously measured fractal geometry complexity; now it simply counts HTF parent zones, which proved more predictive in preliminary analysis
- Future metrics to add here (not yet implemented): `tf_dominance` (which TF drove the most zones in recent history), `cascade_score` (how quickly zone touch propagated across TFs)
