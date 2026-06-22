"""
ORB-001 HONEST-EDGE survival re-run (Monte Carlo).

The Gate-6 OOS dollar run used the REALIZED OOS edge (+0.88R), which is INFLATED:
gold doubling shrank the fixed spread drag and a trend regime flattered the 3R
bet. The honest FORWARD edge is the IS expectancy +0.31R (N=5, frozen config,
from gate6 IS_REF).

Edge inflation manifests as an elevated WIN RATE (the 3R target hit more often;
recall the JM spread itself is modelled as a win-rate drag, not a payoff cut).
So we de-rate to the honest edge by converting the *excess* winners (+3R) back
into -1R stop-outs, at random, via Monte Carlo — preserving the REAL OOS range_w
sequence (true current-price dollar risk) and the real trade count. This answers
the question that actually matters for a live $50 account: does it survive and
grow at the HONEST edge, not the regime-flattered one?

Method, per MC path:
  1. take the 522 real OOS trades (real range_w, real outcomes)
  2. randomly flip k winning (+3R) trades to losers (-1R) so E[R] -> target (0.31)
  3. walk $50 at min-lot under the 5% survival cap (the Mode-A winner)
  4. record terminal equity, max drawdown, blew_up

Report: median / p5 / p95 terminal equity, P(blow-up), median max DD over N paths.
Also writes a structured JSON result + a terminal-equity histogram + a tearsheet
for the median path, to research/outputs/orb/.

    python research/models/orb/equity_sim_honest.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from research.models.orb.orb001.equity_sim import (
    simulate_equity, load_oos_trades, daily_returns, MIN_LOT,
)

TARGET_ER = 0.31      # honest forward edge = IS E[R] at N=5 (gate6 IS_REF: 0.3114)
SURVIVAL_CAP = 5.0    # %-of-equity skip-filter — the Mode-A winner
START = 50.0
N_PATHS = 1000
WIN_R = 3.0
LOSS_R = -1.0
SEED = 42


def n_flips_to_target(trades: pd.DataFrame, target_er: float) -> int:
    """How many +3R winners to convert to -1R losers to hit target E[R].
    Each flip lowers the R-sum by (WIN_R - LOSS_R) = 4."""
    n = len(trades)
    cur_sum = float(trades["R"].sum())
    target_sum = target_er * n
    reduction = cur_sum - target_sum
    k = int(round(reduction / (WIN_R - LOSS_R)))
    return max(0, k)


def derate_path(trades: pd.DataFrame, k: int, win_idx: np.ndarray,
                rng: np.random.Generator) -> pd.DataFrame:
    """Return a copy of trades with k randomly-chosen winners flipped to -1R."""
    df = trades.copy()
    if k > 0:
        flip = rng.choice(win_idx, size=min(k, len(win_idx)), replace=False)
        df.loc[flip, "R"] = LOSS_R
        df.loc[flip, "outcome"] = "stop"
    return df


def monte_carlo_honest(trades: pd.DataFrame, target_er: float = TARGET_ER,
                       n_paths: int = N_PATHS, cap: float = SURVIVAL_CAP,
                       start: float = START, seed: int = SEED) -> dict:
    """Run N de-rated paths; return per-path arrays + the chosen seeds."""
    from tqdm import tqdm

    win_idx = trades.index[trades["R"] == WIN_R].to_numpy()
    k = n_flips_to_target(trades, target_er)

    # sanity block (RESEARCH_CODE_PROTOCOL rule 5)
    n = len(trades)
    print("-" * 84)
    print(f"SANITY  n_trades={n}  realized E[R]={trades['R'].mean():+.4f}  "
          f"target E[R]={target_er:+.4f}")
    print(f"        winners(+3R)={len(win_idx)}  flips needed k={k}  "
          f"-> win-rate {len(win_idx)/n:.1%} -> {(len(win_idx)-k)/n:.1%}")
    print(f"        paths={n_paths}  cap={cap}%  start=${start:.0f}")
    print("-" * 84)
    if k > len(win_idx):
        print(f"[warn] k={k} exceeds winners={len(win_idx)} — target unreachable by "
              f"flipping wins alone; flipping all winners.")

    terminals, maxdds, blowups, seeds = [], [], [], []
    base = np.random.SeedSequence(seed)
    child_seeds = base.spawn(n_paths)
    for i in tqdm(range(n_paths), desc="honest MC"):
        rng = np.random.default_rng(child_seeds[i])
        df = derate_path(trades, k, win_idx, rng)
        s = simulate_equity(df, start=start, risk_cap_pct=cap)["summary"]
        terminals.append(s["terminal_equity"])
        maxdds.append(s["max_drawdown_pct"])
        blowups.append(s["blew_up"])
        seeds.append(int(child_seeds[i].generate_state(1)[0]))
    return {
        "terminals": np.array(terminals), "maxdds": np.array(maxdds),
        "blowups": np.array(blowups), "child_seeds": child_seeds,
        "k": k, "win_idx": win_idx,
    }


def main() -> None:
    out_dir = Path(__file__).resolve().parents[4] / "research" / "outputs" / "orb"
    out_dir.mkdir(parents=True, exist_ok=True)
    print("=" * 84)
    print("ORB-001 HONEST-EDGE SURVIVAL — Monte Carlo (de-rated to IS +0.31R, 5% cap)")
    print("=" * 84)

    trades = load_oos_trades().reset_index(drop=True)
    print(f"OOS trades: {len(trades)}  ({trades['date'].min()} -> {trades['date'].max()})")

    mc = monte_carlo_honest(trades)
    term = mc["terminals"]
    p5, p50, p95 = np.percentile(term, [5, 50, 95])
    p_blow = float(mc["blowups"].mean()) * 100.0
    med_dd = float(np.median(mc["maxdds"]))

    print("\n===== HONEST FORWARD RESULT (de-rated +0.31R, $50, 5% cap) =====")
    print(f"  terminal equity   median ${p50:,.2f}   p5 ${p5:,.2f}   p95 ${p95:,.2f}")
    print(f"  P(blow-up)        {p_blow:.1f}%   (of {len(term)} paths)")
    print(f"  median max DD     {med_dd:.1f}%")
    print(f"  vs inflated OOS   ${2473.69:,.2f} (no-cap) / ${2542.42:,.2f} (5% cap)")

    # median-path tearsheet + histogram
    med_i = int(np.argsort(term)[len(term) // 2])
    rng = np.random.default_rng(mc["child_seeds"][med_i])
    med_df = derate_path(trades, mc["k"], mc["win_idx"], rng)
    med_out = simulate_equity(med_df, start=START, risk_cap_pct=SURVIVAL_CAP)

    import plotly.graph_objects as go
    fig = go.Figure(go.Histogram(x=term, nbinsx=50))
    fig.add_vline(x=p50, line_dash="dash", annotation_text=f"median ${p50:,.0f}")
    fig.add_vline(x=START, line_dash="dot", line_color="red",
                  annotation_text="start $50")
    fig.update_layout(title="ORB-001 honest-edge terminal equity — 1000 MC paths "
                            "($50, IS +0.31R, 5% cap)",
                      xaxis_title="terminal equity ($)", yaxis_title="paths")
    fig.write_html(str(out_dir / "orb001_honest_terminal_hist.html"))

    try:
        import quantstats as qs
        rets = daily_returns(med_out["curve"], START)
        qs.reports.html(rets, output=str(out_dir / "orb001_honest_median_tearsheet.html"),
                        title="ORB-001 honest-edge median path ($50, IS +0.31R, 5% cap)")
    except Exception as e:
        print(f"[warn] quantstats tearsheet skipped: {e}")

    # structured JSON result (shared source of truth — infra backlog item)
    result = {
        "model": "ORB-001", "analysis": "honest_edge_survival_mc",
        "target_ER": TARGET_ER, "survival_cap_pct": SURVIVAL_CAP,
        "start_usd": START, "n_paths": N_PATHS, "n_trades": int(len(trades)),
        "flips_k": int(mc["k"]),
        "terminal_median": float(p50), "terminal_p5": float(p5),
        "terminal_p95": float(p95),
        "p_blowup_pct": p_blow, "median_max_dd_pct": med_dd,
        "data_start": str(trades["date"].min()), "data_end": str(trades["date"].max()),
    }
    (out_dir / "orb001_honest_survival.json").write_text(json.dumps(result, indent=2))

    verdict = ("SURVIVES" if p_blow < 5 else
               "FRAGILE" if p_blow < 25 else "FAILS")
    print(f"\nVERDICT (honest edge): $50 {verdict} — P(blow-up) {p_blow:.1f}%, "
          f"median ${p50:,.0f}")
    print(f"outputs -> {out_dir}")


if __name__ == "__main__":
    main()
