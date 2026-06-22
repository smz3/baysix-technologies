# Where Everything Lives — Research Protocol + Gates

_A map, not a spec. When you need to know **which file** holds a protocol rule, a gate metric, or the code that enforces it, look here. The actual gate definitions live in [research_protocol.md](research_protocol.md)._

_Last updated: 2026-06-22 · Protocol 3.3_

---

## The protocol itself (docs)

| File | What it is |
|------|------------|
| [research_protocol.md](research_protocol.md) | **THE gate ladder (Protocol 3.3)** — gate defs + metrics. Edit this to change the rules. |
| [research_db_schema.md](research_db_schema.md) | DB schema mirror (gate tables: `step3_gates`, `step4_results`, …). |
| [../specs/2026-06-15-research-protocol-3.2-generic-gating.md](../specs/2026-06-15-research-protocol-3.2-generic-gating.md) | ADR — idea-kind branching, generic Gate 2/3/5. |
| [../specs/2026-06-15-research-infra-consolidation-ldp-carver-aqr.md](../specs/2026-06-15-research-infra-consolidation-ldp-carver-aqr.md) | ADR — 3.2→3.3 keystone (DSR, CSCV/PBO Gate 5b, cost gate). |

**Downstream (deployment) half:**
[execution_protocol.md](execution_protocol.md) · [mt5_fidelity_flow.md](mt5_fidelity_flow.md) (Gate 7) · [execution_schema.md](execution_schema.md)

---

## The engine (`research/code/` — code that enforces the gates)

| File | Role |
|------|------|
| [../../research/code/pipeline.py](../../research/code/pipeline.py) | `open_gate` / `pass_gate` / `block_gate` / `kill_idea` / `log_result` |
| [../../research/code/protocol.py](../../research/code/protocol.py) | gate-sequencing rules (which gate is legal next) |
| [../../research/code/idea_cli.py](../../research/code/idea_cli.py) | `next` / `gatecheck` / `status` / `prebrief` driver (CLI) |
| [../../research/code/gate2_sanity.py](../../research/code/gate2_sanity.py) | shared Gate 2 (sanity) |
| [../../research/code/gate5_report.py](../../research/code/gate5_report.py) | shared Gate 5 (significance report) |
| [../../research/code/trial_family.py](../../research/code/trial_family.py) | N_trials / DSR ledger |

> ⚠️ Changing a *rule* in [research_protocol.md](research_protocol.md) usually means also touching `pipeline.py` / `protocol.py` / `idea_cli.py` — the doc and the enforcement must stay in sync.

---

## Guard (hook)

- [../../.claude/hooks/scripts/protocol_guard.py](../../.claude/hooks/scripts/protocol_guard.py) — PreToolUse guard; blocks raw `sqlite3` writes and `.db` hand-edits.

## Tests

- [../../research/tests/test_gate2_sanity.py](../../research/tests/test_gate2_sanity.py)
- [../../research/tests/test_gate5_report.py](../../research/tests/test_gate5_report.py)

## Schema migrations (gate-related)

- [../../research/migrations/017_dedupe_gate_pipeline_view.py](../../research/migrations/017_dedupe_gate_pipeline_view.py)
- [../../research/migrations/022_gate7_tester_schema.py](../../research/migrations/022_gate7_tester_schema.py)

---

## Per-model gate implementations

_Model-specific — **not** the protocol. These run a model's data through the gates; leave them out of any protocol redesign._

- [../../research/models/orb/orb001/](../../research/models/orb/orb001/) · [orb002/](../../research/models/orb/orb002/) · [orb004/](../../research/models/orb/orb004/) — `gate2/3/5/6*.py`
- [../../research/models/hmm/](../../research/models/hmm/) — `gate3/4*.py`
- [../../research/models/msm/](../../research/models/msm/) — `gate2*.py`, `gate_hypC*.py`

---

## The one-command driver

When in doubt about *what gate to run next*, don't recall the ladder — ask the DB:

```
python research/code/idea_cli.py next <idea_id>     # the ONE next legal action
python research/code/idea_cli.py status             # snapshot of all ideas
python research/code/idea_cli.py gatecheck <idea_id># hard PASS/BLOCK on Gates 0/1
```
