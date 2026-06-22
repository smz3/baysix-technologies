# Where Everything Lives — Research Protocol + Gates

_A map, not a spec. When you need to know **which file** holds a protocol rule, a gate metric, or the code that enforces it, look here. The actual gate definitions live in [research_protocol.md](research_protocol.md)._

_Last updated: 2026-06-22 · Protocol 4.0 (lean, 4 gates)_

---

## The protocol itself (docs)

| File | What it is |
|------|------------|
| [research_protocol.md](research_protocol.md) | **THE gate ladder (Protocol 4.0)** — G1 Premise / G2 Edge+Survival / G3 Robustness / G4 Live. Edit this to change the rules. |
| [research_db_schema.md](research_db_schema.md) | DB schema mirror (gate tables: `step3_gates`, `step4_results`, `is_runs`, …). |
| [../specs/2026-06-22-protocol-4.0-lean-gates.md](../specs/2026-06-22-protocol-4.0-lean-gates.md) | ADR — the 4.0 lean rebuild (4 gates, dropped DSR/N_trials/t-stat auto-kill). |
| [../specs/_archive/2026-06-15-research-protocol-3.2-generic-gating.md](../specs/_archive/2026-06-15-research-protocol-3.2-generic-gating.md) | ADR (superseded) — 3.2 idea-kind branching. |
| [../specs/_archive/2026-06-15-research-infra-consolidation-ldp-carver-aqr.md](../specs/_archive/2026-06-15-research-infra-consolidation-ldp-carver-aqr.md) | ADR (superseded) — 3.2→3.3 keystone (DSR, CSCV/PBO, cost gate). |

**Downstream (deployment) half:**
[execution_protocol.md](execution_protocol.md) · [execution_schema.md](execution_schema.md)
(The old MT5 Gate-7 fidelity flow was dissolved in 4.0 — see [../specs/_archive/](../specs/_archive/).)

---

## The engine (`research/code/` — code that enforces the gates)

_Repackaged into 4 subpackages in 4.0; the flat `from research.code import X` contract is preserved via `__init__` re-exports._

| File | Role |
|------|------|
| [../../research/code/gates/pipeline.py](../../research/code/gates/pipeline.py) | `open_gate` / `pass_gate` / `block_gate` / `kill_idea` / `log_result` / `log_is_run` + `_enforce_gate_walls` |
| [../../research/code/gates/protocol.py](../../research/code/gates/protocol.py) | gate-sequencing rules (which of the 4 gates is legal next) |
| [../../research/code/gates/idea_cli.py](../../research/code/gates/idea_cli.py) | `next` / `gatecheck` / `status` / `prebrief` driver (CLI) |

> ⚠️ Changing a *rule* in [research_protocol.md](research_protocol.md) usually means also touching `gates/pipeline.py` / `gates/protocol.py` / `gates/idea_cli.py` — the doc and the enforcement must stay in sync.

---

## Guard (hook)

- [../../.claude/hooks/scripts/protocol_guard.py](../../.claude/hooks/scripts/protocol_guard.py) — PreToolUse guard; blocks raw `sqlite3` writes and `.db` hand-edits.

## Tests

- [../../research/tests/test_backlog.py](../../research/tests/test_backlog.py)
- [../../research/tests/test_run_and_log.py](../../research/tests/test_run_and_log.py)
- [../../research/tests/test_strategy_spec.py](../../research/tests/test_strategy_spec.py)
- [../../research/tests/test_struct_parity.py](../../research/tests/test_struct_parity.py)

## Schema rebuild

- [../../research/migrations/032_rebuild_brc40.py](../../research/migrations/032_rebuild_brc40.py) — the 4.0 lean BRC-only rebuild (migrations 010–031 are now historical; don't replay).

---

## The one-command driver

When in doubt about *what gate to run next*, don't recall the ladder — ask the DB:

```
python research/code/gates/idea_cli.py next <idea_id>     # the ONE next legal action
python research/code/gates/idea_cli.py status             # snapshot of all ideas
python research/code/gates/idea_cli.py gatecheck <idea_id># hard PASS/BLOCK on G1
```
