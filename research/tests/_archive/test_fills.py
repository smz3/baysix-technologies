import numpy as np
import pytest

from research.code.arctic_io import read_tick_month
from research.code.fills import Venue

# frozen ORB-001 live config (strategy_log.get_live_config('ORB-001'))
_ANCHOR_HOUR, _N_MIN, _EOD_HOUR = 9.0, 5, 21
_LOT, _EQUITY, _RISK_CAP_PCT = 0.01, 10_000.0, 5.0
_NS_H, _NS_M, _NS_D = 3_600_000_000_000, 60_000_000_000, 86_400_000_000_000


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


def _orb_day_ea(venue, ts, bid, ask, day0):
    """Worked example: _simulate_day_ea re-ported onto fills.py. ORB owns this loop;
    the venue owns every fill. Mirrors fork_a_ea_emulation._simulate_day_ea."""
    anchor = day0 + int(_ANCHOR_HOUR * _NS_H)
    or_close = anchor + _N_MIN * _NS_M
    eod = day0 + _EOD_HOUR * _NS_H

    in_or = (ts >= anchor) & (ts < or_close)
    if not in_or.any():
        return None
    or_high = float(bid[in_or].max())
    or_low = float(bid[in_or].min())
    range_w = or_high - or_low
    if range_w <= 0:
        return None

    post = np.where((ts >= or_close) & (ts < eod))[0]
    if len(post) == 0:
        return None

    side, ei = 0, None
    for k in post:
        if bid[k] >= or_high:
            side, ei = 1, k; break
        if bid[k] <= or_low:
            side, ei = -1, k; break
    if side == 0:
        return {"range_w": range_w, "traded": False, "R": 0.0, "pnl": 0.0}

    risk = venue.risk_usd(range_w, _LOT)
    if not venue.risk_cap_ok(risk, _EQUITY, _RISK_CAP_PCT):
        return {"range_w": range_w, "traded": False, "R": 0.0, "pnl": 0.0}

    seg = np.arange(ei, post[-1] + 1)
    B, A = bid[seg], ask[seg]
    entry = venue.entry_fill(side, bid=B[0], ask=A[0])
    peak = entry
    sl = or_low if side > 0 else or_high
    exit_px = venue.stop_quote(side, bid=B[-1], ask=A[-1])  # EOD market close at watched quote

    for j in range(1, len(seg)):
        q = venue.stop_quote(side, bid=B[j], ask=A[j])
        if side > 0:
            if q > peak:
                peak = q
            want = peak - range_w
            if want > sl:
                sl = want
            if q <= sl:
                exit_px = venue.exit_fill(side, sl); break
        else:
            if q < peak:
                peak = q
            want = peak + range_w
            if want < sl:
                sl = want
            if q >= sl:
                exit_px = venue.exit_fill(side, sl); break

    pnl = venue.pnl_usd(side, entry, exit_px, _LOT)
    return {"range_w": range_w, "traded": True, "R": pnl / risk, "pnl": pnl}


def test_may2024_orb_parity_matches_fork_a():
    """PERMANENT GUARD: the fills.py re-port must reproduce Fork A's EA-faithful
    May-2024 result bit-for-bit (research/outputs/orb/fork_a/fork_a_summary.json:
    n=23, win=17.4%, sum_R=-11.86, net=-9.71). Fails loudly if fill conventions
    drift out from under the MT5 EA. Do NOT adjust the pinned targets."""
    venue = Venue.from_yaml("justmarkets")
    df = read_tick_month((2024, 5), columns=["bid", "ask"])
    ts = df["ts_utc"].values.astype("datetime64[ns]").astype(np.int64)
    mid = (df["bid"].values + df["ask"].values) * 0.5
    bid, ask = venue.synth_bid_ask(mid)          # flat 2-pip overlay (vectorized)
    day_key = ts // _NS_D

    rows = []
    for d in np.unique(day_key):
        mk = day_key == d
        r = _orb_day_ea(venue, ts[mk], bid[mk], ask[mk], int(d) * _NS_D)
        if r is not None and r.get("traded"):
            rows.append(r)

    n = len(rows)
    net = sum(r["pnl"] for r in rows)
    sum_r = sum(r["R"] for r in rows)
    win = 100.0 * sum(1 for r in rows if r["R"] > 0) / n

    assert n == 23                              # vs stored fork_a: n=23
    assert net == pytest.approx(-9.71, abs=0.05)
    assert sum_r == pytest.approx(-11.86, abs=0.05)
    assert win == pytest.approx(17.4, abs=0.1)
