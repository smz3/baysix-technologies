"""The adjudicator — code, not an agent.

This module exists so that "the agent talked itself into a promotion" is not a
reachable state. It reads the pre-registered rule, applies it, and returns a
verdict. There is no argument surface. If the agent disagrees with a verdict, the
remedy is a new pre-registered batch, never an override.

Ported from the MT5 side, where the reasoning was earned rather than assumed:

*   **Not `eval()`.** Rules are parsed to an AST and every node is vetted. Calls,
    attributes, subscripts, lambdas and comprehensions all raise.

*   **An unknown name RAISES, it does not return False.** A rule that silently
    fails open promotes on a typo, and a typo'd threshold that quietly returns
    False is indistinguishable from a clean falsification.

*   **A NULL input RAISES.** A missing out-of-sample leg must stop the
    adjudication, not compare as zero and read as a failed threshold.
"""

from __future__ import annotations

import ast
import enum
from dataclasses import dataclass
from typing import Any, Mapping

__all__ = ["ADJUDICATION_VARS", "Ruling", "eval_rule", "adjudicate", "RuleError"]


class RuleError(ValueError):
    """A rule that cannot be evaluated. Always fatal — never a silent False."""


#: The ONLY names a rule may reference. Anything else is a hard error.
#:
#: `is_` is the in-sample leg, `oos_` the holdout. `n_trials` is the multiplicity
#: counter and belongs in rules on purpose: as a search widens, the bar should rise.
ADJUDICATION_VARS: tuple[str, ...] = (
    # in-sample
    "is_p_hat", "is_n_pass", "is_n_fail", "is_n_censored", "is_n_resolved",
    "is_censored_frac", "is_ci_low", "is_ci_high",
    "is_net_usd", "is_n_trades", "is_max_dd_usd", "is_median_days_to_pass",
    # holdout
    "oos_p_hat", "oos_n_pass", "oos_n_fail", "oos_n_censored", "oos_n_resolved",
    "oos_censored_frac", "oos_ci_low", "oos_ci_high",
    "oos_net_usd", "oos_n_trades", "oos_max_dd_usd", "oos_median_days_to_pass",
    # search cost
    "n_trials",
)

_ALLOWED_NODES = (
    ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.USub,
    ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Compare,
    ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq,
    ast.Name, ast.Load, ast.Constant,
)


class Ruling(enum.Enum):
    PROMOTE = "PROMOTE"
    FALSIFIED = "FALSIFIED"
    #: Neither rule fired. The candidate is not promoted and not killed; it simply
    #: did not clear the bar it was registered against.
    NO_ACTION = "NO_ACTION"


@dataclass(frozen=True, slots=True)
class Verdict:
    ruling: Ruling
    promote_rule: str
    promote_fired: bool
    kill_rule: str | None
    kill_fired: bool
    #: Every variable the rules actually read, with the value they read. This is
    #: what makes a verdict auditable a month later.
    inputs_used: Mapping[str, Any]
    detail: str


def _names_in(expr: str) -> set[str]:
    return {
        n.id
        for n in ast.walk(ast.parse(_pythonise(expr), mode="eval"))
        if isinstance(n, ast.Name)
    }


def _pythonise(expr: str) -> str:
    """Accept the SQL-ish AND/OR a human naturally writes in a prereg file."""
    return (
        (expr or "")
        .replace(" AND ", " and ")
        .replace(" OR ", " or ")
        .replace(" NOT ", " not ")
    )


def eval_rule(expr: str, values: Mapping[str, Any]) -> bool:
    """Evaluate one promote_if / kill_if rule mechanically.

    Raises `RuleError` on an empty rule, an illegal construct, an unknown variable,
    or a variable whose value is None. Every one of those is a condition under
    which a returned `False` would be a lie.
    """
    raw = (expr or "").strip()
    if not raw:
        raise RuleError("empty adjudication rule")

    try:
        tree = ast.parse(_pythonise(raw), mode="eval")
    except SyntaxError as exc:
        raise RuleError(f"rule {raw!r} does not parse: {exc}") from exc

    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise RuleError(
                f"illegal construct {type(node).__name__} in rule {raw!r} — rules may "
                f"only compare the declared variables using and/or/not and + - * /"
            )
        if isinstance(node, ast.Name):
            if node.id not in ADJUDICATION_VARS:
                raise RuleError(
                    f"unknown variable {node.id!r} in rule {raw!r}. Allowed: "
                    f"{', '.join(ADJUDICATION_VARS)}"
                )
            if values.get(node.id) is None:
                raise RuleError(
                    f"rule {raw!r} references {node.id!r} but that value is NULL — "
                    f"the candidate is not ready to adjudicate; run the missing leg "
                    f"first rather than reading the gap as a failure"
                )

    return bool(
        eval(  # noqa: S307 — every node vetted above; builtins removed
            compile(tree, "<prereg>", "eval"), {"__builtins__": {}}, dict(values)
        )
    )


def adjudicate(
    promote_if: str, kill_if: str | None, values: Mapping[str, Any]
) -> Verdict:
    """Apply a pre-registered rule pair. The agent gets no vote.

    A candidate that fires BOTH rules is a contradiction in the pre-registration
    itself, not a close call — it raises, because silently preferring one of the
    two would mean the prereg did not actually decide anything.
    """
    promoted = eval_rule(promote_if, values)
    killed = eval_rule(kill_if, values) if kill_if else False

    if promoted and killed:
        raise RuleError(
            f"promote_if and kill_if BOTH fired. The pre-registration is "
            f"self-contradictory and cannot decide this candidate: "
            f"promote_if={promote_if!r}, kill_if={kill_if!r}. Register a new batch "
            f"with a coherent rule pair; do not pick a winner by hand."
        )

    read = sorted(_names_in(promote_if) | (_names_in(kill_if) if kill_if else set()))
    used = {k: values[k] for k in read}

    if promoted:
        ruling, detail = Ruling.PROMOTE, f"promote_if satisfied: {promote_if}"
    elif killed:
        ruling, detail = Ruling.FALSIFIED, f"kill_if satisfied: {kill_if}"
    else:
        ruling, detail = Ruling.NO_ACTION, "neither rule fired"

    return Verdict(
        ruling=ruling,
        promote_rule=promote_if,
        promote_fired=promoted,
        kill_rule=kill_if,
        kill_fired=killed,
        inputs_used=used,
        detail=detail,
    )
