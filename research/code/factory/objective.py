"""The objective — what this factory is actually optimising, and nothing else.

Two objectives live here, both barrier problems: *does the account reach a target
before it hits a floor?*  Neither is a terminal-wealth question and neither is
blended with anything.

    barrier_fixed   floor is a constant.  Port of the MT5 GRW objective, kept only
                    so gold logic can be tested for engine independence against a
                    result that already exists.

    barrier_prop    floor MOVES.  This is the real one: a prop-firm evaluation.

Three rules carried over from the MT5 side unchanged, because each was paid for:

1.  **One run is ONE Bernoulli draw.**  A single equity path cannot estimate a
    probability and must not pretend to.  `p_hat` comes from K independent,
    NON-OVERLAPPING windows (see `aggregate`), never from one pass.

2.  **CENSORED is not FAIL.**  A window that ended with neither barrier touched is
    unresolved, not unsuccessful.  Scoring it as 0.0 makes "we ran out of data"
    indistinguishable from "the method died", which is the exact substitution the
    whole objective-as-artifact discipline exists to prevent.

3.  **The objective is a declared, versioned artifact.**  It lives in
    `config/objective/*.json`, it is never edited by an agent, and a change bumps
    the version and starts a NEW trial family.  Old passes were judged against a
    different question and cannot be pooled with new ones.

## The prop rules, and the one that is genuinely surprising

Verified against Topstep's own help centre on 2026-08-13 (CITED, see the JSON's
`sources`).  Three mechanics, and they interact:

*   **The floor ratchets on END-OF-DAY BALANCE, and it locks.**  The Maximum Loss
    Limit starts `mll_offset` below the starting balance, rises as the end-of-day
    balance grows, never falls, and freezes permanently once it reaches the
    starting balance.  It does NOT track the intraday equity high-water mark
    forever — an earlier research note said it did, and that was wrong in both
    halves.

*   **But it is enforced intraday, on EQUITY.**  Monitored in real time including
    unrealized P&L; a touch liquidates immediately.  So the floor is *set* daily
    and *tested* continuously.  Both halves matter and modelling only one of them
    produces a number that looks right and is not.

*   **The consistency rule makes the target ENDOGENOUS.**  `best_day / total_profit`
    must stay at or below `consistency_frac`.  Breaching it does not fail the
    account — it RAISES the profit target until the ratio is satisfied again:

        effective_target = max(profit_target, best_day_profit / consistency_frac)

    That is the interesting consequence of this whole file.  A single huge day
    raises your own bar, so the search cannot win by finding one lucky session.
    A naive fixed-barrier objective would rank exactly that strategy first.
"""

from __future__ import annotations

import enum
import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Iterable, Sequence

__all__ = [
    "Verdict",
    "EquityPoint",
    "BarrierOutcome",
    "FixedBarrierRules",
    "PropRules",
    "evaluate_fixed",
    "evaluate_prop",
    "aggregate",
    "PHat",
    "load_rules",
    "UNRANKABLE",
]


#: Fitness sentinel for an unresolved episode. "Cannot be scored", never "scored
#: badly" — a censored episode ranked at 0.0 is indistinguishable from a measured
#: failure, and an optimiser would happily prefer it to a real loss.
UNRANKABLE = -1e9


class Verdict(enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    CENSORED = "CENSORED"


@dataclass(frozen=True, slots=True)
class EquityPoint:
    """One observation of the account, in chronological order.

    `equity` includes floating P&L; `balance` is realized only. The distinction is
    load-bearing, not cosmetic: the prop floor ratchets on BALANCE and is enforced
    against EQUITY.
    """

    ts: datetime
    equity: float
    balance: float


@dataclass(frozen=True, slots=True)
class BarrierOutcome:
    verdict: Verdict
    resolved_at: datetime | None
    #: Diagnostics. REPORTED, never optimised — the objective stays pure.
    final_equity: float
    final_balance: float
    peak_equity: float
    trough_equity: float
    days_traded: int = 0
    best_day_profit: float = 0.0
    effective_target: float | None = None
    floor_at_end: float | None = None
    detail: str = ""

    @property
    def fitness(self) -> float:
        """1.0 target-first, 0.0 floor-first, UNRANKABLE if unresolved."""
        if self.verdict is Verdict.PASS:
            return 1.0
        if self.verdict is Verdict.FAIL:
            return 0.0
        return UNRANKABLE


# --------------------------------------------------------------------------- #
#  barrier_fixed — the MT5 GRW port
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class FixedBarrierRules:
    stake: float
    target_mult: float
    floor_frac: float

    @property
    def target(self) -> float:
        return self.stake * self.target_mult

    @property
    def floor(self) -> float:
        return self.stake * self.floor_frac


def evaluate_fixed(
    path: Iterable[EquityPoint], rules: FixedBarrierRules
) -> BarrierOutcome:
    """P(equity >= target BEFORE equity <= floor), on a single path.

    Barriers are tested on EQUITY including floating P&L, because ruin is an equity
    event and the target is read off open P&L. Whichever is touched first resolves
    the episode; the caller is responsible for stopping the strategy there, since
    post-resolution trading is a different experiment.
    """
    peak = trough = None
    last: EquityPoint | None = None

    for pt in path:
        peak = pt.equity if peak is None else max(peak, pt.equity)
        trough = pt.equity if trough is None else min(trough, pt.equity)
        last = pt

        if pt.equity <= rules.floor:
            return BarrierOutcome(
                Verdict.FAIL, pt.ts, pt.equity, pt.balance, peak, trough,
                detail=f"equity {pt.equity:.2f} <= floor {rules.floor:.2f}",
            )
        if pt.equity >= rules.target:
            return BarrierOutcome(
                Verdict.PASS, pt.ts, pt.equity, pt.balance, peak, trough,
                detail=f"equity {pt.equity:.2f} >= target {rules.target:.2f}",
            )

    if last is None:
        raise ValueError("empty equity path: nothing to evaluate")

    return BarrierOutcome(
        Verdict.CENSORED, None, last.equity, last.balance, peak, trough,
        detail="window ended with neither barrier touched",
    )


# --------------------------------------------------------------------------- #
#  barrier_prop — the moving floor
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class PropRules:
    """One prop firm's evaluation, as numbers.

    Every field here is a rulebook fact, not a tuning knob. Changing one changes
    the question being asked, which is a version bump and a new trial family.
    """

    firm: str
    account_size: float
    profit_target: float
    mll_offset: float
    consistency_frac: float
    min_trading_days: int
    max_contracts: int
    #: True when the floor stops ratcheting once it reaches `account_size`.
    mll_locks_at_start: bool = True
    #: True when the profit target must be satisfied on an end-of-day balance
    #: rather than touched intraday. Topstep: "reach AND MAINTAIN".
    target_on_eod_balance: bool = True
    version: str = "0.0.0"
    source: str = ""

    @property
    def initial_mll(self) -> float:
        return self.account_size - self.mll_offset

    def effective_target(self, best_day_profit: float) -> float:
        """The consistency rule, as a raised bar rather than a failure.

        `best_day / total_profit <= consistency_frac`  rearranges to
        `total_profit >= best_day / consistency_frac`, so a big day simply moves
        the target up. A non-positive best day leaves the target alone.
        """
        if best_day_profit <= 0:
            return self.profit_target
        return max(self.profit_target, best_day_profit / self.consistency_frac)


def _cme_trading_day(ts: datetime) -> date:
    """Default day boundary: the CME session rolls at 17:00 US Central.

    ASSUMED, and the caller should override it with the firm's own boundary before
    any number is logged — Topstep settles on its own clock, not the exchange's.
    Falsified by: a settled day whose P&L differs from this grouping.
    """
    d = ts.date()
    return d if ts.hour < 17 else date.fromordinal(d.toordinal() + 1)


def evaluate_prop(
    path: Sequence[EquityPoint],
    rules: PropRules,
    *,
    trading_day_of: Callable[[datetime], date] = _cme_trading_day,
) -> BarrierOutcome:
    """Run one evaluation attempt to PASS, FAIL or CENSORED.

    The loop does exactly two things per observation and one thing per day close:

        every point   test the floor against EQUITY (unrealized counts)
        every close   settle the day: ratchet the floor, update best-day,
                      then test the target against the END-OF-DAY BALANCE

    Order matters. The floor is tested first and always, because a liquidation at
    11:00 is not undone by a profitable close.
    """
    if not path:
        raise ValueError("empty equity path: nothing to evaluate")

    mll = rules.initial_mll
    mll_locked = False
    prev_eod_balance = rules.account_size
    best_day_profit = 0.0
    days_traded = 0
    peak = path[0].equity
    trough = path[0].equity

    current_day = trading_day_of(path[0].ts)
    day_open_balance = rules.account_size
    day_last: EquityPoint = path[0]
    day_touched = False

    def settle(day_end: EquityPoint) -> BarrierOutcome | None:
        """Close out a trading day. Returns an outcome only on PASS."""
        nonlocal mll, mll_locked, prev_eod_balance, best_day_profit, days_traded

        eod_balance = day_end.balance
        day_pnl = eod_balance - day_open_balance

        if day_touched:
            days_traded += 1
        best_day_profit = max(best_day_profit, day_pnl)

        # Floor ratchets on end-of-day BALANCE, never downward, and freezes once it
        # reaches the starting balance.
        if not mll_locked:
            mll = max(mll, eod_balance - rules.mll_offset)
            if rules.mll_locks_at_start and mll >= rules.account_size:
                mll = rules.account_size
                mll_locked = True

        prev_eod_balance = eod_balance

        total_profit = eod_balance - rules.account_size
        target = rules.effective_target(best_day_profit)
        if total_profit >= target and days_traded >= rules.min_trading_days:
            return BarrierOutcome(
                Verdict.PASS, day_end.ts, day_end.equity, eod_balance, peak, trough,
                days_traded=days_traded,
                best_day_profit=best_day_profit,
                effective_target=target,
                floor_at_end=mll,
                detail=(
                    f"profit {total_profit:.2f} >= effective target {target:.2f} "
                    f"(base {rules.profit_target:.2f}, best day {best_day_profit:.2f}) "
                    f"on day {days_traded}"
                ),
            )
        return None

    for pt in path:
        day = trading_day_of(pt.ts)

        if day != current_day:
            passed = settle(day_last)
            if passed is not None:
                return passed
            current_day = day
            day_open_balance = day_last.balance
            day_touched = False

        peak = max(peak, pt.equity)
        trough = min(trough, pt.equity)

        # The floor: intraday, on equity, unrealized included. Touch = liquidation.
        if pt.equity <= mll:
            return BarrierOutcome(
                Verdict.FAIL, pt.ts, pt.equity, pt.balance, peak, trough,
                days_traded=days_traded,
                best_day_profit=best_day_profit,
                effective_target=rules.effective_target(best_day_profit),
                floor_at_end=mll,
                detail=f"equity {pt.equity:.2f} <= MLL {mll:.2f} (intraday)",
            )

        if pt.balance != day_last.balance or pt.equity != pt.balance:
            day_touched = True
        day_last = pt

    # Final partial day still settles: the window ending is not a reason to ignore
    # the last session's result.
    passed = settle(day_last)
    if passed is not None:
        return passed

    return BarrierOutcome(
        Verdict.CENSORED, None, day_last.equity, day_last.balance, peak, trough,
        days_traded=days_traded,
        best_day_profit=best_day_profit,
        effective_target=rules.effective_target(best_day_profit),
        floor_at_end=mll,
        detail="window ended with neither target nor floor reached",
    )


# --------------------------------------------------------------------------- #
#  aggregation — one pass is one draw, so the estimate lives up here
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class PHat:
    p_hat: float | None
    n_pass: int
    n_fail: int
    n_censored: int
    ci_low: float | None
    ci_high: float | None
    reportable: bool
    why: str

    @property
    def n_resolved(self) -> int:
        return self.n_pass + self.n_fail


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return max(0.0, centre - half), min(1.0, centre + half)


def aggregate(
    outcomes: Iterable[BarrierOutcome],
    *,
    min_resolved: int = 20,
    max_censored_frac: float = 0.50,
) -> PHat:
    """Turn K independent episodes into an estimate, or refuse to.

    The two guards are the ones already argued for on the MT5 side:

    * below `min_resolved` draws the estimate is an anecdote with a decimal point,
      so the config is UNJUDGED — not rejected;
    * above `max_censored_frac` unresolved windows the config is idling rather
      than answering the question, and reporting `p_hat` off the minority that
      did resolve is selection on the outcome.

    The caller is responsible for the windows being INDEPENDENT and
    NON-OVERLAPPING. Overlapping windows inflate the effective sample; on the MT5
    side that cost a pooled t of +8.02 against a yearly +0.83 on the same data.
    """
    outs = list(outcomes)
    n_pass = sum(o.verdict is Verdict.PASS for o in outs)
    n_fail = sum(o.verdict is Verdict.FAIL for o in outs)
    n_cens = sum(o.verdict is Verdict.CENSORED for o in outs)
    n_res = n_pass + n_fail
    n_all = len(outs)

    if n_all == 0:
        return PHat(None, 0, 0, 0, None, None, False, "no episodes")

    cens_frac = n_cens / n_all
    if cens_frac > max_censored_frac:
        return PHat(
            None, n_pass, n_fail, n_cens, None, None, False,
            f"censored fraction {cens_frac:.2f} > {max_censored_frac:.2f}: the "
            f"config is idling, not answering the question",
        )
    if n_res < min_resolved:
        return PHat(
            None, n_pass, n_fail, n_cens, None, None, False,
            f"{n_res} resolved episodes < {min_resolved}: UNJUDGED, not rejected",
        )

    p = n_pass / n_res
    lo, hi = _wilson(n_pass, n_res)
    return PHat(p, n_pass, n_fail, n_cens, lo, hi, True, "reportable")


# --------------------------------------------------------------------------- #
#  loading — the objective is an artifact on disk, not a literal in code
# --------------------------------------------------------------------------- #


def _fingerprint(payload: dict) -> str:
    body = {k: v for k, v in payload.items() if k != "fingerprint"}
    blob = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


class UnverifiedObjective(RuntimeError):
    """Raised when an objective carries numbers nobody has read off the source.

    A rulebook figure taken from a review site is an ASSUMED value wearing the
    costume of a CITED one. It is the most dangerous kind of input here, because
    the resulting equity path looks completely normal.
    """


def load_rules(
    path: str | Path, *, allow_unverified: bool = False
) -> tuple[FixedBarrierRules | PropRules, str]:
    """Read a versioned objective JSON and return (rules, fingerprint).

    The fingerprint is what a logged result cites. Two results carrying different
    fingerprints were judged against different questions and must never be pooled,
    which is the whole reason it is returned rather than left implicit.

    A file whose `verification.blocks_use` is true raises `UnverifiedObjective`.
    `allow_unverified=True` exists only for tests of the mechanics themselves, and
    any result produced under it is not admissible.
    """
    p = Path(path)
    payload = json.loads(p.read_text(encoding="utf-8"))
    kind = payload["kind"]
    params = payload["parameters"]
    fp = _fingerprint(payload)

    verification = payload.get("verification", {})
    if verification.get("blocks_use") and not allow_unverified:
        unverified = [
            f"{k} ({v.get('status')})"
            for k, v in verification.get("fields", {}).items()
            if v.get("status") not in {"VERIFIED", "VERIFIED_WITH_AMBIGUITY"}
        ]
        raise UnverifiedObjective(
            f"{p.name} is {verification.get('status', 'UNVERIFIED')} and may not "
            f"drive a decision. Unverified fields: {', '.join(unverified) or 'unlisted'}. "
            f"{verification.get('how_to_clear', '')}"
        )

    if kind == "barrier_fixed":
        return (
            FixedBarrierRules(
                stake=float(params["stake"]),
                target_mult=float(params["target_mult"]),
                floor_frac=float(params["floor_frac"]),
            ),
            fp,
        )
    if kind == "barrier_prop":
        return (
            PropRules(
                firm=payload["firm"],
                account_size=float(params["account_size"]),
                profit_target=float(params["profit_target"]),
                mll_offset=float(params["mll_offset"]),
                consistency_frac=float(params["consistency_frac"]),
                min_trading_days=int(params["min_trading_days"]),
                max_contracts=int(params["max_contracts"]),
                mll_locks_at_start=bool(params["mll_locks_at_start"]),
                target_on_eod_balance=bool(params["target_on_eod_balance"]),
                version=payload["version"],
                source=payload.get("cite_as", str(p)),
            ),
            fp,
        )
    raise ValueError(f"unknown objective kind {kind!r} in {p}")
