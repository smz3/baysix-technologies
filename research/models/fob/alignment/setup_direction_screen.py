"""
Task 206 — FOB Setup<->Direction conditioner screen (guarded, cohort-separated).

The FIRST conditioner off the v3 awareness spec. Question: does a setup's alignment
with D1's OWN-cycle direction (Direction = D1, manual 5.1) shift continuation /
excursion? This is the honest re-examination of the -33.8pp full-stack "ghost"
(result_id 19) under the task-204 INDEPENDENCE GUARD.

Why this is NOT the full-stack screen (storyline_alignment_screen.py):
  * Full-stack alignment (every higher TF agrees) is a mathematical function of the
    setup's own lower chain -> circular -> manufactures extremes. We DON'T use it.
  * Here the conditioner is a SINGLE, structurally-independent TF: D1's own active-PBO
    direction (htf_state['D1'].dir is the RAW own-cycle standing, propagation NOT baked
    -- fob_types.mqh:236-252). D1 is anchored by D1 breaks on D1 bars, so for an M15/M5
    setup it is not a restatement of the setup's own chain.

Cohorts (spec decision 1) screened SEPARATELY -- pooling recreates the multi-population
attribution trap because M5 is the hinge (setup-TF for M5-band, VR-TF for M15-band):
    M15-M5  = cycles setup_tf=M15  (CFs on M5)
    M5-M1   = cycles setup_tf=M5   (CFs on M1)

States (Setup dir vs D1 own dir):
    aligned  -- D1 live cycle same direction as the setup
    counter  -- D1 live cycle opposite the setup
    D1-flat  -- D1 has no live cycle at the CF bar (dir == "")

EXPLORATORY, MID-PRICE (cost-free) -- NOT a tester gate. The MT5 tester stays the money
arbiter (CLAUDE.md trust rule). This only tells us whether the state is worth an MT5-net
validation / a RE-EMIT.

Usage:
    python research/models/fob/alignment/setup_direction_screen.py --run-id 18
"""
import argparse
import json
import math
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from research.code.io import tester
from storyline_alignment_screen import _resolve_run_id, _two_prop_z  # reuse guards

COHORTS = {"M15-M5": "M15", "M5-M1": "M5"}
OPP = {"BUY": "SELL", "SELL": "BUY"}


def _d1_warmup_cutoff(conn, run_id):
    """First confirmed D1 cycle (vr_time) = the moment D1's own direction is first
    definable. Before it, D1-flat is warm-up ignorance, not a real flat state."""
    row = conn.execute(
        "SELECT MIN(vr_time) FROM fob_cycles WHERE run_id=? AND setup_tf='D1' "
        "AND vr_time IS NOT NULL", (run_id,)).fetchone()
    return row[0] if row else None


def _d1_state(htf_json, direction):
    """aligned / counter / D1-flat from D1's OWN active-PBO direction."""
    try:
        d1 = (json.loads(htf_json).get("D1") or {}).get("dir", "")
    except (TypeError, json.JSONDecodeError):
        return None
    if d1 == "":
        return "D1-flat"
    return "aligned" if d1 == direction else "counter"


def _welch_t(a, b):
    """Welch t for mean(a) - mean(b)."""
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return float("nan")
    va, vb = a.var(ddof=1), b.var(ddof=1)
    se = math.sqrt(va / na + vb / nb)
    return (a.mean() - b.mean()) / se if se > 0 else float("nan")


def _bucket_row(tag, g):
    n = len(g)
    p = g["continued"].mean()
    se_p = math.sqrt(p * (1 - p) / n) if n else float("nan")
    er = g["realized_r"].mean()
    se_r = g["realized_r"].std(ddof=1) / math.sqrt(n) if n > 1 else float("nan")
    return f"{tag:>9} {n:>7} {p:>8.4f} {se_p:>7.4f} {er:>+8.3f} {se_r:>7.3f}"


def main():
    # DISABLED by migration 038 (2026-08-16): this reads fob_events/fob_zones/fob_cycles,
    # which were dropped when the ledger stopped carrying strategy-shaped tables. The same
    # payload is still on disk as Parquet — port the query to
    # fob_payload.read_fob_payload(run_id, table, setup_tf=..., cols=[...]) to revive it.
    raise SystemExit(
        "disabled: migration 038 dropped the fob_* tables. Port this screen to read "
        "Parquet via research/code/io/fob_payload.py."
    )

    ap = argparse.ArgumentParser(description="FOB Setup<->Direction conditioner screen (task 206)")
    ap.add_argument("--run-id", type=int, default=None)
    ap.add_argument("--idea-id", default="FOB-001")
    ap.add_argument("--no-warmup-cut", action="store_true")
    args = ap.parse_args()

    conn = sqlite3.connect(tester.DB_PATH)
    run_id, hdr = _resolve_run_id(conn, args.idea_id, args.run_id)
    cutoff = None if args.no_warmup_cut else _d1_warmup_cutoff(conn, run_id)

    print("=" * 84)
    print("FOB SETUP<->DIRECTION CONDITIONER SCREEN  --  EXPLORATORY | MID-PRICE | NOT A GATE")
    print(f"run_id={run_id}  idea_id={hdr[0]}  ea_v={hdr[2]}  window={hdr[3]}->{hdr[4]}")
    print(f"conditioner = D1 own-cycle dir (independence-guarded) | D1 warm-up cutoff = {cutoff or '(none)'}")
    print("=" * 84)

    q = """
        SELECT c.setup_tf AS cohort, e.direction, e.bar_time, e.htf_state, e.risk_class,
               z.continued, z.realized_r, z.mfe_r, z.mae_r, z.vr_fresh
        FROM fob_events e
        JOIN fob_zones  z ON z.zone_id  = e.zone_id  AND z.run_id = e.run_id
        JOIN fob_cycles c ON c.cycle_id = e.cycle_id AND c.run_id = e.run_id
        WHERE e.run_id = ?
          AND e.label IN ('CF','HRCF')
          AND c.setup_tf IN ('M15','M5')
          AND z.zone_valid = 1
          AND e.htf_state IS NOT NULL
          AND z.continued IS NOT NULL
    """
    df = pd.read_sql_query(q, conn, params=(run_id,))
    conn.close()

    n_raw = len(df)
    if cutoff:
        df = df[df["bar_time"] >= cutoff].copy()
    if df.empty:
        raise SystemExit(f"no eligible CF zones (raw={n_raw}, after warm-up cut=0)")
    df["state"] = df.apply(lambda r: _d1_state(r["htf_state"], r["direction"]), axis=1)
    df = df.dropna(subset=["state"])
    df["year"] = df["bar_time"].str[:4]
    print(f"\neligible CF zones: raw={n_raw}  after D1 warm-up cut={len(df)}")

    for cohort_name, stf in COHORTS.items():
        d = df[df["cohort"] == stf]
        if d.empty:
            print(f"\n### {cohort_name}: no rows"); continue
        aligned = d[d["state"] == "aligned"]
        counter = d[d["state"] == "counter"]
        flat = d[d["state"] == "D1-flat"]
        print("\n" + "=" * 84)
        print(f"### COHORT {cohort_name}  (setup_tf={stf})   n={len(d)}   "
              f"baseline cont={d['continued'].mean():.4f}  E[R]={d['realized_r'].mean():+.3f}")
        print("-" * 84)
        print(f"{'state':>9} {'n':>7} {'cont':>8} {'se':>7} {'E[R]':>8} {'se':>7}")
        for tag, g in (("aligned", aligned), ("counter", counter), ("D1-flat", flat)):
            if len(g):
                print(_bucket_row(tag, g))

        if len(aligned) and len(counter):
            z = _two_prop_z(aligned["continued"].sum(), len(aligned),
                            counter["continued"].sum(), len(counter))
            t = _welch_t(aligned["realized_r"], counter["realized_r"])
            lift = (aligned["continued"].mean() - counter["continued"].mean()) * 100
            dR = aligned["realized_r"].mean() - counter["realized_r"].mean()
            print("-" * 84)
            print(f"ALIGNED - COUNTER:  cont lift = {lift:+.1f}pp (z={z:+.2f})   "
                  f"E[R] diff = {dR:+.3f} (t={t:+.2f})")
            print(f"[ghost check] full-stack claimed aligned=-33.8pp (reversal). Guarded single-D1 "
                  f"lift here = {lift:+.1f}pp.")

        # BUY/SELL symmetry of the aligned-vs-counter contrast
        print(f"\n  -- BUY/SELL symmetry (aligned vs counter cont-lift) --")
        for dd in ("BUY", "SELL"):
            a = aligned[aligned["direction"] == dd]; c = counter[counter["direction"] == dd]
            if len(a) and len(c):
                z = _two_prop_z(a["continued"].sum(), len(a), c["continued"].sum(), len(c))
                print(f"     {dd:>4}: {(a['continued'].mean()-c['continued'].mean())*100:>+6.1f}pp "
                      f"(z={z:+.2f})  n_al={len(a)} n_ct={len(c)}")

        # per-year durability of the aligned-vs-counter continued lift
        print(f"\n  -- per-year aligned-vs-counter cont-lift (durability) --")
        for y in sorted(d["year"].unique()):
            gy = d[d["year"] == y]
            a = gy[gy["state"] == "aligned"]; c = gy[gy["state"] == "counter"]
            if len(a) and len(c):
                print(f"     {y}: {(a['continued'].mean()-c['continued'].mean())*100:>+6.1f}pp "
                      f"n_al={len(a):>5} n_ct={len(c):>5}")

    print("\n[reminder] EXPLORATORY mid-price screen -- NOT a money result. Any edge must be "
          "MT5-net validated before it counts (CLAUDE.md trust rule).")


if __name__ == "__main__":
    main()
