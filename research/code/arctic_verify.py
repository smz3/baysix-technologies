"""
arctic_verify.py — post-migration acceptance check. Fresh process (proves the store
persists), exercises the read adapter end-to-end. Firewall: only counts / timestamps /
bools reach stdout — never tick rows.

Checks:
  1. store_info: metadata present, rows_written == parquet ground truth.
  2. is_ticks(one IS day): non-empty, monotonic, max < seal.
  3. oos_ticks(one OOS day): non-empty, monotonic, min >= seal.
  4. read_ticks(full, no allow_oos): MUST raise PermissionError (seal guard works).
  5. global span: first/last timestamp of the symbol.
"""
from __future__ import annotations

import sys

import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import arctic_io as aio  # noqa: E402

EXPECTED_TICKS = 511_145_204
checks: list[tuple[str, bool]] = []


def _check(name: str, cond: bool, extra: str = "") -> None:
    checks.append((name, bool(cond)))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}{('  — ' + extra) if extra else ''}")


print("=" * 64)
print("ARCTICDB MIGRATION — ACCEPTANCE CHECK")
print("=" * 64)

# 1. metadata + row count
info = aio.store_info()
meta = info["metadata"] or {}
rows = meta.get("rows_written")
print(f"store version={info['version']}  seal={aio.seal_date().date()}  rows_written={rows:,}" if rows else meta)
_check("row count == parquet ground truth", rows == EXPECTED_TICKS, f"{rows:,} vs {EXPECTED_TICKS:,}")

seal = aio.seal_date()

# 2. IS day read
is_day = aio.is_ticks("2023-06-01", "2023-06-01 23:59:59", columns=["bid", "ask"])
_check("is_ticks non-empty", len(is_day) > 0, f"rows={len(is_day):,}")
_check("is_ticks monotonic", is_day.index.is_monotonic_increasing)
_check("is_ticks stays < seal", (is_day.index.max() < seal))

# 3. OOS day read
oos_day = aio.oos_ticks("2024-06-03", "2024-06-03 23:59:59", columns=["bid", "ask"])
_check("oos_ticks non-empty", len(oos_day) > 0, f"rows={len(oos_day):,}")
_check("oos_ticks monotonic", oos_day.index.is_monotonic_increasing)
_check("oos_ticks stays >= seal", (oos_day.index.min() >= seal))

# 4. seal guard must block a full/unscoped read
try:
    aio.read_ticks()  # no allow_oos -> should raise
    _check("seal guard blocks unscoped read", False, "did NOT raise")
except PermissionError:
    _check("seal guard blocks unscoped read", True, "PermissionError raised as expected")

# 5. global span (allow_oos to see the whole thing)
full_head = aio.read_ticks(end=None, allow_oos=True, columns=["bid"])
first, last = full_head.index.min(), full_head.index.max()
_check("global index monotonic", full_head.index.is_monotonic_increasing, f"[{first} .. {last}]")
_check("global row count matches", len(full_head) == EXPECTED_TICKS, f"{len(full_head):,}")

ok = all(c for _, c in checks)
print("=" * 64)
print(f"VERDICT: {'PASS — store accepted, adapter + seal verified.' if ok else 'FAIL — see above.'}")
print("=" * 64)
sys.exit(0 if ok else 1)
