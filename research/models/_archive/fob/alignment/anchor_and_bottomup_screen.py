"""
FOB confluence — the DECISIVE two-part screen (task 243).

Part A (mirage test): re-tag low-TF setups against a NON-ADJACENT, structurally
independent anchor (D1 = Direction, W1 = Bias per manual 5.1) instead of the adjacent
grandparent. If the giant "counter" edge collapses to ~0 here, the adjacent-grandparent
result (confluence_topdown_screen.py: counter +0.75R, t=-128) is confirmed VR-nesting
coupling, not alpha. Split by vr_fresh (fresh=layer-in retrace vs structured=ride).

Part B (bottom-up LOCATION proxy): for higher-TF setups, condition NOT on direction
(circular) but on a LOWER TF's sequence-PHASE (cf-count = how mature the micro move is)
-> "when I take this setup, is the micro TF fresh (room) or extended (late)?" This is the
honest bottom-up form Syafiq asked for: the low TF as a timing/location lens, not a
direction vote.

EXPLORATORY, MID-PRICE (cost-free), run_19 (git-DIRTY, realized_r only). NOT a gate.
"""
import argparse
import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from research.code.io import fob_payload
from confluence_topdown_screen import _tf_state, _welch_t, LADDER, LADDER_IX


def _load(run_id):
    ev = fob_payload.read_fob_payload(
        run_id, "events", cols=["zone_id", "label", "direction", "htf_state", "setup_tf"])
    ev = ev[ev["label"] == "CF"].copy()
    zo = fob_payload.read_fob_payload(
        run_id, "zones", cols=["zone_id", "source_label", "realized_r", "continued", "vr_fresh"])
    zo = zo[zo["source_label"] == "CF"]
    df = ev.merge(zo[["zone_id", "realized_r", "continued", "vr_fresh"]], on="zone_id", how="inner")
    return df[df["realized_r"].notna()].copy()


def _er(g):
    n = len(g)
    se = g["realized_r"].std(ddof=1) / math.sqrt(n) if n > 1 else float("nan")
    return f"{n:>7} {g['realized_r'].mean():>+8.3f} {se:>7.3f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", type=int, default=19)
    args = ap.parse_args()
    df = _load(args.run_id)

    print("=" * 78)
    print("PART A — NON-ADJACENT ANCHOR (mirage test)  |  EXPLORATORY MID-PRICE, NOT A GATE")
    print("  independent anchor dir vs trade dir; adjacent-grandparent gave counter +0.75R")
    print("=" * 78)
    for stf, anchors in (("M5", ["D1", "W1"]), ("M15", ["D1", "W1"]), ("M30", ["D1", "W1"])):
        d = df[df["setup_tf"] == stf]
        if d.empty:
            continue
        print(f"\n### setup_tf={stf}   n={len(d)}   baseline E[R]={d['realized_r'].mean():+.3f}")
        for anc in anchors:
            d2 = d.copy()
            d2["adir"] = d2["htf_state"].map(lambda h: _tf_state(h, anc)[0])
            agree = d2[(d2["adir"] != "") & (d2["adir"] == d2["direction"])]
            counter = d2[(d2["adir"] != "") & (d2["adir"] != d2["direction"])]
            flat = d2[d2["adir"] == ""]
            t = _welch_t(agree["realized_r"], counter["realized_r"]) if len(agree) > 1 and len(counter) > 1 else float("nan")
            dR = (agree["realized_r"].mean() - counter["realized_r"].mean()) if len(agree) and len(counter) else float("nan")
            print(f"  anchor={anc}:  agree[{_er(agree)}]  counter[{_er(counter)}]  flat[{_er(flat)}]")
            print(f"            AGREE-COUNTER dE[R]={dR:+.3f}  (t={t:+.2f})   <- ~0 => mirage confirmed")
        # vr_fresh control (is 'counter' just picking retrace/fresh legs?)
        for anc in anchors[:1]:
            d2 = d.copy()
            d2["adir"] = d2["htf_state"].map(lambda h: _tf_state(h, anc)[0])
            for vf, lab in ((1, "vr_fresh=1(retrace)"), (0, "vr_fresh=0(structured)")):
                dv = d2[d2["vr_fresh"] == vf]
                ag = dv[(dv["adir"] != "") & (dv["adir"] == dv["direction"])]
                ct = dv[(dv["adir"] != "") & (dv["adir"] != dv["direction"])]
                if len(ag) and len(ct):
                    print(f"      [{anc} | {lab}]  agree E[R]={ag['realized_r'].mean():+.3f}(n={len(ag)})  "
                          f"counter E[R]={ct['realized_r'].mean():+.3f}(n={len(ct)})")

    print("\n" + "=" * 78)
    print("PART B — BOTTOM-UP LOCATION PROXY (lower-TF sequence phase, NOT direction)")
    print("  'is the micro TF fresh (room) or extended (late)?'  cf0=fresh cf1=mid cf2+=late")
    print("=" * 78)
    # for each higher setup, use a micro TF two below the child as the locator
    for stf, micro in (("H1", "M5"), ("H4", "M15"), ("D1", "H1")):
        d = df[df["setup_tf"] == stf]
        if d.empty:
            continue
        d = d.copy()
        d["mcf"] = d["htf_state"].map(lambda h: _tf_state(h, micro)[1])
        d["mdir"] = d["htf_state"].map(lambda h: _tf_state(h, micro)[0])
        print(f"\n### setup_tf={stf}  micro-locator={micro}   n={len(d)}   baseline E[R]={d['realized_r'].mean():+.3f}")
        for lab, mask in (("fresh cf0", d["mcf"] == 0), ("mid cf1", d["mcf"] == 1), ("late cf2+", d["mcf"] >= 2)):
            g = d[mask & (d["mdir"] != "")]
            gflat = d[mask & (d["mdir"] == "")]
            if len(g):
                print(f"  {micro} {lab:>10} (live): {_er(g)}")
            if len(gflat):
                print(f"  {micro} {lab:>10} (flat): {_er(gflat)}")

    print("\n[reminder] EXPLORATORY mid-price — NOT a money result. MT5-net is the arbiter.")


if __name__ == "__main__":
    main()
