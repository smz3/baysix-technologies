import pytest
from research.code.fills import Venue


def test_from_yaml_loads_jm_pro_constants():
    v = Venue.from_yaml("justmarkets")
    assert v.venue_id == "just_markets_mt5"
    assert v.half_spread == pytest.approx(0.10)     # 2-pip JM-Pro full $0.20 / 2
    assert v.contract_size == pytest.approx(100.0)  # oz per lot
    assert v.min_lot == pytest.approx(0.01)
    assert v.lot_step == pytest.approx(0.01)
    assert v.commission_per_lot_side == pytest.approx(0.0)
    assert v.swap_long == pytest.approx(0.0)
    assert v.swap_short == pytest.approx(0.0)


def _venue():
    return Venue.from_yaml("justmarkets")


def test_synth_bid_ask_flat_overlay():
    bid, ask = _venue().synth_bid_ask(2000.0)
    assert bid == pytest.approx(1999.90)
    assert ask == pytest.approx(2000.10)


def test_entry_fill_long_buys_ask_short_sells_bid():
    v = _venue()
    assert v.entry_fill(+1, bid=1999.90, ask=2000.10) == pytest.approx(2000.10)
    assert v.entry_fill(-1, bid=1999.90, ask=2000.10) == pytest.approx(1999.90)


def test_stop_quote_long_watches_bid_short_watches_ask():
    v = _venue()
    assert v.stop_quote(+1, bid=1999.90, ask=2000.10) == pytest.approx(1999.90)
    assert v.stop_quote(-1, bid=1999.90, ask=2000.10) == pytest.approx(2000.10)


def test_exit_fill_is_the_level():
    assert _venue().exit_fill(+1, level=1995.0) == pytest.approx(1995.0)


def test_pnl_usd_signed_by_side():
    v = _venue()
    # long +$3 move, 0.01 lot -> (2003-2000)*100*0.01 = +3.00
    assert v.pnl_usd(+1, entry=2000.0, exit=2003.0, lot=0.01) == pytest.approx(3.0)
    # short profits when price falls
    assert v.pnl_usd(-1, entry=2000.0, exit=1997.0, lot=0.01) == pytest.approx(3.0)


def test_risk_usd_is_stop_distance_times_contract_times_lot():
    # $3 stop distance, 0.01 lot -> 3*100*0.01 = $3.00
    assert _venue().risk_usd(stop_distance=3.0, lot=0.01) == pytest.approx(3.0)


def test_risk_cap_ok():
    v = _venue()
    # $0.50 risk on $50 equity = 1% <= 5% cap -> ok
    assert v.risk_cap_ok(risk_usd=0.50, equity=50.0, cap_pct=5.0) is True
    # $5 risk on $50 = 10% > 5% -> not ok
    assert v.risk_cap_ok(risk_usd=5.0, equity=50.0, cap_pct=5.0) is False
    # cap disabled (<=0) -> always ok
    assert v.risk_cap_ok(risk_usd=999.0, equity=50.0, cap_pct=0.0) is True
