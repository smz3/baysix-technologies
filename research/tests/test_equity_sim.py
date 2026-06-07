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


def _df(rows):
    # rows: list of (R, range_w, entry_px, date)
    return pd.DataFrame(
        [{"R": r, "range_w": w, "entry_px": p, "date": d} for r, w, p, d in rows]
    )


def test_walk_simple_growth():
    # two +3R wins, range_w=$1, min lot -> +$3 each -> $50 -> $56
    df = _df([(3.0, 1.0, 2000.0, "2024-05-02"), (3.0, 1.0, 2000.0, "2024-05-03")])
    out = es.simulate_equity(df, start=50.0)
    assert out["summary"]["terminal_equity"] == pytest.approx(56.0)
    assert out["summary"]["blew_up"] is False
    assert out["summary"]["n_taken"] == 2


def test_walk_ruin_on_loss_string():
    # range_w=$30, -1R each -> -$30/trade; $50 -> $20 -> blow up (can't take 3rd)
    df = _df([(-1.0, 30.0, 2000.0, f"2024-05-0{i}") for i in range(2, 6)])
    out = es.simulate_equity(df, start=50.0)
    assert out["summary"]["blew_up"] is True
    assert out["summary"]["terminal_equity"] < 50.0


def test_survival_filter_skips_oversized_risk():
    # range_w=$30 -> risk $30 = 60% of $50; cap 10% -> skip every trade
    df = _df([(3.0, 30.0, 2000.0, "2024-05-02")])
    out = es.simulate_equity(df, start=50.0, risk_cap_pct=10.0)
    assert out["summary"]["n_taken"] == 0
    assert out["summary"]["n_skipped"] == 1
    assert out["summary"]["terminal_equity"] == pytest.approx(50.0)
