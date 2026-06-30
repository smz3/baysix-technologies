"""
Task 192 — FOB storyline-alignment screen, re-run on FOB's OWN zones.

The 2026-06-27 alignment findings (docs/specs/2026-06-27_fob_storyline_alignment_findings.md)
were computed on tester_zones run_id 5 — BRC-CONTAMINATED, VOID for FOB. This re-runs the
same causal screen on the FOB emitter's own fob_events/fob_zones payload.

Method (causal, no look-ahead): each CF (execution-TF confirmation) carries an htf_state
snapshot {M1..MN1: {dir, cf}} captured AT its bar_time. alignment = # of higher-TF ladder
members (TFs strictly above the exec TF) whose live dir == the CF's own direction. Outcome
metrics come from the CF's 1:1 zone, measured FORWARD: continued (hit-rate proxy) and
realized_r (continuation magnitude in R). We compare full-stack-aligned vs baseline.

EXPLORATORY, MID-PRICE (cost-free) — NOT a tester gate. The MT5 tester remains the money
arbiter (CLAUDE.md MT5 trust rule). This screen only tells us whether the alignment HIT-RATE
edge survives on clean FOB zones before we spend an MT5-net validation on it.

Guards:
  * ISOLATION — asserts the run's idea_id == --idea-id (FOB-001). A screen can never silently
    grab another idea's zones cross-run (the run_id 5 contamination lesson).
  * zone_valid=1 only.
  * W1/MN1 WARM-UP — high-TF context isn't formed at the start of the sample. Cutoff = bar_time
    of the FIRST MN1 VR in the run; CF events before it are excluded (their MN1/W1 bias is
    structurally unknown, not neutral). Reported; if no MN1 VR exists (too-short slice) the
    screen runs uncut with a loud warning.

Usage:
    python research/models/fob/alignment/storyline_alignment_screen.py            # latest FOB-001 emitter run
    python research/models/fob/alignment/storyline_alignment_screen.py --run-id 18
"""
import argparse
import json
import math
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from research.code.io import tester

# TF ladder, low -> high. htf_state stores all nine.
TF_ORDER = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"]
TF_RANK = {tf: i for i, tf in enumerate(TF_ORDER)}


def _resolve_run_id(conn, idea_id, run_id):
    """Pick the run; default = newest emitter run for idea_id. Isolation-assert idea_id."""
    if run_id is None:
        row = conn.execute(
            "SELECT run_id FROM tester_runs WHERE idea_id=? AND run_role='emitter' "
            "ORDER BY run_id DESC LIMIT 1", (idea_id,)).fetchone()
        if not row:
            raise SystemExit(f"no emitter run found for idea_id={idea_id}")
        run_id = row[0]
    hdr = conn.execute(
        "SELECT idea_id, run_role, ea_version, period_start, period_end "
        "FROM tester_runs WHERE run_id=?", (run_id,)).fetchone()
    if not hdr:
        raise SystemExit(f"run_id {run_id} not found")
    if hdr[0] != idea_id:
        raise SystemExit(f"ISOLATION GUARD: run_id {run_id} is idea_id={hdr[0]!r}, "
                         f"expected {idea_id!r} — refusing to screen another idea's zones")
    return run_id, hdr


def _warmup_cutoff(conn, run_id):
    """First MN1 VR bar_time = the moment the top-of-stack bias is first defined."""
    row = conn.execute(
        "SELECT MIN(vr_time) FROM fob_cycles WHERE run_id=? AND setup_tf='MN1' "
        "AND vr_time IS NOT NULL", (run_id,)).fetchone()
    return row[0] if row else None


def _alignment(htf_json, exec_tf, direction):
    """# higher-TF ladder members (strictly above exec_tf) whose live dir == direction,
    and how many higher TFs are active (dir != '') — the denominator for 'full stack'."""
    try:
        st = json.loads(htf_json)
    except (TypeError, json.JSONDecodeError):
        return None, None
    er = TF_RANK.get(exec_tf)
    if er is None:
        return None, None
    aligned = active = 0
    for tf, rank in TF_RANK.items():
        if rank <= er:
            continue
        d = (st.get(tf) or {}).get("dir", "")
        if not d:
            continue
        active += 1
        if d == direction:
            aligned += 1
    return aligned, active


def _two_prop_z(c1, n1, c0, n0):
    """Two-proportion z for hit-rate(full) vs hit-rate(baseline)."""
    if n1 == 0 or n0 == 0:
        return float("nan")
    p1, p0 = c1 / n1, c0 / n0
    p = (c1 + c0) / (n1 + n0)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n0))
    return (p1 - p0) / se if se > 0 else float("nan")


def main():
    ap = argparse.ArgumentParser(description="FOB storyline-alignment exploratory screen (task 192)")
    ap.add_argument("--run-id", type=int, default=None, help="default = newest FOB-001 emitter run")
    ap.add_argument("--idea-id", default="FOB-001")
    ap.add_argument("--no-warmup-cut", action="store_true", help="disable the MN1 warm-up exclusion")
    args = ap.parse_args()

    conn = sqlite3.connect(tester.DB_PATH)
    run_id, hdr = _resolve_run_id(conn, args.idea_id, args.run_id)
    cutoff = None if args.no_warmup_cut else _warmup_cutoff(conn, run_id)

    print("=" * 78)
    print(f"FOB STORYLINE-ALIGNMENT SCREEN  --  EXPLORATORY | MID-PRICE | NOT A GATE")
    print(f"run_id={run_id}  idea_id={hdr[0]}  ea_v={hdr[2]}  window={hdr[3]}->{hdr[4]}")
    print(f"MN1 warm-up cutoff = {cutoff or '(none — uncut)'}")
    print("=" * 78)

    # CF/HRCF events 1:1 with their valid zones; outcome = zone.continued / realized_r.
    q = """
        SELECT e.event_tf, e.direction, e.bar_time, e.htf_state,
               z.continued, z.realized_r, z.vr_fresh
        FROM fob_events e
        JOIN fob_zones  z ON z.zone_id = e.zone_id
        WHERE e.run_id = ? AND z.run_id = ?
          AND e.label IN ('CF','HRCF')
          AND z.zone_valid = 1
          AND e.htf_state IS NOT NULL
          AND z.continued IS NOT NULL
    """
    df = pd.read_sql_query(q, conn, params=(run_id, run_id))
    conn.close()

    n_raw = len(df)
    if cutoff:
        df = df[df["bar_time"] >= cutoff].copy()
    if df.empty:
        raise SystemExit(f"no eligible CF zones (raw={n_raw}, after warm-up cut={len(df)})")

    al = df.apply(lambda r: _alignment(r["htf_state"], r["event_tf"], r["direction"]), axis=1)
    df["aligned"] = [a for a, _ in al]
    df["active"] = [n for _, n in al]
    df = df.dropna(subset=["aligned", "active"])
    df["aligned"] = df["aligned"].astype(int)
    df["active"] = df["active"].astype(int)
    # full-stack = every active higher TF agrees (and at least one is active)
    df["full"] = (df["active"] > 0) & (df["aligned"] == df["active"])
    df["year"] = df["bar_time"].str[:4]

    print(f"\neligible CF zones: raw={n_raw}  after warm-up cut={len(df)}")
    print(f"overall continued-rate = {df['continued'].mean():.4f}   "
          f"E[R] = {df['realized_r'].mean():+.3f}   n={len(df)}")

    # ── full-stack-aligned vs baseline, by exec TF ───────────────────────────
    print("\n--- full-stack-aligned vs baseline, by execution TF ---")
    print(f"{'TF':>4} {'base_cont':>10} {'full_cont':>10} {'lift_pp':>8} {'z':>6} "
          f"{'base_ER':>8} {'full_ER':>8} {'n_full':>7} {'n_base':>7}")
    order = sorted(df["event_tf"].unique(), key=lambda t: TF_RANK.get(t, 99))
    for tf in order:
        g = df[df["event_tf"] == tf]
        full, base = g[g["full"]], g[~g["full"]]
        if len(full) == 0 or len(base) == 0:
            continue
        z = _two_prop_z(full["continued"].sum(), len(full), base["continued"].sum(), len(base))
        print(f"{tf:>4} {base['continued'].mean():>10.4f} {full['continued'].mean():>10.4f} "
              f"{(full['continued'].mean()-base['continued'].mean())*100:>+8.1f} {z:>6.2f} "
              f"{base['realized_r'].mean():>+8.2f} {full['realized_r'].mean():>+8.2f} "
              f"{len(full):>7} {len(base):>7}")

    # ── BUY/SELL symmetry (aggregate over TF) ────────────────────────────────
    print("\n--- BUY/SELL split (full vs base, all TFs) ---")
    print(f"{'dir':>5} {'base_cont':>10} {'full_cont':>10} {'lift_pp':>8} {'z':>6} "
          f"{'base_ER':>8} {'full_ER':>8}")
    for d in ("BUY", "SELL"):
        g = df[df["direction"] == d]
        full, base = g[g["full"]], g[~g["full"]]
        if len(full) == 0 or len(base) == 0:
            continue
        z = _two_prop_z(full["continued"].sum(), len(full), base["continued"].sum(), len(base))
        print(f"{d:>5} {base['continued'].mean():>10.4f} {full['continued'].mean():>10.4f} "
              f"{(full['continued'].mean()-base['continued'].mean())*100:>+8.1f} {z:>6.2f} "
              f"{base['realized_r'].mean():>+8.2f} {full['realized_r'].mean():>+8.2f}")

    # ── per-year durability (hit-rate lift sign in every year) ───────────────
    print("\n--- per-year full-stack hit-rate lift (durability check) ---")
    print(f"{'year':>5} {'base_cont':>10} {'full_cont':>10} {'lift_pp':>8} {'n_full':>7}")
    for y in sorted(df["year"].unique()):
        g = df[df["year"] == y]
        full, base = g[g["full"]], g[~g["full"]]
        if len(full) == 0 or len(base) == 0:
            continue
        print(f"{y:>5} {base['continued'].mean():>10.4f} {full['continued'].mean():>10.4f} "
              f"{(full['continued'].mean()-base['continued'].mean())*100:>+8.1f} {len(full):>7}")

    print("\n[reminder] EXPLORATORY mid-price screen — NOT a money result. Any edge here must be "
          "MT5-net validated before it counts (CLAUDE.md trust rule).")


if __name__ == "__main__":
    main()
