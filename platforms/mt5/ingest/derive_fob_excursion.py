"""Task 246 / ingest_fob phase-2b PART B — derive per-CF-zone forward EXCURSION
(mfe_r / mae_r) for an already-emitted FOB run, PARQUET-NATIVE (the raw payload now
lives in data/fob_payload/run_<id>/, not the DB — task 229).

WHY: run_19 carries realized_r only (the +2/-1 fixed-2R-vs-1R barrier LABEL), which
truncates at resolution and is blind to how far price actually ran. Confluence's real
payoff is bigger runs, invisible in realized_r. This fills the run-distance fields so
the intra-band counter/reversion signal (task 247) can be judged on MFE, not just
hit-rate-to-target.

MODEL (EXPLORATORY mid-price, M1 high/low first-touch — NOT a money result; the MT5
tester is the arbiter):
    entry = l1, stop = l2, R = |l1 - l2|.
    Walk M1 mid bars forward from the CF entry bar_time until L2 is first TOUCHED
    intrabar (the real stop, conservative same-bar tie -> stopped) or data-end.
    mfe_r = max favorable excursion / R  (>=0 typically; <0 = never traded past entry)
    mae_r = -max adverse excursion / R   (<=0; a stopped trade reaches <= -1)
    The stop bar is INCLUDED in the excursion (matches BRC brc_lifecycle death-bar rule).
    NO target cap (that is the realized_r truncation we are escaping) and NO bar-count
    cap (FOB lifecycle is event-driven — the stop IS the event).

Idempotent: overwrites mfe_r/mae_r in data/fob_payload/run_<id>/zones.parquet in place.

Usage (long-run — launch in a new PowerShell window):
    python research/code/io/derive_fob_excursion.py --run-id 19
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


QUARANTINE = """\
QUARANTINED (task 261) — this producer has no FILL GATE and its output is invalid.

It assumes a limit fill at l1 on the CF bar unconditionally. Measured on run_19 (278,592
CF zones):
  * 39% of zones had price ALREADY PAST l1 at the CF bar -> the fill never happens, the
    stop is never reached, and the sweep runs to end-of-data. 98.8% of the mfe_r > 100
    rows are these. Max mfe_r = 32,120 R: that is the 2016-24 gold bull, not a trade.
  * 56% had price ALREADY BEYOND l2 -> stopped on bar 0, so mae_r <= -1 by construction.
  * No censoring guard: a sweep that never resolves writes a number instead of NaN.

Task 202 owns the correct rebuild: gate on an actual touch of l1 after the CF bar_time,
NaN out unfilled + unresolved zones, floor R, and use SL = l2 -/+ 0.5*band (this script
used SL = l2). Until then mfe_r/mae_r are NULL in the payload and nothing may repopulate
them. Do not "just re-run" this to get numbers.
"""


def derive_excursion(run_id: int, idea_id: str = "FOB-001") -> dict:
    raise RuntimeError(QUARANTINE)


def _derive_excursion_QUARANTINED(run_id: int, idea_id: str = "FOB-001") -> dict:
    import numpy as np
    import pandas as pd
    from numba import njit

    from research.code.io import arctic_io, fob_payload, tester

    hdr = tester.get_tester_run(run_id)
    if not hdr:
        raise SystemExit(f"run_id {run_id} not found in tester_runs")
    if hdr["idea_id"] != idea_id:
        raise SystemExit(f"ISOLATION GUARD: run_id {run_id} is idea_id={hdr['idea_id']!r}, "
                         f"expected {idea_id!r}")

    # --- CF zones (entry/stop/direction) + their CF entry bar_time from events -------
    zo = fob_payload.read_fob_payload(
        run_id, "zones", cols=["zone_id", "source_label", "direction", "l1", "l2"])
    ev = fob_payload.read_fob_payload(
        run_id, "events", cols=["zone_id", "label", "bar_time"])
    ev = ev[ev["label"] == "CF"][["zone_id", "bar_time"]]

    cf = zo[(zo["source_label"] == "CF")
            & zo["l1"].notna() & zo["l2"].notna()
            & (zo["l1"] != zo["l2"])
            & zo["direction"].isin(["BUY", "SELL"])].merge(ev, on="zone_id", how="inner")
    if cf.empty:
        print(f"[excursion] run #{run_id}: no eligible CF zones")
        return {"cf_zones": 0}

    cf = cf.sort_values("bar_time").reset_index(drop=True)
    zids = cf["zone_id"].to_numpy(np.int64)
    is_buy = (cf["direction"].to_numpy() == "BUY").astype(np.int8)
    l1 = cf["l1"].to_numpy(float)
    l2 = cf["l2"].to_numpy(float)
    R = np.abs(l1 - l2)
    entry_ts = pd.to_datetime(cf["bar_time"], utc=True)

    # --- M1 mid bars [first entry, end]; high/low drive first-touch -----------------
    bars = arctic_io.m1_bars(start=entry_ts.min(), end=None, columns=["high", "low"])
    bt = bars.index.values.astype("datetime64[ns]")
    highs = bars["high"].to_numpy(float)
    lows = bars["low"].to_numpy(float)
    start_idx = np.searchsorted(bt, entry_ts.values.astype("datetime64[ns]"), side="left")

    @njit(cache=True)
    def _sweep(start_idx, is_buy, entry, stop, R, highs, lows):
        n = start_idx.shape[0]
        nb = highs.shape[0]
        mfe = np.full(n, np.nan)
        mae = np.full(n, np.nan)
        for k in range(n):
            i0 = start_idx[k]
            if i0 >= nb:
                continue
            best_fav = -1.0e18   # favorable excursion in price (can go negative)
            worst_adv = -1.0e18  # adverse excursion in price (>=0 once past entry)
            for i in range(i0, nb):
                hi = highs[i]
                lo = lows[i]
                if is_buy[k] == 1:
                    fav = hi - entry[k]
                    adv = entry[k] - lo
                    hit_stop = lo <= stop[k]
                else:
                    fav = entry[k] - lo
                    adv = hi - entry[k]
                    hit_stop = hi >= stop[k]
                if fav > best_fav:
                    best_fav = fav
                if adv > worst_adv:
                    worst_adv = adv
                if hit_stop:      # stop bar included, then done
                    break
            mfe[k] = best_fav / R[k]
            mae[k] = -worst_adv / R[k]
        return mfe, mae

    mfe, mae = _sweep(start_idx, is_buy, l1, l2, R, highs, lows)

    # --- write mfe_r/mae_r back into the zones parquet (idempotent, in place) --------
    full = pd.read_parquet(fob_payload.parquet_path(run_id, "zones"))
    m = dict(zip(zids.tolist(), mfe.tolist()))
    a = dict(zip(zids.tolist(), mae.tolist()))
    full["mfe_r"] = full["zone_id"].map(m).astype(float)
    full["mae_r"] = full["zone_id"].map(a).astype(float)
    full.to_parquet(fob_payload.parquet_path(run_id, "zones"), index=False)

    n = len(zids)
    print(f"[excursion] run #{run_id}: {n} CF zones -> "
          f"mfe_r mean={np.nanmean(mfe):+.3f} med={np.nanmedian(mfe):+.3f}  "
          f"mae_r mean={np.nanmean(mae):+.3f} med={np.nanmedian(mae):+.3f}")
    return {"cf_zones": n,
            "mfe_mean": float(np.nanmean(mfe)), "mae_mean": float(np.nanmean(mae))}


def main():
    ap = argparse.ArgumentParser(description="FOB excursion derive (task 246, phase-2b PART B)")
    ap.add_argument("--run-id", type=int, required=True)
    ap.add_argument("--idea-id", default="FOB-001")
    ap.add_argument("--done-sentinel", default=None,
                    help="touch this path on success (long-run completion signal)")
    args = ap.parse_args()

    out = derive_excursion(args.run_id, args.idea_id)
    print(f"=== excursion done: run #{args.run_id} === {out}")
    if args.done_sentinel:
        Path(args.done_sentinel).write_text("done\n", encoding="utf-8")


if __name__ == "__main__":
    main()
