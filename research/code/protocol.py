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

try:                                    # package import (pytest: research.code.*)
    from research.code import pipeline
except ImportError:                     # script import (own dir on sys.path)
    import pipeline

# Gates whose pass requires a LOGGED metric result, not a free assertion.
EVIDENCE_GATES = {3: "t>1.0 raw+net", 5: "t>2.0 net", 6: "OOS / walk-forward retention"}
FIDELITY_GATE = 7

# Protocol 3.2 — idea_kind picks WHICH gates apply (legal skip of vacuous gates).
# docs/specs/2026-06-15-research-protocol-3.2-generic-gating.md
# Fallback: an untagged idea (idea_kind NULL) gets the full ladder (3.1 behaviour).
GATE_APPLICABILITY = {
    "strategy":   {0, 1, 2, 3, 4, 5, 6, 7},  # 4 collapses into 5 if no overlay
    "primitive":  {0, 1, 2, 7},              # correctness + port fidelity; no edge/signal gates
    "overlay":    {0, 1, 2, 4, 5, 6, 7},     # conditional improvement; no standalone baseline (3)
    "classifier": {0, 1, 2, 3, 4, 5, 6, 7},  # Markov-4 sanity at 2, model at 4
}

# Significance test is RESOLVED from output_type, never chosen by the agent.
SIGNIFICANCE_TEST = {
    "pnl_stream":       "PSR / DSR (deflated Sharpe)",
    "classifier_score": "IC t-stat / AUC CI",
    "primitive_output": "correctness (oracle / parity)",
}

# Which step4_results metric_key family PROVES the mandated Gate-5 test. Single
# source of truth alongside SIGNIFICANCE_TEST — pipeline.pass_gate(5) validates a
# logged metric_key against this so a pnl_stream can't pass Gate 5 on an AUC row
# (3.2 enforcement chain step 4). Substring match, case-insensitive (so 'psr_net'
# or 'regime_change_auc_hmm' count). primitive_output -> Gate 5 inapplicable.
SIGTEST_METRIC_KEYS = {
    "pnl_stream":       ("psr", "dsr", "deflated_sharpe"),
    "classifier_score": ("ic_t", "auc"),
    "primitive_output": (),
}


def significance_test_for(idea_kind: str | None, output_type: str | None) -> str:
    """The mandated Gate-5 significance test for an idea, resolved from output_type.
    Single source of truth — agents read this, they never decide it."""
    if not output_type:
        return "UNDECLARED — set output_type at Gate 1 (pnl_stream/classifier_score/primitive_output)"
    return SIGNIFICANCE_TEST.get(output_type, f"UNKNOWN output_type {output_type!r}")


def metric_key_matches_sigtest(output_type: str | None, metric_key: str | None) -> bool:
    """True if a step4_results metric_key satisfies the Gate-5 test mandated by
    output_type. Resolved from SIGTEST_METRIC_KEYS — never an agent's free call."""
    needles = SIGTEST_METRIC_KEYS.get(output_type or "")
    if not needles:  # undeclared / primitive_output -> nothing satisfies it here
        return False
    mk = (metric_key or "").lower()
    return any(n in mk for n in needles)


def applicable_gates(idea_kind: str | None) -> set[int]:
    """Gates that apply to this idea_kind. Untagged -> full ladder (back-compat)."""
    return GATE_APPLICABILITY.get(idea_kind, {0, 1, 2, 3, 4, 5, 6, 7})

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


def _compute(idea_id: str, states: dict[int, str], falsified: int,
             gates: set[int] | None = None) -> tuple[str, str]:
    gates = gates if gates is not None else set(range(8))
    for n in range(8):
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
    return ("ALL GATES PASSED -> proceed to deploy ladder (FORWARD: demo -> live)",
            "validated end-to-end including Gate 7 fidelity")


def _has_conditioning(idea_id: str) -> bool:
    """True if a conditioning component has been declared in log_strategy. 3.2 wants
    a `strategy`'s conditional edge declared (mechanism-born) before Gate 3 tests it."""
    try:                                # package vs script import (mirror pipeline)
        from research.code import strategy_log
    except ImportError:
        import strategy_log
    return any(r.get("component") == "conditioning" for r in strategy_log.get_lineage(idea_id))


def _advisories(idea_id: str, idea: dict, states: dict[int, str], kind: str | None) -> list[str]:
    """Soft driver warnings (3.2 task 81) — surfaced, not blocking. The hard wall is
    Gate-5 metric enforcement (task 80); these nudge declaration before you get there."""
    out: list[str] = []
    # output_type undeclared -> Gate-5 enforcement is silently skipped (back-compat).
    if kind in ("strategy", "classifier", "overlay") and not idea.get("output_type"):
        out.append("output_type UNDECLARED — set it at Gate 1 (pipeline.update_idea); "
                   "until then the Gate-5 significance-test wall is skipped.")
    # a strategy that has reached Gate 3 should have declared its conditioning.
    if kind == "strategy" and states.get(3) is not None and not _has_conditioning(idea_id):
        out.append("Gate 3 reached with NO conditioning declared — 3.2 tests the "
                   "CONDITIONED rule. Declare it (strategy_log.log_change component="
                   "'conditioning') or confirm the edge is genuinely symmetric.")
    return out


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
        "idea_kind": kind or "UNTAGGED (full ladder; set idea_kind)",
        "gates": _gate_line(states),
        "applies": " ".join(str(n) for n in sorted(gates)),
        "sig_test": significance_test_for(kind, idea.get("output_type")),
        "falsified": f"{falsified}/2 (kill needs 2)",
        "warnings": [],
    }

    if idea.get("status") == "killed":
        out["next"] = "KILLED — no further action"
        out["why"] = idea.get("kill_reason") or ""
        return out

    out["next"], out["why"] = _compute(idea_id, states, falsified, gates)
    out["warnings"] = _advisories(idea_id, idea, states, kind)
    return out
