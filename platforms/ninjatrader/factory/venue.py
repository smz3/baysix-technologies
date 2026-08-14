"""The venue contract — six verbs, and why the sixth exists.

A platform is automatable exactly to the degree that the loop's verbs have a
non-GUI entry point. Five of them are obvious:

    write_source · compile · run_test · read_fitness · read_results

The sixth is `selfcheck`, and it is the one that was added after the research
rather than before it. NinjaTrader's headless backtest switches are undocumented
and unsupported by the vendor, so they can change or vanish on any minor release.
An adapter built on that surface must prove itself against a KNOWN strategy with a
KNOWN result at the top of every session rather than trust it.

Making that a contract verb instead of an NT8 detail means every venue proves
itself before it is allowed to produce a number — including the Python oracle,
which is the one most likely to be quietly wrong because nobody else wrote it.

## The two-engine arrangement

`PyOracle` searches. NT8 arbitrates. A candidate must produce materially the same
result on both before it can be promoted, and a disagreement HALTS the batch — it
does not demote the candidate. A divergence means one of the engines is wrong, and
which one is a question, not a ranking.

This is the only available defence against the failure mode that matters here: not
an error, but a *plausible wrong number*.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, Sequence, runtime_checkable

from factory.objective import BarrierOutcome, EquityPoint
from factory.spec import StrategySpec

__all__ = [
    "Venue",
    "VenueRole",
    "Window",
    "CompileResult",
    "RunHandle",
    "RunResult",
    "SelfCheckReport",
    "Trade",
    "AgreementReport",
    "compare",
]


class VenueRole(enum.Enum):
    #: Searches. Fast, fully ours, exercised thousands of times per batch.
    SEARCH = "SEARCH"
    #: Arbitrates. Slow, third-party, exercised on survivors only.
    ARBITER = "ARBITER"
    #: Executes. Touches an account. Never driven unattended.
    EXECUTION = "EXECUTION"


@dataclass(frozen=True, slots=True)
class Window:
    start: datetime
    end: datetime
    #: IS windows may be searched freely. OOS is a one-way door: looking is
    #: spending, so the flag travels with the window rather than living in a
    #: caller's head.
    is_holdout: bool = False

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValueError(f"window ends before it starts: {self.start} -> {self.end}")


@dataclass(frozen=True, slots=True)
class CompileResult:
    ok: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    artifact: Path | None = None
    log: str = ""


@dataclass(frozen=True, slots=True)
class RunHandle:
    """A run in flight. Completion is signalled by a sentinel FILE EXISTING.

    Never by output mtime — a partially written report has a fresh mtime and reads
    as a finished run, which is how a truncated result becomes a logged finding.
    """

    venue: str
    run_id: str
    workdir: Path
    sentinel: Path
    started_at: datetime
    spec_hash: str

    @property
    def done(self) -> bool:
        return self.sentinel.exists()


@dataclass(frozen=True, slots=True)
class Trade:
    entry_ts: datetime
    exit_ts: datetime
    direction: int          # +1 long, -1 short
    qty: float
    entry_px: float
    exit_px: float
    gross_usd: float
    cost_usd: float

    @property
    def net_usd(self) -> float:
        return self.gross_usd - self.cost_usd


@dataclass(frozen=True, slots=True)
class RunResult:
    handle: RunHandle
    trades: tuple[Trade, ...]
    equity: tuple[EquityPoint, ...]
    outcome: BarrierOutcome
    objective_fingerprint: str
    #: Whatever the venue wants on the record: build ids, data ranges, settings
    #: that would change the number if they moved.
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def n_trades(self) -> int:
        return len(self.trades)

    @property
    def net_usd(self) -> float:
        return sum(t.net_usd for t in self.trades)


@dataclass(frozen=True, slots=True)
class SelfCheckReport:
    ok: bool
    venue: str
    checked_at: datetime
    #: Each entry: (what was checked, expected, observed, passed)
    assertions: tuple[tuple[str, Any, Any, bool], ...] = ()
    detail: str = ""

    def raise_if_failed(self) -> None:
        if self.ok:
            return
        failed = [
            f"{name}: expected {exp!r}, observed {obs!r}"
            for name, exp, obs, passed in self.assertions
            if not passed
        ]
        raise RuntimeError(
            f"{self.venue} failed selfcheck and may not produce a number this "
            f"session -> " + "; ".join(failed or [self.detail])
        )


@runtime_checkable
class Venue(Protocol):
    """Six verbs. Implement all of them, including the one you think you can skip."""

    name: str
    role: VenueRole

    def write_source(self, spec: StrategySpec) -> Path: ...

    def compile(self, src: Path) -> CompileResult: ...

    def run_test(self, spec: StrategySpec, window: Window, data_ref: str) -> RunHandle: ...

    def read_fitness(self, handle: RunHandle) -> float: ...

    def read_results(self, handle: RunHandle) -> RunResult: ...

    def selfcheck(self) -> SelfCheckReport: ...


# --------------------------------------------------------------------------- #
#  cross-engine agreement
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class AgreementReport:
    agree: bool
    spec_hash: str
    #: (metric, search value, arbiter value, tolerance, within)
    lines: tuple[tuple[str, float, float, float, bool], ...]
    detail: str = ""

    def raise_if_divergent(self) -> None:
        if self.agree:
            return
        bad = [
            f"{m}: search {a:.4f} vs arbiter {b:.4f} (tolerance {t:.4f})"
            for m, a, b, t, ok in self.lines
            if not ok
        ]
        raise RuntimeError(
            f"cross-engine divergence on {self.spec_hash} — the batch HALTS. One of "
            f"the two engines is wrong and which one is a question, not a ranking. "
            + "; ".join(bad)
        )


def compare(
    search: RunResult,
    arbiter: RunResult,
    *,
    trade_count_tol: float = 0.05,
    net_usd_tol_frac: float = 0.10,
    net_usd_tol_abs: float = 25.0,
) -> AgreementReport:
    """Do two engines tell the same story about the same spec on the same window?

    Tolerances are fractional and deliberately loose, because the engines will
    never agree to the cent: they fill on different data granularity and round
    differently. What must agree is the SHAPE — roughly the same trades, roughly
    the same money, the same verdict.

    The verdict is compared exactly. A PASS on one engine and a FAIL on the other
    is not a tolerance question.
    """
    if search.handle.spec_hash != arbiter.handle.spec_hash:
        raise ValueError(
            f"comparing different specs: {search.handle.spec_hash} vs "
            f"{arbiter.handle.spec_hash}"
        )

    lines: list[tuple[str, float, float, float, bool]] = []

    n_a, n_b = float(search.n_trades), float(arbiter.n_trades)
    n_tol = max(1.0, trade_count_tol * max(n_a, n_b))
    lines.append(("n_trades", n_a, n_b, n_tol, abs(n_a - n_b) <= n_tol))

    p_a, p_b = search.net_usd, arbiter.net_usd
    p_tol = max(net_usd_tol_abs, net_usd_tol_frac * max(abs(p_a), abs(p_b)))
    lines.append(("net_usd", p_a, p_b, p_tol, abs(p_a - p_b) <= p_tol))

    v_a = search.outcome.verdict
    v_b = arbiter.outcome.verdict
    same_verdict = v_a is v_b
    lines.append((
        f"verdict({v_a.value} vs {v_b.value})",
        search.outcome.fitness, arbiter.outcome.fitness, 0.0, same_verdict,
    ))

    agree = all(ok for *_, ok in lines)
    return AgreementReport(
        agree=agree,
        spec_hash=search.handle.spec_hash,
        lines=tuple(lines),
        detail="" if agree else "see lines",
    )
