# Quantum Audit V2 + Anchor TF Refactor

> **Date**: 2026-01-23  
> **Version**: V11.2  
> **Purpose**: Document all changes for future agent reference

---

## 1. What Was Changed

### A. New ENUM: `ENUM_VECTOR_ANCHOR` (Replaces `ENUM_VECTOR_MODE`)

**File**: `Common/Defines.mqh` (lines 79-92)

```cpp
enum ENUM_VECTOR_ANCHOR {
    ANCHOR_OFF         = 0, // No HTF Requirement
    ANCHOR_H1          = 1, // H1 Anchor Only
    ANCHOR_H1_H4       = 2, // H1 + H4 Must Align
    ANCHOR_H4          = 3, // H4 Anchor Only
    ANCHOR_H4_D1       = 4, // H4 + D1 (Swing)
    ANCHOR_D1          = 5, // D1 Only
    ANCHOR_D1_W1       = 6, // D1 + W1 (Long-Term)
    ANCHOR_FULL_STACK  = 7  // H1+H4+D1+W1
};
```

### A2. New ENUM: `ENUM_FRACTAL_ANCHOR` (Replaces `InpEnforceFractalAncestry` + `InpMinFractalDepth`)

**File**: `Common/Defines.mqh` (lines 94-108)

```cpp
enum ENUM_FRACTAL_ANCHOR {
    FRACTAL_OFF         = 0, // No parent required
    FRACTAL_ANY         = 1, // Must have ANY parent
    FRACTAL_H1          = 2, // Must nest inside H1 zone
    FRACTAL_H4          = 3, // Must nest inside H4 zone
    FRACTAL_H1_H4       = 4, // Must nest inside BOTH H1 and H4
    FRACTAL_D1          = 5, // Must nest inside D1 zone
    FRACTAL_H4_D1       = 6, // Must nest inside H4 AND D1
    FRACTAL_FULL_STACK  = 7  // Must nest inside H1+H4+D1
};
```

### B. New Input Parameters

**File**: `Configuration/TradingParameters.mqh` (lines 48-52)

| Parameter | Type | Default | Purpose |
|:----------|:-----|:--------|:--------|
| `InpMinFractalDepth` | int | 0 | Min "Russian Doll" score (0=any, 3=medium, 6+=strong) |
| `InpVectorAnchor` | enum | ANCHOR_OFF | Which HTF zones must align with trade direction |

### C. New Statistical Anchor Functions

**File**: `Analysis/MetricCalculator.mqh` (lines 177-330)

| Function | Returns | Description |
|:---------|:--------|:------------|
| `CalculateDailyPivotDistance()` | double (points) | Distance from yesterday's Pivot (P) |
| `CalculateStdDevBand()` | double (-3 to +3) | Which 20-period H1 StdDev band |
| `CalculateVolZScore()` | double | ATR Z-score vs 100-bar historical mean |
| `CalculateDailyOpenDistance()` | double (points) | Distance from today's open |

### D. New CSV Columns (Quantum Audit V2)

**File**: `Data/QuantTypes.mqh` (lines 88-105)

| Column | Type | Source |
|:-------|:-----|:-------|
| `is_shadow` | bool | `true` = harvest only, `false` = real trade |
| `base_risk_pct` | double | From `InpBaseRisk` |
| `touch_risk_pct` | double | Calculated per T1/T2/T3 |
| `leverage` | int | `AccountInfoInteger(ACCOUNT_LEVERAGE)` |
| `capital_at_entry` | double | `AccountInfoDouble(ACCOUNT_BALANCE)` |
| `trailing_sl_locked_pts` | double | Points locked by trailing stop |
| `be_activated` | bool | Break-even triggered? |
| `pivot_daily_dist` | double | From `MetricCalculator` |
| `std_dev_band` | double | From `MetricCalculator` |
| `vol_z_score` | double | From `MetricCalculator` |
| `daily_open_dist` | double | From `MetricCalculator` |

---

## 2. What Was Removed (Deprecated)

| Item | Was In | Reason |
|:-----|:-------|:-------|
| `ENUM_VECTOR_MODE` | `Defines.mqh` | Replaced by `ENUM_VECTOR_ANCHOR` |
| `InpVectorMode` | `TradingParameters.mqh` | Replaced by `InpVectorAnchor` |
| `InpMinVectorSum` | `TradingParameters.mqh` | No longer needed (Anchor TF is binary) |
| `InpSurvivalMinVectorSum` | `TradingParameters.mqh` | Vector filtering now at signal level |
| Old vector filter logic | `TradeSignalGenerator.mqh` | Replaced by Anchor TF switch-case |

---

## 3. Critical Bug Fixes

### Fractal Depth Write-Back

**File**: `Sigma_V5.0.mq5` → `UpdateGlobalConfluence()` (lines 1561-1563)

```cpp
// V11.1 FIX: God Data Metrics (was missing!)
original.fractal_depth_score = updated.fractal_depth_score;
original.tf_dominance_score = updated.tf_dominance_score;
original.cluster_density = updated.cluster_density;
```

**Problem**: Metrics were calculated but never written back to global arrays.  
**Result**: `fractal_depth` was always 0 in CSV.

---

## 4. Files Modified Summary

| File | Changes |
|:-----|:--------|
| `Common/Defines.mqh` | New `ENUM_VECTOR_ANCHOR` |
| `Configuration/TradingParameters.mqh` | New inputs, removed deprecated |
| `Trading/TradeSignalGenerator.mqh` | Anchor TF logic, fractal depth check |
| `Trading/OrderManager.mqh` | V2 field population, removed old ref |
| `Data/QuantTypes.mqh` | 12 new fields |
| `Data/QuantLogger.mqh` | Updated CSV header, DNA Card |
| `Analysis/MetricCalculator.mqh` | 4 new stat functions |
| `Sigma_V5.0.mq5` | Fractal write-back fix |

---

## 5. How to Use

### Anchor TF Examples:
- **Intraday (LTF + H1)**: `InpVectorAnchor = ANCHOR_H1`
- **Swing (LTF + H1+H4)**: `InpVectorAnchor = ANCHOR_H1_H4`
- **Position (LTF + D1)**: `InpVectorAnchor = ANCHOR_D1`
- **Raw Harvest**: `InpVectorAnchor = ANCHOR_OFF`

### Fractal Examples:
- **Any nesting**: `InpMinFractalDepth = 0`
- **Medium support**: `InpMinFractalDepth = 3`
- **Strong confluence**: `InpMinFractalDepth = 6`
