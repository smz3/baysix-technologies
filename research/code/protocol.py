"""Research-protocol state machine — the single source of truth for the ONE next
legal action on an idea, COMPUTED from research.db rather than remembered.

`next_step(idea_id)` reads gate / result / falsification state and returns the
next legal protocol move plus its precondition. Rendered by
`idea_cli.py next <idea_id>`. The point: the workflow stops being prose that
scrolls out of context mid-session and becomes something you *query*.

Lifecycle (CLAUDE.md rules 8 / 8b · docs/reference/research_protocol.md):
    Gate 0  prior-art / mathematical truth      open+pass before ANY code
    Gate 1  simple rule + null hypothesis        open+pass before model code
    Gate 2  simplest impl produces sane output
    Gate 3  dumb-rule edge, raw + net            EVIDENCE gate (t>1.0 confirm)
    Gate 4  sophisticated model vs baseline
    Gate 5  tradeable signal, positive net edge  EVIDENCE gate (t>2.0 confirm)
    Gate 6  survives walk-forward / OOS          EVIDENCE gate
    Gate 7  deployed artifact == validated bt    FIDELITY gate (tester evidence)

A FALSIFIED hypothesis is a REFRAME trigger, not a kill; kill needs >=2 (rule 8b).
t-stat is a CONFIRMATION bar at Gates 3/5 — never an anchor/front-gate cutoff.

This module holds workflow logic ONLY; all DB access is via pipeline getters.
"""
from __future__ import annotations

import pipeline

# Gates whose pass requires a LOGGED metric result, not a free assertion.
EVIDENCE_GATES = {3: "t>1.0 raw+net", 5: "t>2.0 net", 6: "OOS / walk-forward retention"}
FIDELITY_GATE = 7

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
    return " ".join(f"{n}:{_SYM.get(states.get(n), '-')}" for n in range(8))


def _open_action(n: int) -> tuple[str, str]:
    if n in EVIDENCE_GATES:
        return (f"Gate {n} OPEN -> run backtest, pipeline.log_result(), then pass_gate({n})",
                f"needs metric EVIDENCE ({EVIDENCE_GATES[n]}); t-stat is a confirmation bar, not an anchor")
    if n == FIDELITY_GATE:
        return ("Gate 7 OPEN -> run MT5 tester vs research, log fidelity diff, then pass_gate(7)",
                "pass_gate(7) is code-blocked without real tester-vs-research evidence")
    return (f"Gate {n} OPEN -> pass_gate({n}) when the gate question is met, else block_gate",
            "sense/structure gate -- no metric required")


def _compute(idea_id: str, states: dict[int, str], falsified: int) -> tuple[str, str]:
    for n in range(8):
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
    return ("ALL GATES PASSED -> proceed to deploy ladder (FORWARD: demo -> live)",
            "validated end-to-end including Gate 7 fidelity")


def next_step(idea_id: str) -> dict:
    """Compute the single next legal protocol action for an idea from DB state."""
    idea = pipeline.get_idea(idea_id)
    if not idea:
        return {"idea": idea_id, "error": f"no idea {idea_id!r}"}

    states = _gate_states(idea_id)
    falsified = pipeline._falsified_count(idea_id)
    out = {
        "idea": idea_id,
        "status": idea.get("status"),
        "gates": _gate_line(states),
        "falsified": f"{falsified}/2 (kill needs 2)",
    }

    if idea.get("status") == "killed":
        out["next"] = "KILLED — no further action"
        out["why"] = idea.get("kill_reason") or ""
        return out

    out["next"], out["why"] = _compute(idea_id, states, falsified)
    return out
