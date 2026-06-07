import pandas as pd
import pytest

from research.models.orb import equity_sim as es


def test_trade_pnl_usd_loss_min_lot():
    # -1R, range_w=$3, min lot 0.01 -> -$3.00 exactly (R * range_w * 100 * lot)
    assert es.trade_pnl_usd(R=-1.0, range_w=3.0, lot=0.01) == pytest.approx(-3.0)


def test_trade_pnl_usd_win_min_lot():
    # +3R, range_w=$3, min lot -> +$9.00
    assert es.trade_pnl_usd(R=3.0, range_w=3.0, lot=0.01) == pytest.approx(9.0)


def test_trade_pnl_scales_with_lot():
    assert es.trade_pnl_usd(R=1.0, range_w=5.0, lot=0.02) == pytest.approx(10.0)


def test_used_margin_tiny_at_high_leverage():
    # 0.01 lot at $3300, 1:3000 -> notional 3300, margin ~1.10
    assert es.used_margin_usd(entry_px=3300.0, lot=0.01, leverage=3000) == pytest.approx(1.10, abs=0.01)
