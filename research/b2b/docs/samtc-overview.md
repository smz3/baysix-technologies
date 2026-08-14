---
type: wiki
domain: strategy
status: archived
tags:
  - samtc
  - crypto
  - python
  - strategy
related:
  - "[[b2b-overview]]"
  - "[[mt5-ea-architecture]]"
source_files:
  - "sigma-crypto/core/strategy/orchestrator.py (external, not in this repo)"
  - "sigma-crypto/core/strategy/engines/state_manager.py (external, not in this repo)"
last_updated: 2026-08-04
maintained_by: ai
ai_summary: "SAMTC V6.7 (State Aware Multi-Temporal Consensus) uses a 6-TF FlowState machine with Storyline Latches, Inertial Flow, Siege detection, and 3 trade gates (Fader, Inertial, Discovery). Generals (MN1/W1/D1) set the narrative; Officers (H4/H1/M30) execute. D1 latch is the primary driver. ARCHIVED — the sigma-crypto codebase is not in this repo; kept as the design ancestor of the FOB cross-TF storyline model."
---

# SAMTC Overview

**State Aware Multi-Temporal Consensus** — the Python crypto trading strategy that ran on top of sigma_core B2B detection. Version at time of writing: **V6.7 "Inertial Flow"**.

> **Status: archived / reference only.** The `sigma-crypto` codebase this documents is not
> part of this repo, and none of the numbers below have been re-validated under the current
> protocol. It is kept because the cross-TF storyline machinery here (Generals/Officers,
> latches, magnets, siege) is the direct design ancestor of the FOB storyline model.
> Moved out of `mt5/Documentation/` on 2026-08-04 — nothing in it is MQL5.

---

## What SAMTC Does

SAMTC answers one question: **given all the B2B zones across all timeframes, which way should we trade right now?**

It does this by:
1. Maintaining a persistent **FlowState** for each of 6 timeframes
2. Using those states to build a **Storyline** — a directional narrative the market is telling
3. Allowing trades only when local signals align with the Storyline
4. Blocking trades when a **Roadblock** (opposing zone) sits in the path

---

## The Two Tiers: Generals and Officers

```
GENERALS (Context Only — they set direction, never trade directly)
─────────────────────────────────────────────────────────────
   MN1 ── "The Tide"       ← Monthly institutional flow
   W1  ── "The Wind"       ← Weekly directional bias
   D1  ── "The Path"       ← Daily primary driver (V6.7 PRIMARY)

OFFICERS (Execute Trades — they fight the battles the Generals map out)
─────────────────────────────────────────────────────────────
   H4  ── Control
   H1  ── Control
   M30 ── Control (entry TF for SAMTC)
   M15, M5, M1 ── Sniper (via B2B confirmation)
```

> [!DECISION]
> **D1 is the Primary Driver in V6.7.** The W1 latch is too slow to turn. D1 leads reversals. If D1 and W1 disagree (Civil War), D1 wins — Officers can trade with D1 even if W1 hasn't flipped yet.

---

## FlowState — What Each TF Tracks

Every timeframe (MN1, W1, D1, H4, H1, M30) maintains a persistent `FlowState` object:

| Field | Meaning |
|-------|---------|
| `origin_id` | The active B2B zone driving direction on this TF |
| `origin_dir` | BULLISH or BEARISH — which way the zone points |
| `latch_dir` | **Storyline Latch** — remembered direction even when origin goes invalid |
| `magnet_id` | The opposing zone this TF is driving toward |
| `outpost_id` | The most recent aligned zone between origin and magnet |
| `is_siege_active` | True when price is attacking the magnet from the wrong side |
| `roadblock_id` | An opposing zone that blocks continuation |

### Storyline Latches — Structural Memory

> [!DECISION]
> The `latch_dir` field persists even when the origin zone is invalidated. This is **structural memory** — the market's last clear directional statement stays in force until a new opposite origin forms.
>
> This solved the 2022 waterfall problem: W1 was slow to flip bearish, blocking valid D1 shorts. Latch let D1 lead the move.

---

## The Three Trade Gates

Every entry candidate passes through `is_trade_allowed()`:

### Gate 0 — Pre-Filters (all candidates)
1. **Officers Only**: MN1/W1/D1 zones never trade directly ("Generals Don't Fight")
2. **Tier Gating** (Phase 12A — `EfficiencyGovernor`): Some signal types restricted per TF
3. **Structural Gasket** (Phase 12C): Rejects entries too deep inside a zone (no edge)

### Gate A — Anti-Trend Faders (Reversal Sieges)
Triggered when the signal opposes the current D1 Storyline.

**These are HIGH FRICTION trades.** Allowed only at:
- A major Narrative zone (MN1/W1/D1) where the magnet has been touched at L1 or 50%
- Price must be inside the magnet's core (between 50% and L2)
- Signal direction must OPPOSE the origin direction (fader = reversal trade)

```
Example: D1 BULLISH origin driving toward MN1 BEARISH zone.
MN1 zone's magnet is touched. A H4 BEARISH B2B forms inside the MN1 zone.
→ Gate A allows the H4 short (fading the D1 bull run at MN1 resistance)
```

### Gate B — Inertial Flow (Continuation)
Triggered when the signal AGREES with the D1 Storyline.

**These are LIBERATED trades.** The Inertial Flow mode bypasses:
- Strict nesting requirements (in Strict mode, must be inside origin or outpost)
- W1 veto (D1 leads)
- Roadblock checks (Bulldozer mode: if price punched through the magnet L2, continue)

**Siege block:** If the magnet is under active siege (price attacking it from the wrong side), continuation is blocked — unless price has punched through (Bulldozer Exception).

### Gate C — Discovery Bridge
Triggered when D1 is currently invalid (no live origin) but the Latch is confluent.

Allows the local Officer (H4/H1/M30) to lead until D1 recovers its narrative.

---

## Key Concepts

### The Magnet
The opposing zone the current narrative is driving toward. For a BULLISH origin, the magnet is the nearest BEARISH zone above current price. Trades target the space between origin and magnet.

### Siege Mode
When price enters the magnet zone from the "wrong" side — e.g., price broke into a BEARISH zone from below, testing its L2. This is a dangerous condition (crowded trade, could reverse hard). New continuation entries are blocked during Siege unless the Bulldozer Exception triggers.

### The Bulldozer Exception
If price punches through the magnet's L2 (fully breaks the opposing zone), Siege is over — the zone is defeated. Continuation resumes, and the next outpost zone is promoted as the new origin.

### Successor Promotion
When a magnet zone is defeated (price closes beyond its L2), the most recent aligned outpost zone between origin and the defeated magnet becomes the new origin. The narrative continues without resetting.

---

## Performance Results

| Test | Period | Sharpe | Payoff | Skew | Status |
|------|--------|--------|--------|------|--------|
| 13A — OOS Alpha Sentinel | 2024–2025 | 1.16 | 1.65 | 3.43 | Awaiting CIO approval |
| 10C — Governance Baseline | 3yr | — | — | — | ✅ Approved baseline (Calmar 3.90, Sortino 3.06) |
| 9G — Max Alpha (IS) | In-sample | 1.90 | — | — | Research reference only |

These are the numbers as recorded in the sigma-crypto era. The `backtest-results` page they referenced is not in this repo, and none of them have been re-run under Protocol 4.0 — treat as historical, not as validated results.

---

## Signal Flow (Full)

```
sigma_core detects B2B zones → all TFs
    │
    ▼
StateManager.update_timeframe_flow() per TF, per bar
    ├── Sticky validation (keep origin if still valid)
    ├── Siege state update
    ├── Successor promotion (if magnet defeated)
    └── New origin search (if current origin dead)
    │
    ▼
FractureEngine.is_inside_opposing_zone() → roadblock_id
    │
    ▼
StrategyOrchestrator.is_trade_allowed(signal_tf, direction, zone)
    ├── Gate 0: Officers only + Tier gating + Gasket
    ├── Gate A: Fader (anti-trend reversal at major magnet)
    ├── Gate B: Inertial Flow (continuation with D1 storyline)
    └── Gate C: Discovery Bridge (when D1 is invalid)
    │
    ▼
TradeManager → position sizing → execution
```

---

## Vaulted Logic (Deactivated but Preserved)

These were active in earlier phases, disabled to restore 10C Alpha:
- **H4 Veto (Phase 12D):** H4 could block entries when misaligned — too restrictive
- **Temporal Muter (Phase 12B/D/E):** Cooldown after failed trade on same TF/direction — blocked too many good re-entries

> [!NOTE]
> Both are preserved in `Logic_Vault_V6.md` for potential re-activation.

---

## Related Pages

- [b2b-overview.md](b2b-overview.md) — The B2B zones SAMTC operates on
- [mt5-ea-architecture.md](../../mt5/Documentation/mt5-ea-architecture.md) — The MQL5 sibling (Sigma V5.0, legacy)
