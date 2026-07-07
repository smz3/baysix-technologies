"""
FOB top-down storyline-confluence screen  (State-Engine measurement, task 243).

Question (Syafiq's framing): confluence is read TOP-DOWN -- "what are the higher
TFs doing, and which part of their sequence are they in?" -- and it is 2D per TF:
    dir  = that TF's OWN active-PBO direction   (independent, parent-scale)
    cf   = that TF's CF-count in its live cycle  (0=fresh PBO, N=Nth CF = sequence phase)
Both come straight from the causal htf_state snapshot stamped on each CF event
(FobBuildHtfState, fob_types.mqh:276-289 -- dir is pbo_dir, NOT a lower-derived
refresh, so it is structurally independent of the child trigger).

OWNERSHIP (confirmed w/ Syafiq 2026-07-07): the cycle is owned by the PARENT (PBO
fires on setup_tf) and TRADED by the child (VR/CF fire on setup_tf-1). So:
  * htf_state[setup_tf].dir  == the parent PBO the child CF resumes -> baked agreement,
    LOW variance (reported as a sanity check, not a conditioner).
  * htf_state[GRANDPARENT].dir  (grandparent = setup_tf + 1) == the first structurally
    INDEPENDENT context above the cycle owner -> THIS is the confluence signal.

INDEPENDENCE GUARD (task 204 / the -33.8pp ghost): we never tag against the setup's
own lower chain nor against a full-stack function of it. Grandparent own-PBO dir is
anchored by grandparent bars, so for the child it is not a restatement of its trigger.

EXPLORATORY, MID-PRICE (cost-free) -- NOT a tester gate. run_19 is git-DIRTY
(exploratory by rule) and carries realized_r only (mfe_r/mae_r NULL this emit). The
MT5 tester stays the money arbiter (CLAUDE.md trust rule); this only tells us whether
storyline confluence is worth an MT5-net validation.

Usage:
    python research/models/fob/alignment/confluence_topdown_screen.py --run-id 19
"""
import argparse
import json
import math
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from research.code.io import tester, fob_payload

# ascending TF ladder (htf_state key order) -> index lets us walk one TF UP for grandparent
LADDER = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"]
LADDER_IX = {tf: i for i, tf in enumerate(LADDER)}


def _grandparent(setup_tf: str):
    """One TF above the cycle-owning parent (= setup_tf + 1). None if off the top."""
    i = LADDER_IX.get(setup_tf)
    if i is None or i + 1 >= len(LADDER):
        return None
    return LADDER[i + 1]


def _welch_t(a: pd.Series, b: pd.Series) -> float:
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return float("nan")
    se = math.sqrt(a.var(ddof=1) / na + b.var(ddof=1) / nb)
    return (a.mean() - b.mean()) / se if se > 0 else float("nan")


def _tf_state(htf_json: str, tf: str):
    """(dir, cf) for one TF out of the htf_state JSON. dir='' => that TF has no live cycle."""
    try:
        d = (json.loads(htf_json).get(tf) or {})
    except (TypeError, json.JSONDecodeError):
        return None, None
    return d.get("dir", ""), int(d.get("cf", 0))


def _state_tag(gp_dir: str, trade_dir: str) -> str:
    if gp_dir == "":
        return "flat"          # no live grandparent cycle = no story above
    return "agree" if gp_dir == trade_dir else "counter"


def _phase_bucket(cf: int) -> str:
    if cf <= 0:
        return "cf0"           # grandparent fresh off PBO, no CF yet (most room)
    if cf == 1:
        return "cf1"
    return "cf2+"              # extended / late in its sequence


def _row(tag: str, g: pd.DataFrame) -> str:
    n = len(g)
    er = g["realized_r"].mean()
    se = g["realized_r"].std(ddof=1) / math.sqrt(n) if n > 1 else float("nan")
    cont = g["continued"].mean() if "continued" in g else float("nan")
    return f"{tag:>10} {n:>7} {er:>+8.3f} {se:>7.3f} {cont:>8.4f}"


def main():
    ap = argparse.ArgumentParser(description="FOB top-down confluence screen (task 243)")
    ap.add_argument("--run-id", type=int, default=19)
    ap.add_argument("--idea-id", default="FOB-001")
    args = ap.parse_args()

    # run header (tester_runs still holds metadata; raw rows live in Parquet post-229)
    conn = sqlite3.connect(tester.DB_PATH)
    hdr = conn.execute(
        "SELECT ea_version, git_sha, git_dirty, run_role FROM tester_runs WHERE run_id=?",
        (args.run_id,)).fetchone()
    conn.close()
    ea_v, sha, dirty, role = hdr if hdr else ("?", "?", "?", "?")

    # CF entries: htf_state+dir+setup_tf from events, outcome from zones, joined on zone_id
    ev = fob_payload.read_fob_payload(
        args.run_id, "events", cols=["zone_id", "label", "direction", "htf_state", "setup_tf"])
    ev = ev[ev["label"] == "CF"].copy()
    zo = fob_payload.read_fob_payload(
        args.run_id, "zones", cols=["zone_id", "source_label", "realized_r", "continued"])
    zo = zo[zo["source_label"] == "CF"]
    df = ev.merge(zo[["zone_id", "realized_r", "continued"]], on="zone_id", how="inner")
    df = df[df["realized_r"].notna()].copy()

    print("=" * 74)
    print("FOB TOP-DOWN CONFLUENCE SCREEN  --  EXPLORATORY | MID-PRICE | NOT A GATE")
    print(f"run_id={args.run_id}  ea_v={ea_v}  git={sha}{'-DIRTY' if dirty else ''}  role={role}")
    print(f"conditioner = GRANDPARENT (setup_tf+1) own-PBO dir x sequence-phase  |  n_CF={len(df)}")
    print("=" * 74)

    # --- sanity: parent (setup_tf) agreement should be ~baked (low variance) ---
    def _parent_agree(r):
        pdir, _ = _tf_state(r["htf_state"], r["setup_tf"])
        return None if pdir == "" else (pdir == r["direction"])
    pa = df.apply(_parent_agree, axis=1).dropna()
    if len(pa):
        print(f"[sanity] parent(setup_tf) dir == trade dir: {100*pa.mean():.1f}%  "
              f"(expect HIGH -- CF resumes the parent PBO by SOP)\n")

    df["gp"] = df["setup_tf"].map(_grandparent)
    df = df[df["gp"].notna()].copy()

    for stf in [t for t in LADDER if t in df["setup_tf"].unique()]:
        d = df[df["setup_tf"] == stf].copy()
        gp = _grandparent(stf)
        st = d["htf_state"].combine(d["direction"], lambda h, dr: _state_tag(_tf_state(h, gp)[0], dr))
        d["state"] = st
        d["gp_cf"] = d["htf_state"].map(lambda h: _tf_state(h, gp)[1])

        print("=" * 74)
        print(f"### setup_tf={stf}  (child traded = {LADDER[LADDER_IX[stf]-1] if LADDER_IX[stf] else '-'})"
              f"  grandparent={gp}   n={len(d)}   baseline E[R]={d['realized_r'].mean():+.3f}")
        print("-" * 74)
        print(f"{'state':>10} {'n':>7} {'E[R]':>8} {'se':>7} {'cont':>8}")
        agree = d[d["state"] == "agree"]; counter = d[d["state"] == "counter"]; flat = d[d["state"] == "flat"]
        for tag, g in (("agree", agree), ("counter", counter), ("flat", flat)):
            if len(g):
                print(_row(tag, g))
        if len(agree) > 1 and len(counter) > 1:
            t = _welch_t(agree["realized_r"], counter["realized_r"])
            dR = agree["realized_r"].mean() - counter["realized_r"].mean()
            print("-" * 74)
            print(f"AGREE - COUNTER:  dE[R] = {dR:+.3f}  (Welch t = {t:+.2f})")

        # phase split within agree/counter (only if the direction split showed life)
        print(f"\n  -- grandparent sequence-phase (cf) x direction --")
        print(f"  {'state.phase':>12} {'n':>7} {'E[R]':>8} {'se':>7}")
        for tag, g in (("agree", agree), ("counter", counter)):
            for ph in ("cf0", "cf1", "cf2+"):
                gg = g[g["gp_cf"].map(_phase_bucket) == ph]
                if len(gg):
                    print(f"  {tag+'.'+ph:>12} {len(gg):>7} {gg['realized_r'].mean():>+8.3f} "
                          f"{(gg['realized_r'].std(ddof=1)/math.sqrt(len(gg)) if len(gg)>1 else float('nan')):>7.3f}")

    print("\n[reminder] EXPLORATORY mid-price screen -- NOT a money result. Any edge must be "
          "MT5-net validated before it counts (CLAUDE.md trust rule).")


if __name__ == "__main__":
    main()
