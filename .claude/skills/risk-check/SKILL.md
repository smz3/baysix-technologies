---
name: risk-check
description: >
  Risk and compliance check before any sizing change, strategy promotion, or live action.
  Validates position sizing, drawdown vs limit, leverage, and correlation against the active
  Deployment Profile, and arms the kill switch. Invoke whenever risk, position size, drawdown,
  leverage, kill-switch, or "is this safe to deploy/size" comes up — and always before capital
  moves on the XAUUSD MT5 book. Produces an APPROVED / CONDITIONAL / BLOCKED verdict.
---

# Skill: risk-check

The risk gate. Run before any sizing change, strategy promotion to live, or capital action.
This replaces the former risk-manager agent — same discipline, run inline (no spawn).

## Usage
```
/risk-check [what you're evaluating — e.g. "size IB-001 for the Just Markets profile"]
```

## Source of truth
- **Active Deployment Profile** + limits — `Memory/risk_parameters.md` (binding kill constraint, target vol, max drawdown, capacity floor per venue). If it doesn't exist yet, say so and stop — a gate with no profile cannot know its threshold.
- Methodology — [BAYSIX_FRAMEWORK.md](../../../BAYSIX_FRAMEWORK.md) Part 2 (portfolio-risk) + Layer 0 (profile).

## Procedure
1. **Load** the active profile and its numeric limits from `risk_parameters.md`.
2. **Assess exposure** — proposed position size, leverage, correlation to existing book (if 2+ strategies).
3. **Validate** — does the action stay inside every profile limit? `size = min(vol-target, Kelly cap) × conviction`.
4. **Stress** — what happens in a 3-sigma adverse move? Ruin probability < 5%?
5. **Kill-switch check** — flag `[KILL SWITCH]` if any of: drawdown > profile `max_drawdown`; size > `max_position_pct`; leverage > approved; rolling expectancy negative over last `N_min` trades (never win-rate).
6. **Decide + log** — verdict below; if flagged, append a dated line to `Memory/risk_log.md`.

## Output
```markdown
## Risk Check
**Evaluating**: [what]
**Profile**: [active profile + key limits]
**Exposure**: [size / leverage / drawdown / correlation]
**Verdict**: APPROVED / CONDITIONAL / BLOCKED
**Kill switch**: Not triggered / [TRIGGERED — exact breach with numbers]
**Requires user approval**: Yes/No   (capital moves always = Yes)
```

## Hard rules (from CLAUDE.md)
- Never authorize a live trade without explicit user confirmation (two-key rule).
- No capital moves without this check passing. You trade XAUUSD on MT5 by hand — this is the pre-trade sanity gate, not an order router.
