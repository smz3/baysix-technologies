# Session Handover — May 18, 2026 (Morning — B2B Focus Locked)

## Strategic Reframe This Session

**Key decision made:** The Context Engine, Regime Engine, and Data Engine described in
the architecture docs are **add-on layers, not prerequisites.** Build B2B signal quality
first. Add conditioners once the core signal has proven IC.

**The correct sequence:**
1. Does raw B2B (zone characteristics → forward returns) have IC? Measure it.
2. Does cheap regime conditioning (GEX binary) improve ICIR? Add it.
3. CE/RE/DuckDB are subsequent upgrades — they make the story richer, they don't create it.

**Tier C story target:**
> "I measured IC = X on B2B zone characteristics. Regime conditioning with GEX binary
> improved ICIR by Y%. IC decays over Z H1 bars. Here is the factor decomposition."

---

## Current System State

### What Is Deployed / Working
- MT5 EA (XAUUSD, B2B zones, Russian Doll confluence) — **not currently live trading**
- sigma-are: detectors exist (`core/detectors/b2b_engine.py`, `confluence.py`, etc.)
- B2B_STRATEGY_MASTER.md — single source of truth for B2B logic (written last session)
- ic_engine.py — **fully stubbed, nothing implemented**

### What Is Not Built
- `event_time` IC mode (DEC-008) — not even stubbed in ic_engine.py
- `adapters/gold/` — does not exist
- DuckDB data layer — not designed
- God Data analysis — fields are being captured by MT5 EA but never analysed

---

## B2B Brainstorm — The Core Question

> Which B2B zone characteristics predict forward trade outcome (win/loss, MFE, MAE)?

### God Data Fields Already Captured (per zone, per trade)
From MT5 EA QuantLogger CSV export:
```
fractal_depth       0–4 (nesting depth of zone in Russian Doll hierarchy)
is_nested           bool (zone sits inside a higher-TF parent)
is_multi_parent     bool (zone has ≥2 HTF parents)
is_pioneer          bool (first touch of price level — untested supply/demand)
touch_count         int (how many times price has revisited zone before entry)
zone_age_bars       int (bars since zone was created)
entry_level_used    T1 / 50% / T3 (where in the zone did we enter)
MAE                 float (max adverse excursion — how far against us before resolution)
MFE                 float (max favourable excursion — best the trade ever got)
rr_planned          float (planned reward/risk at entry)
pnl                 float (actual result)
exit_reason         str (TP / SL / manual / cascade)
```

### Research Questions for the Brainstorm
1. **Pioneer flag IC**: Do pioneer zones (first touch) win more than revisited zones?
2. **Fractal depth IC**: Does deeper nesting (higher fractal_depth) predict better MAE/MFE ratio?
3. **Touch count decay**: Does IC decay as touch_count increases? (zone gets used up)
4. **Entry level impact**: Is T1 entry materially different from 50% entry on forward IC?
5. **Zone age**: Do fresh zones (low zone_age_bars) outperform stale ones?
6. **GEX conditioning**: Does GEX binary (+1 range / -1 trend) improve IC of the above?
7. **Composite zone_score**: What linear combination of the above has highest ICIR?

### Minimum Viable Build to Start Measuring
1. Export MT5 CSV trade log (God Data fields above)
2. Load H1 XAUUSD bars (already in `data/raw/` as parquet — BTCUSDT, need gold)
3. Compute forward returns at H1 horizons: [1, 4, 8, 24, 48] bars after zone activation
4. Stub `event_time` IC mode in ic_engine.py
5. Run Spearman IC: each God Data field vs forward return — which fields have t-stat > 2?

No DuckDB needed yet. No HMM. No Kalman filter. Just CSV + parquet + Spearman.

---

## Open Issues (Do Not Block Brainstorm)

These are real but don't block the B2B signal research:

| Issue | File | Priority |
|-------|------|----------|
| sigma-are/CLAUDE.md stale — says sigma-crypto/Binance | sigma-are/CLAUDE.md | Low — fix later |
| ADR missing for Context Engine | Research/architecture/ | Low — needed before building CE |
| GEX dual-use undocumented (feeds CE + RE differently) | — | Low — document when building CE |
| Two HMM designs not demarcated (ARE equities vs Gold) | ADR-002 vs RE architecture doc | Medium — fix before building gold HMM |
| ic_engine.py fully stubbed | alpha_engine/core/ic_engine.py | HIGH — blocks all IC measurement |

---

## Session 0 Patches Still Needed (ARE)

These were the priority from the May 16 handover but haven't been done:

1. **ic_engine.py** — add `event_time` mode (Phase 1: sequential loop → timestamps, Phase 2+3: vectorized IC over event subset). IC decay horizons for gold: `[1, 4, 8, 24, 48]` H1 bars.
2. **base.py** — allow `load_data()` to return `dict[str, pd.DataFrame]` for multi-TF.
3. **hypothesis_log.md** — H001 (cross-sectional momentum) not yet logged.

---

## Architecture Docs Written (Reference — Not Active Build Targets Yet)

These are the future-state specs. Well-documented, internally consistent. Build in sequence:

| Doc | Status |
|-----|--------|
| Context Engine Architecture (Kalman→EWM→IC→PCA→L5) | Spec only — not building yet |
| Regime Engine Architecture (HMM+BOCPD→sizing→L5) | Spec only — not building yet |
| Signal + Execution Architecture (SAMTC→risk→execution) | Partially deployed in MT5 |
| sigma_gold_system.svg | Overview diagram |

---

## Priority for This Session

### 1. B2B Brainstorm (DO THIS FIRST)

Define the `zone_score` composite signal:
- Which God Data fields to use as features
- What the forward return label should be (H1 bars ahead, win/loss, MFE, MAE)
- What IC threshold counts as "edge worth measuring"
- Which GEX conditioning hypothesis to test first

### 2. Stub event_time mode in ic_engine.py

Get the measurement tool ready so the brainstorm can turn into code.

### 3. Source gold H1 data

Check: does `data/raw/` have XAUUSD bars? If not, pull from MT5 CSV export.
MT5 exports already have the God Data per trade. Need the OHLCV bars separately for
computing forward returns.

---

## Key Decisions Locked

| Decision | What | File |
|----------|------|------|
| DEC-008 | B2B IC mode = event_time. Sequential loop Phase 1, vectorized Phase 2+3 | decisions.md |
| DEC-005 WITHDRAWN | Cluster pairing not root cause. Wrong-direction trades were. | decisions.md |
| 3-Room Model | ARE = signal quality. LEAN = event simulator (mandatory). MT5 = production. | RESEARCH_FRAMEWORK.md |
| B2B First | CE/RE/Data Engine are add-on layers. Prove B2B IC first, layer sophistication after. | THIS HANDOVER |
