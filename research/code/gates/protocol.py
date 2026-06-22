"""Research-protocol state machine — the single source of truth for the ONE next
legal action on an idea, COMPUTED from research.db rather than remembered.

`next_step(idea_id)` reads gate / result / falsification state and returns the
next legal protocol move plus its precondition. Rendered by
`idea_cli.py next <idea_id>`. The point: the workflow stops being prose that
scrolls out of context mid-session and becomes something you *query*.

Protocol 4.0 — four lean gates (docs/specs/2026-06-22-protocol-4.0-lean-gates.md):
    G1  Premise          idea + one simple rule + thesis + a linked paper  (no code)
    G2  Edge & Survival  build the rule, emit IS net ledger; smooth curve + DD  (EVIDENCE)
    G3  Robustness       survives walk-forward + Monte Carlo                (EVIDENCE)
    G4  Live             MT5 tester -> demo -> live parity                  (EVIDENCE)

A FALSIFIED hypothesis is a REFRAME trigger, not a kill; kill needs >=2 (rule 8b).
t-stat is NOT an auto-kill in 4.0 — it may be reported beside the curve, never
blocks; OOS/WF persistence (G3) is the luck-test that replaced it.

This module holds workflow logic ONLY; all DB access is via pipeline getters.
"""
from __future__ import annotations

from research.code.gates import pipeline

# Gates whose pass requires LOGGED evidence, not a free assertion.
EVIDENCE_GATES = {
    2: "smooth equity curve + acceptable DD on a NET-of-cost result",
    3: "OOS / walk-forward persistence + Monte-Carlo trade-shuffle survival",
}
LIVE_GATE = 4

# idea_kind picks WHICH gates apply (legal skip of vacuous gates). Untagged ->
# the full ladder. Primitives are correctness-only (no edge/robustness/live).
GATE_APPLICABILITY = {
    "strategy":   {1, 2, 3, 4},
    "primitive":  {1, 2},
    "overlay":    {1, 2, 3, 4},
    "classifier": {1, 2, 3, 4},
}
_FULL = {1, 2, 3, 4}


def applicable_gates(idea_kind: str | None) -> set[int]:
    """Gates that apply to this idea_kind. Untagged -> full ladder (back-compat)."""
    return GATE_APPLICABILITY.get(idea_kind, _FULL)


_SYM = {"passed": "P", "open": "o", "blocked": "X", "killed": "K"}


def _resolved(by_attempts: list[str]) -> str:
    """Collapse a gate's attempt statuses to one: passed > open > blocked > killed."""
    s = set(by_attempts)
    for pref in ("passed", "open", "blocked", "killed"):
        if pref in s:
            return pref
    return "none"


def _gate_states(idea_id: str) -> dict[int, str]:
    rows = pipeline.get_gates(idea_id)
    acc: dict[int, list[str]] = {}
    for g in rows:
        acc.setdefault(g.get("gate_number"), []).append(g.get("status"))
    return {n: _resolved(v) for n, v in acc.items()}


def _gate_line(states: dict[int, str]) -> str:
    return " ".join(f"{n}:{_SYM.get(states.get(n), '-')}" for n in (1, 2, 3, 4))


def _open_action(n: int) -> tuple[str, str]:
    if n in EVIDENCE_GATES:
        return (f"Gate {n} OPEN -> run/emit the ledger, pipeline.log_result(net), then pass_gate({n})",
                f"needs EVIDENCE ({EVIDENCE_GATES[n]})")
    if n == LIVE_GATE:
        return ("Gate 4 OPEN -> run MT5 tester -> demo -> live, log the parity diff, then pass_gate(4)",
                "demo/live ledger must match the tester within tolerance")
    return (f"Gate {n} OPEN -> pass_gate({n}) when the gate question is met, else block_gate",
            "premise gate -- mechanism + falsifiable thesis + >=1 linked paper")


def _compute(idea_id: str, states: dict[int, str], falsified: int,
             gates: set[int]) -> tuple[str, str]:
    for n in (1, 2, 3, 4):
        if n not in gates:
            continue  # not applicable to this idea_kind — legal skip
        s = states.get(n)
        if s == "passed":
            continue
        q = pipeline.GATE_QUESTIONS[n]
        if s is None:
            return (f"OPEN Gate {n}: {q}",
                    f"pipeline.open_gate('{idea_id}', {n}, pass_criteria=...) -- prior gate(s) passed")
        if s == "open":
            return _open_action(n)
        if s == "blocked":
            if falsified >= 2:
                return (f"Gate {n} BLOCKED with {falsified} FALSIFIED -- kill_idea now permitted, OR reframe again",
                        f"rule 8b satisfied ({falsified}>=2); kill only if the thesis is exhausted")
            return (f"Gate {n} BLOCKED -> reframe or test a NEW hypothesis (do not kill yet)",
                    f"FALSIFIED={falsified}/2; <2 = reframe via variant (rule 8b), not kill_idea")
        if s == "killed":
            return (f"Gate {n} KILLED -- idea is dead at this gate", "no further action")
    return ("ALL GATES PASSED -> live (G4 demo->live parity holds)",
            "validated end-to-end on the MT5-native ledger")


def next_step(idea_id: str) -> dict:
    """Compute the single next legal protocol action for an idea from DB state."""
    idea = pipeline.get_idea(idea_id)
    if not idea:
        return {"idea": idea_id, "error": f"no idea {idea_id!r}"}

    states = _gate_states(idea_id)
    falsified = pipeline._falsified_count(idea_id)
    kind = idea.get("idea_kind")
    gates = applicable_gates(kind)
    out = {
        "idea": idea_id,
        "status": idea.get("status"),
        "idea_kind": kind or "UNTAGGED (full ladder; set idea_kind at G1)",
        "gates": _gate_line(states),
        "applies": " ".join(str(n) for n in sorted(gates)),
        "falsified": f"{falsified}/2 (kill needs 2)",
        "warnings": [],
    }

    if idea.get("status") == "killed":
        out["next"] = "KILLED — no further action"
        out["why"] = idea.get("kill_reason") or ""
        return out

    out["next"], out["why"] = _compute(idea_id, states, falsified, gates)
    return out
