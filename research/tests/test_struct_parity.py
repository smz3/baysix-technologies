"""
test_struct_parity.py — drift guard for STRUCT-001's decoupled primitives.

STRUCT-001 owns its own swing detector (detectors.py) + structural types
(structures.py), forked from the parity-audited b2b engine so the struct filing
system stands alone. This test is the tripwire: it asserts struct's swing
detector still produces IDENTICAL swings to the b2b engine on real D1 bars. If
either side is edited and they diverge, this fails — the fork cannot silently
drift from the audited ground truth.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
STRUCT = REPO / "research" / "models" / "struct" / "struct001"
sys.path.insert(0, str(STRUCT))
sys.path.insert(0, str(REPO / "b2b"))
sys.path.insert(0, str(REPO / "research" / "code"))


def _d1():
    import arctic_io as aio
    d = aio.daily_bars().reset_index()
    d.columns = [c.lower() for c in d.columns]
    return d.rename(columns={"date": "time"})[["time", "open", "high", "low", "close"]]


@pytest.mark.parametrize("window", [3, 5, 7])
def test_struct_swings_match_b2b(window):
    """struct detect_swings == b2b detect_swings, field-for-field, at each window."""
    pytest.importorskip("arcticdb")
    from detectors import detect_swings as struct_detect          # struct-owned
    from structures import DetectionConfig as StructCfg
    from sigma_core.b2b.detectors.swing_points import detect_swings as b2b_detect
    from sigma_core.b2b.models.structures import DetectionConfig as B2bCfg

    df = _d1()
    s_sw = struct_detect(df, StructCfg(swing_window=window))
    b_sw = b2b_detect(df, B2bCfg(swing_window=window))

    assert len(s_sw) == len(b_sw), f"swing count differs at window={window}"
    for a, b in zip(s_sw, b_sw):
        assert a.bar_index == b.bar_index
        assert a.time == b.time
        assert a.price == b.price
        assert a.close_price == b.close_price
        assert a.type.name == b.type.name      # compare by name (distinct enum classes)
