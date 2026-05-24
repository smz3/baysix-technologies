---
name: check-mt5-health
description: >
  Check the live XAUUSD B2B MT5 Expert Advisor: current EA version, whether a compiled .ex5 binary
  exists, open issues, and latest development state. Invoke when asked about MT5/EA health, the live
  gold system status, or "is the EA up to date". Read-only — never edits MQL5 source.
---

# Skill: check-mt5-health

Health check for the live B2B XAUUSD Expert Advisor.
EA lives at `workspace/baysix-engine/trading-engine/mt5-path/b2b-mt5/` (junction-linked into the MT5 terminal).

## Usage
```
/check-mt5-health
```

## Steps
1. **EA architecture + state** — read `b2b-mt5/Documentation/mt5-ea-architecture.md`; scan `Documentation/modules/` and `Documentation/samtc-overview.md` for the active design.
2. **Compiled binary** — look for `.ex5` files under `b2b-mt5/` (esp. `Experts/`); note version + last-modified.
3. **Source version** — newest version dir under `b2b-mt5/Include/Sigma_System/` (e.g. `V5.0/`).
4. **Strategy state** — `Memory/strategy_state.md` for active systems + last result.

## Output
```markdown
## MT5 EA Health Report
**EA version**:      V[X]
**Compiled .ex5**:   Found (modified [date]) / Not Found — EA cannot be running
**Active dev**:      Yes / No
**Open issues**:     [from docs, or None]
**Heartbeat**:       No heartbeat log — verify in the MT5 terminal manually
**Status**:          Healthy / Needs Attention / Unknown
**Action**:          [if any]
```

## Notes
- Read-only — never modify MQL5 source as part of this check.
- Alert if no compiled binary exists (the EA cannot be live).
- You run XAUUSD on Just Markets by hand — this reports state, it does not control the EA.
