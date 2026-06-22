# Baysix Research Protocol
_Last updated: 2026-06-22 — **Protocol 4.0 "Lean Gates"**. Design-of-record + full rationale: [docs/specs/2026-06-22-protocol-4.0-lean-gates.md](../specs/2026-06-22-protocol-4.0-lean-gates.md). Supersedes 3.2 (generic gating) and 3.3 (LdP/Carver/AQR infra) — those specs are archived in [docs/specs/_archive/](../specs/_archive/)._

> **One line:** 7 gates → 4. Strip the front-loaded academic machinery (DSR/PSR/CSCV/PBO, N_trials ledger, t-stat auto-kills). A good strategy is three reads: smooth equity curve, acceptable drawdown, holds under cost + walk-forward + Monte Carlo. MT5 emits the ledger; Python only analyses it.

## A good strategy = three reads
- **(a)** smooth equity curve · **(b)** acceptable drawdown · **(c)** holds under cost + walk-forward + Monte Carlo.
- Diagnostic loop: **bad curve → tune signal/entry params · high DD → tune sizing/exits.**
- t-stat is **reported beside** the curve, **never** an auto-kill (inherited orthodoxy, removed). OOS/WF persistence is the luck-test that replaced it.

## The 4 gates

| Gate | Name | What it asks | Pass bar | Code wall |
|---|---|---|---|---|
| **G1** | Premise | idea + one simple rule + thesis + **a linked paper**. Why should this edge exist? | sensible mechanism + falsifiable thesis + ≥1 `step2_papers` row; tag `idea_kind` + `output_type`. | `idea_kind`+`output_type` tagged **and** ≥1 paper |
| **G2** | Edge & Survival | build the rule; emit the **IS net-of-cost** ledger. Smooth curve + DD acceptable? | curve eyeball + DD read on a logged NET result. | ≥1 `step4_results` row with `cost_adjusted=1` |
| **G3** | Robustness | does the IS edge survive **walk-forward + Monte Carlo**? | OOS/WF persistence + MC trade-shuffle survival. | human read (OOS-freeze chokepoint on `open_gate(3)`) |
| **G4** | Live | MT5 tester → demo → live parity. | demo/live ledger matches tester within tolerance. | human read |

- **Cost is in from the first edge number** (G2 net, OOS net). No separate cost gate.
- **The old Gate-7 FIDELITY gap dissolves** — MT5 *is* the engine, so port-fidelity is replaced by G4 demo/live parity.
- Code-enforced by `pipeline.pass_gate` → `_enforce_gate_walls` (G1/G2 hard walls). `allow_incomplete=True` bypasses with a logged waiver reason.

## Gate status values
`open` (created, work in progress) · `passed` (question answered, criteria met) · `blocked` (cannot be answered yet — blocker logged) · `killed` (falsified here — `kill_reason` mandatory).

## Kill rule (unchanged, rule 8b)
- Kill stays **human + ≥2 FALSIFIED hypotheses** (base/symmetric framing + ≥1 directional/conditional variant). A single FALSIFIED is a **reframe** trigger, not a kill. Code-enforced in `pipeline.kill_idea`.

## IS run numbering (replaces DSR / N_trials)
- Per-idea **IS run labels** (IS-01, IS-02…): an `is_run` column on `step4_results` + the `is_runs` table (`idea_id, label, what_changed, created_at`).
- Its job isn't "best Sharpe" — it **counts how many shots were taken** before G3 (the only honest deflator kept). Register each tune via `pipeline.log_is_run()`; `log_result(stage IN ('IS','OOS'))` requires an `is_run` label.

## Metrics stack (settled 2026-06-22)
- Unit of measurement = **a trade (an event)**, never a calendar day.
1. **MT5 tester report → decides** (trade list + curve + Sharpe/PF/max-DD/recovery/expected payoff). Parsed by `io/ingest_tester_report.py`.
2. **empyrical → our-convention per-trade Sharpe** (T = trade count, no √252; matches [per_period_sharpe_units_rule]).
3. **QuantStats-lumi → decorates only** (tearsheet; its annualised Sharpe never drives a gate).
4. **Monte Carlo + Walk-forward → bespoke** on the trade list (the only real G3 build).
5. **Frequency** (trades/yr, avg hold, % time in market) is its own visible number, never baked into an annualised Sharpe.

## MT5-native architecture
- The **EA emits the ledger inside the MT5 Strategy Tester** — causal, bar-by-bar; the OnBar structure kills the argmax-by-position look-ahead that manufactured the old ORB "edge".
- **Python is the analysis layer only** — PnL + stats on the emitted ledger; it never simulates fills or reconstructs trades.
- **Venue = asset class:** CFD / FX / high-leverage → MT5 (wire now). Equity / ETF → IBKR (design seam, defer).

## The driver (use it, don't recall the ladder)
- `python research/code/gates/idea_cli.py next <idea_id>` → the ONE next legal action, computed from DB state.
- `... gatecheck <idea_id>` → hard PASS/BLOCK on G1 Premise · `... status <idea_id>` → snapshot · `... prebrief <idea_id>` → pre-brief check (rule 6).
- Gate sequence + applicability live in [research/code/gates/protocol.py](../../research/code/gates/protocol.py) (`idea_kind` picks which of G1–G4 apply: primitives are correctness-only {1,2}).

## DB write-contract (code layer only — rule 10)
- gate open/pass/block/kill → `pipeline.open_gate/pass_gate/block_gate/kill_idea`
- metric result → `pipeline.log_result()` (git_sha + n_obs required; `is_run` required on IS/OOS) · IS run → `pipeline.log_is_run()`
- strategy lineage → `strategy_log.log_change()` · QR find/dissect → `agent_log.log_agent_call/log_dissect_result` · human arch call → `agent_log.log_human_decision`
- task → `backlog.add_task/resolve_task`. Never raw `sqlite3` (hook-enforced by `protocol_guard.py`).

## On a nuke-and-rebuild, always preserve
`step1_ideas` (the idea catalog = research IP), `step2_papers` (dissected paper knowledge), and `log_strategy` (the live-config lineage). Everything else is rebuildable.

## What 4.0 dropped vs 3.2/3.3
DSR/PSR true-deflation · CSCV/PBO · speed-limit cost gate · purged/embargoed dev-CV · t-stat auto-kill · Gate-7 FIDELITY (→ G4) · the 7-gate ladder · `trial_family` ledger + the `n_trials/trial_family_id/config_hash/cost_bps/cost_basis` result columns.

**Kept:** idea_kind/output_type tagging (now at G1) · the metric wall (G2 needs a logged net result) · human + ≥2-falsified kill · the code-layer write-contract · **`step2_papers` + `log_agent` — MANDATORY** (every idea links a paper before leaving G1).
