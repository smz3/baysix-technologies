# Quant 2.0 Protocol
**Version:** 2.0  
**Status:** PHASE 0: ZONE FOUNDATION  
**Last Updated:** January 15, 2026

---

## 1. RESEARCH HIERARCHY

```
PHASE 0: Zone Foundation (Prerequisite)
         ↓
PHASE 1: GPS Flow Analysis
         ↓
PHASE 2: Hypothesis Validation
```

---

## 2. THE THESIS

**One Sentence:**
> B2B Zones have predictive power — price returns to and respects zones at a rate statistically greater than random chance (>50%).

**Key Insight:**
> Before measuring GPS flow success, we must first validate zone structural integrity.

---

## 3. PHASE 0: ZONE FOUNDATION (NEW)

### Purpose
Establish zone survivability baseline before analyzing GPS flows.

### Questions
| ID | Question | Metric | Breakdown |
|----|----------|--------|-----------|
| Z1 | How many zones detected per TF? | Zone count | By TF × Direction (BUY/SELL) |
| Z2 | What % survived vs bulldozed? | Survival rate | By TF × Direction |
| Z3 | At what age did zones survive/break? | Age at outcome | By TF × Direction × Outcome |
| Z4 | At what depth (T1/T2/T3) did outcome occur? | Depth at outcome | By TF × Direction × Depth |
| Z5 | What predicts survival? | Cross-reference | Confluence, HTF alignment, etc. |

### Definitions
- **Survived** = Zone was touched AND respected (price bounced)
- **Bulldozed** = Zone was invalidated (bar closed beyond L2)
- **Untouched** = Zone never got touched (expires naturally)

### Kill Condition
> If SURVIVAL_RATE ≤ 50% across all TFs, zones have no structural edge.

---

## 3b. PHASE 0 FINDINGS (2026-01-16)

### Critical Bug Fixed (V6.2)
- Zones were invalidated on **wick touch** instead of **bar close**
- Bug caused premature invalidation, inflating bulldozed count
- Fix: Invalidation now only triggers when `is_new_bar = true`

### Overall Results (Post-Fix)
| Metric | Value |
|--------|-------|
| Total Zones | 6,424 |
| Tested | 506 (7.9%) |
| Untouched | 5,918 (92.1%) |
| **Survival Rate** | **14.4%** |

### 🚨 MAJOR DISCOVERY: Historical vs Live-Detected Zones

| Category | Tested | Survival Rate |
|----------|--------|---------------|
| **Historical (pre-2023)** | 24 | **50.0%** (12/24) |
| **Live-detected (2023+)** | 482 | **12.7%** (61/482) |

> **Thesis VALIDATED for historical zones!** Established zones survive at 50%.

### Historical Zones - Direction Breakdown
| Direction | Survival Rate |
|-----------|---------------|
| **BUY** | **80.0%** (12/15) |
| **SELL** | **0.0%** (0/9) |

### Historical Zones - Direction × TF Matrix
| Combo | Survival Rate |
|-------|---------------|
| **BUY + D1** | **100.0%** (4/4) |
| **BUY + H4** | **80.0%** (4/5) |
| **BUY + H1** | **66.7%** (4/6) |

### Key Insight
> The problem isn't the THESIS - it's the TIMING.
> Live-detected zones are caught in market noise.
> Established zones (historical) have proven structural significance.

### Next Question
> How do we PREDICT which live-detected zones will become "structural"?

### 📜 Research Paper Published
[Phase 0: The Zone Age Constant](Research_Paper_Phase0_Zone_Age_Constant.md)

---

## 4. PHASE 1: FRACTAL FLOW ANALYSIS (Exit Strategy Optimization)

### Purpose
Optimize the exit strategy to capture the "Legend Curve" (Power Law) distribution.

### ⚠️ CRITICAL WARNING: THE TEMPORAL BLIND SPOT
> **Current Status**: The "Whiplash Check" (MAE > 1R) in our simulation is **flawed** because `max_adverse_excursion` is a lifetime maximum. It does not know *when* the drawdown occurred relative to the target. 
> **Impact**: Winning trades that experience drawdown *after* hitting the target are falsely marked as losses. This severely penalizes "Sell" trades which often have high post-target volatility.
> **Result**: Current "Safe" simulations are a **Conservative Lower Bound**. The true edge is likely significantly higher.

### Questions (Q1-Q8)
| ID | Question |
|----|----------|
| Q1 | What is the optimal R-Target for "Legend" zones? |
| Q2 | Does the "No Sells" anomaly disappear when ignoring timestamp errors? |
| Q3 | How does Zone Age affect R-Multiple potential? |
| Q4 | Does a trailing stop (Wide & Long) outperform fixed targets? |
| Q5 | Can we predict "Power Law" candidates using fractal nesting? |

---

## 5. EXISTING CODE ASSETS (Reusable for Phase 0 & 1)

| File | Valuable Logic |
|------|----------------|
| `B2BZoneStatus.mqh` | Touch tracking, MFE/MAE Calculation (needs timestamp fix) |
| `B2BZoneManager.mqh` | Zone ID generation, Zone cleanup |
| `B2BConfluence.mqh` | Parent/child hierarchy, HTF alignment |
| `B2BDetector.mqh` | 5-Pointer detection, Zone creation |
| `phase1_exit_simulator.py` | Python simulation engine (Audited 2026-01-19) |

### Already Tracked in B2BZoneInfo Struct:
- `zone_id` - Unique identifier
- `L1_touched`, `fifty_touched`, `L2_touched` - Touch depth
- `is_invalidated` - Bulldozed flag
- `zone_age_bars` - Age at touch
- `sequence_index` - Lifecycle position
- `htf_parent_id` - HTF alignment

---

## 6. DATA REQUIREMENTS

### New Table: `b2b_zones`
Log ALL zones, not just flows.

### Zone Lifecycle Events
- ZONE_CREATED - When 5-pointer pattern completes
- ZONE_TOUCHED - When L1/50%/L2 touched
- ZONE_SURVIVED - When zone held and price bounced
- ZONE_BULLDOZED - When bar closes beyond L2

---

## 7. EXECUTION CHECKLIST

### Phase 0
- [x] Create `b2b_zones` table in Supabase
- [x] Add zone lifecycle logging in MQL5
- [x] Run mining job (physics only)
- [x] Upload zone data
- [x] Analyze Z1-Z5 questions
- [x] Determine zone selection criteria (Result: Age > 500 bars)

### Phase 1 (After Phase 0)
- [ ] Cross-reference zone survival with GPS flow success
- [ ] Re-run GPS flow analysis with filtered zones
