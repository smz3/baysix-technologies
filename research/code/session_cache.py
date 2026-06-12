"""
session_cache.py — RETIRED 2026-06-12 (task 51).

WHY RETIRED
    This module existed only because the source tick parquet was a 24GB unsorted
    tree that was slow to re-scan for every ORB variant. The canonical tick store
    is now a SORTED, seal-enforced ArcticDB ([research/code/arctic_io.py]) with
    native, fast date-range reads — so a pre-sliced parquet copy buys nothing and
    re-introduces a second on-disk source to drift. The old session parquet
    (data/parquet/session) is quarantined/deleted.

    Crucially, the old cache inherited the source's UNSORTED order — the exact
    look-ahead vector ([[orb_unsorted_tick_lookahead]]). Arctic is sorted at the
    store, so reads are time-ordered by construction.

COMPAT SHIM
    The old names still resolve so nothing import-breaks, but they now read Arctic:
        session_files(year_months)  -> arctic_io.tick_months(year_months)
        read_session(ym, columns)   -> arctic_io.read_tick_month(ym, columns)
    New code should import from arctic_io directly. `build`/`verify` are gone —
    use research/code/arctic_verify.py for store integrity.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
from research.code.arctic_io import tick_months, read_tick_month  # noqa: E402

# Back-compat aliases (old call sites) -------------------------------------
session_files = tick_months          # session_files(year_months) -> [(y, m), ...]
read_session = read_tick_month       # read_session(ym, columns=...) -> sorted df


def _retired(*_a, **_k):
    raise RuntimeError(
        "session_cache.build/verify are RETIRED (task 51). The tick store is "
        "ArcticDB now — there is no parquet cache to build. For store integrity "
        "run: python research/code/arctic_verify.py")


build_session_cache = verify = _retired


if __name__ == "__main__":
    _retired()
