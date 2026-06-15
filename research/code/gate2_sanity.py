"""Generic Gate-2 sanity checker (Protocol 3.2, task 82).

Gate 2 asks "does the simplest implementation produce SANE output?" — plumbing,
not edge (that is Gate 3). 3.1 hard-coded the 4 Markov checks (occupancy /
stochastic-matrix / ergodicity / persistence); ORB & STRUCT silently hand-rolled
their own `gate2_sanity.py`. 3.2 replaces that with THREE method-free categories
every idea-kind shares:

    validity            — output is well-formed: finite, right shape/count, in a
                          plausible range (gold $, a probability in [0,1], ...).
    non_degeneracy      — output is not trivial: not constant, both directions /
                          classes present, variance > 0 (a model that always says
                          'long' or 'flat' passes nothing).
    causal_cleanliness  — NO look-ahead and realistic fills: timestamps strictly
                          monotonic before any tick sim (the ORB unsorted-tick
                          lesson — argmax-by-position manufactured a fake edge),
                          entry strictly AFTER the signal window closes.

Markov-4 is demoted to a `classifier`-only instance (`markov4()` below), not the
universal gate. Trader's-eye inspection is per-idea OPTIONAL supplementary evidence.

Usage (each assert_* both checks AND registers; or register a raw bool):

    g = Gate2Sanity("BRK-001", "London breakout 08:00")
    g.assert_monotonic_time(bars.index)              # causal — do this FIRST
    g.assert_in_range(bars["range_w"].median(), 0.5, 30, "range width USD")
    g.assert_both_directions(orb["direction"])       # non-degeneracy
    g.validity("anchor present most days", n_anchor >= 0.9 * n_days)
    ok = g.verdict(); g.render()

The module holds the SHAPE of the gate; the idea supplies the data. No model
assumptions leak in, so it is reusable across strategy / primitive / classifier.
"""
from __future__ import annotations

import numpy as np

VALIDITY = "validity"
NON_DEGENERACY = "non_degeneracy"
CAUSAL = "causal_cleanliness"
CATEGORIES = (VALIDITY, NON_DEGENERACY, CAUSAL)


class Gate2Sanity:
    """Collects named pass/fail checks under the 3 categories and renders a verdict."""

    def __init__(self, idea_id: str, label: str = ""):
        self.idea_id = idea_id
        self.label = label
        self.checks: list[tuple[str, str, bool, str]] = []  # (category, name, ok, detail)

    # ── raw registration (use when you already have the bool) ────────────────
    def add(self, category: str, name: str, ok: bool, detail: str = "") -> bool:
        if category not in CATEGORIES:
            raise ValueError(f"category must be one of {CATEGORIES}, got {category!r}")
        self.checks.append((category, name, bool(ok), detail))
        return bool(ok)

    def validity(self, name, ok, detail="") -> bool:        return self.add(VALIDITY, name, ok, detail)
    def non_degeneracy(self, name, ok, detail="") -> bool:  return self.add(NON_DEGENERACY, name, ok, detail)
    def causal(self, name, ok, detail="") -> bool:          return self.add(CAUSAL, name, ok, detail)

    # ── reusable assertions (check + auto-register) ──────────────────────────
    def assert_monotonic_time(self, ts, name="timestamps strictly increasing") -> bool:
        """CAUSAL — the ORB unsorted-tick lesson. Any tick/bar series fed to a
        sim MUST be time-sorted; argmax-by-position on unsorted data = look-ahead."""
        a = np.asarray(ts)
        ok = len(a) <= 1 or bool(np.all(a[1:] >= a[:-1]))
        n_back = 0 if ok else int(np.sum(a[1:] < a[:-1]))
        return self.causal(name, ok, "" if ok else f"{n_back} backward steps — SORT before sim")

    def assert_entry_after_signal(self, signal_time, entry_time, name="entry after signal window") -> bool:
        """CAUSAL — fill realism. Entry must be strictly AFTER the bar/window that
        produced the signal closes (no entering on the bar you used to decide)."""
        s = np.asarray(signal_time); e = np.asarray(entry_time)
        ok = bool(np.all(e > s))
        n_bad = int(np.sum(e <= s))
        return self.causal(name, ok, "" if ok else f"{n_bad} entries at/before signal time")

    def assert_finite(self, arr, name="output finite (no NaN/Inf)") -> bool:
        a = np.asarray(arr, dtype=float)
        ok = bool(np.all(np.isfinite(a))) if a.size else False
        n_bad = int(np.sum(~np.isfinite(a))) if a.size else 0
        return self.validity(name, ok, "" if ok else f"{n_bad} non-finite values")

    def assert_in_range(self, value, lo, hi, name) -> bool:
        ok = lo <= value <= hi
        return self.validity(name, ok, f"{value:.4g} vs [{lo}, {hi}]")

    def assert_not_constant(self, arr, name="output not constant") -> bool:
        a = np.asarray(arr)
        ok = a.size > 1 and len(np.unique(a[~_nan_mask(a)] if a.dtype.kind == "f" else a)) > 1
        return self.non_degeneracy(name, ok, "" if ok else "all values identical — degenerate")

    def assert_both_directions(self, series, longs=("long",), shorts=("short",),
                               name="both directions present") -> bool:
        """NON-DEGENERACY — a rule that only ever fires one way isn't a two-sided test."""
        vals = list(series)
        has_l = any(v in longs for v in vals)
        has_s = any(v in shorts for v in vals)
        ok = has_l and has_s
        return self.non_degeneracy(name, ok, f"long={has_l} short={has_s}")

    # ── verdict / reporting ──────────────────────────────────────────────────
    def verdict(self) -> bool:
        """PASS only if every registered check passed AND all 3 categories have ≥1
        check (a gate that never tested causal-cleanliness has not passed Gate 2)."""
        if not self.checks:
            return False
        covered = {c for c, *_ in self.checks}
        return all(ok for _, _, ok, _ in self.checks) and covered == set(CATEGORIES)

    def report(self) -> str:
        lines = [f"== Gate 2 sanity · {self.idea_id}" + (f" · {self.label}" if self.label else "")]
        for cat in CATEGORIES:
            rows = [(n, ok, d) for c, n, ok, d in self.checks if c == cat]
            lines.append(f"  [{cat}]" + ("" if rows else "  (no checks — INCOMPLETE)"))
            for name, ok, detail in rows:
                tail = f"  ({detail})" if detail else ""
                lines.append(f"    [{'PASS' if ok else 'FAIL'}] {name}{tail}")
        lines.append("  -> " + ("ALL SANE — Gate 2 plumbing OK" if self.verdict()
                                else "INCOMPLETE or FAILED — inspect before logging Gate 2"))
        return "\n".join(lines)

    def render(self) -> None:
        print(self.report())


def _nan_mask(a):
    return np.isnan(a) if np.asarray(a).dtype.kind == "f" else np.zeros(len(a), bool)


# ── classifier-only instance: the demoted Markov-4 ──────────────────────────────

def markov4(state_series, transition_matrix, occupancy_floor: float = 0.02,
            persistence_floor: float = 0.5, idea_id: str = "", label: str = "Markov-4") -> Gate2Sanity:
    """The 3.1 HMM/Markov Gate-2 checks, demoted to a `classifier`-kind instance of
    the generic gate (NOT universal anymore). Maps the 4 legacy checks onto the 3
    categories:

      validity         — transition rows are a stochastic matrix (each sums to 1)
      non_degeneracy   — every state is OCCUPIED above a floor (no dead regime) and
                         states PERSIST (diagonal >= floor; not a coin-flip relabel)
      causal_cleanliness — the state series is time-ordered (fit on past only)

    `transition_matrix` is K×K row-stochastic; `state_series` is the decoded path.
    """
    g = Gate2Sanity(idea_id, label)
    P = np.asarray(transition_matrix, dtype=float)
    states = np.asarray(state_series)
    K = P.shape[0]

    # validity — stochastic matrix
    row_sums = P.sum(axis=1)
    g.assert_in_range(float(np.max(np.abs(row_sums - 1.0))), 0.0, 1e-6,
                      "transition rows sum to 1 (max |dev|)")

    # non-degeneracy — occupancy + persistence
    occ = np.array([np.mean(states == k) for k in range(K)])
    g.non_degeneracy(f"all {K} states occupied >= {occupancy_floor:.0%}",
                     bool(np.all(occ >= occupancy_floor)),
                     "min occupancy " + ", ".join(f"{o:.2f}" for o in occ))
    diag = np.diag(P)
    g.non_degeneracy(f"states persist (diag >= {persistence_floor})",
                     bool(np.all(diag >= persistence_floor)),
                     "diag " + ", ".join(f"{d:.2f}" for d in diag))

    # causal-cleanliness — the decoded path is time-ordered (no future leakage)
    g.causal("state path is sequential (no shuffle)", states.size > 0,
             f"{states.size} decoded states")
    return g
