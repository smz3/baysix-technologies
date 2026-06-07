"""
HMM-001 Gate 3 — Does the dumb 5%/20-day rule have edge, raw and after costs?

Steps 8-9 of the Hedge Fund Method:
  Step 8  signal = P(Bull_{t+1}) - P(Bear_{t+1})  ->  long if >0, short if <0
  Step 9  strict walk-forward: rebuild M from data[0:t] ONLY before trading t+1

Cost model: TCM-001 (brokers/justmarkets.yaml) — Pro account, 2.0 pip spread,
no commission. Half-spread = 1 pip = 0.10 in price per unit of turnover.

Pass (research_protocol.md Gate 3): raw edge > 0 AND raw t-stat > 1.0.
Net edge logged separately (cost_adjusted=1). Does NOT auto-kill on fail —
blocks and defers the kill decision to a human.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parents[2] / "code"))
from pipeline import get_gates, log_result, open_gate, pass_gate, block_gate
from markov_baseline import load_and_label, STATES, S2I

# ── Cost model (TCM-001) ──────────────────────────────────────────────────────
SPREAD_PIPS    = 2.0
PIP_PRICE      = 0.10                       # 1 pip = 0.10 in XAUUSD price
HALF_SPREAD_PX = (SPREAD_PIPS / 2) * PIP_PRICE   # cost per unit |Δpos| = 1 pip = 0.10

MIN_TRAIN = 252        # ~1yr of labels before the first trade (matrix stability)
BULL, SIDE, BEAR = S2I["Bull"], S2I["Sideways"], S2I["Bear"]


def walk_forward(close: pd.Series, labels: pd.Series):
    """Strict walk-forward. Returns a DataFrame indexed by trade date."""
    L      = labels.map(S2I).values                      # int state per day
    px     = close.values
    ret    = close.pct_change().values                   # ret[t] = close[t]/close[t-1]-1
    dates  = labels.index
    N      = len(L)

    counts = np.zeros((3, 3))
    rows   = []
    prev_pos = 0.0

    # i indexes the DECISION day. We add the transition INTO day i, then trade i->i+1.
    for i in tqdm(range(1, N - 1), desc="walk-forward"):
        counts[L[i - 1], L[i]] += 1                      # only data through day i

        if i < MIN_TRAIN:
            continue

        row = counts[L[i]]
        if row.sum() == 0:
            signal = 0.0
        else:
            p = row / row.sum()
            signal = p[BULL] - p[BEAR]                   # Step 8

        pos       = float(np.sign(signal))               # directional dumb rule
        fwd_ret   = ret[i + 1]                            # realised t -> t+1
        gross     = pos * fwd_ret
        turnover  = abs(pos - prev_pos)
        cost      = turnover * HALF_SPREAD_PX / px[i]     # return-space cost
        net       = gross - cost
        prev_pos  = pos

        rows.append({
            "date": dates[i + 1], "state": STATES[L[i]], "signal": signal,
            "pos": pos, "fwd_ret": fwd_ret, "gross": gross,
            "turnover": turnover, "cost": cost, "net": net,
        })

    return pd.DataFrame(rows).set_index("date")


def stats(r: np.ndarray) -> dict:
    """Per-period (daily) stats. t-stat = sharpe_daily * sqrt(T), T = n obs."""
    n      = len(r)
    mean   = r.mean()
    sd     = r.std(ddof=1)
    sharpe = mean / sd if sd > 0 else 0.0
    tstat  = sharpe * np.sqrt(n)
    return {
        "n": n, "mean": mean, "sd": sd,
        "sharpe_daily": sharpe, "sharpe_ann": sharpe * np.sqrt(252),
        "tstat": tstat, "total_ret": r.sum(),
    }


def plot(df: pd.DataFrame, bh: np.ndarray):
    eq_gross = (1 + df["gross"]).cumprod()
    eq_net   = (1 + df["net"]).cumprod()
    eq_bh    = (1 + pd.Series(bh, index=df.index)).cumprod()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=eq_bh.index, y=eq_bh.values, name="Buy & Hold",
                             line=dict(color="#888888", width=1.5)))
    fig.add_trace(go.Scatter(x=eq_gross.index, y=eq_gross.values, name="Strategy (raw)",
                             line=dict(color="#2ECC71", width=1.5)))
    fig.add_trace(go.Scatter(x=eq_net.index, y=eq_net.values, name="Strategy (net)",
                             line=dict(color="#E74C3C", width=1.5)))
    fig.update_layout(title="HMM-001 Gate 3 — 5%/20d Markov Signal, Walk-Forward (IS)",
                      xaxis_title="Date", yaxis_title="Equity (×)",
                      template="plotly_dark", height=600)
    out = "research/outputs/hmm/hmm_gate3_walkforward.html"
    fig.write_html(out)
    print(f"\nChart saved: {out}")


def main():
    close, cum20, labels = load_and_label()

    print("\n--- Sanity block ---")
    print(f"labels       : {len(labels)}  ({labels.index[0].date()} -> {labels.index[-1].date()})")
    print(f"min_train    : {MIN_TRAIN} days   cost: {SPREAD_PIPS} pip half={HALF_SPREAD_PX} px/turnover")

    df = walk_forward(close, labels)
    bh = df["fwd_ret"].values                            # buy & hold benchmark

    raw  = stats(df["gross"].values)
    net  = stats(df["net"].values)
    bhst = stats(bh)

    pos_share = (df["pos"] > 0).mean()
    n_flips   = int((df["turnover"] > 0).sum())

    print(f"\n--- Walk-forward ({raw['n']} trading days) ---")
    print(f"long share   : {pos_share:.1%}   short share: {(df['pos']<0).mean():.1%}   flips: {n_flips}")
    print(f"\n{'':12s}{'mean/day':>12s}{'Sharpe_d':>12s}{'Sharpe_ann':>12s}{'t-stat':>10s}{'total':>10s}")
    for name, s in [("RAW", raw), ("NET", net), ("BuyHold", bhst)]:
        print(f"{name:12s}{s['mean']:>12.2e}{s['sharpe_daily']:>12.4f}"
              f"{s['sharpe_ann']:>12.2f}{s['tstat']:>10.2f}{s['total_ret']:>10.2%}")

    plot(df, bh)

    raw_pass = raw["mean"] > 0 and raw["tstat"] > 1.0
    beats_bh = raw["sharpe_daily"] > bhst["sharpe_daily"]

    print("\n--- Gate 3 verdict ---")
    print(f"  raw edge > 0 & t>1.0 : {'PASS' if raw_pass else 'FAIL'} "
          f"(mean={raw['mean']:.2e}, t={raw['tstat']:.2f})")
    print(f"  net edge             : {'POSITIVE' if net['mean']>0 else 'NEGATIVE'} "
          f"(mean={net['mean']:.2e}, t={net['tstat']:.2f})")
    print(f"  vs buy & hold        : {'BEATS' if beats_bh else 'TRAILS'} "
          f"(strat Sharpe_d {raw['sharpe_daily']:.4f} vs B&H {bhst['sharpe_daily']:.4f})")

    # ── DB logging ────────────────────────────────────────────────────────────
    git_sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
    params  = json.dumps({"signal": "P(Bull)-P(Bear)", "position": "sign",
                          "min_train": MIN_TRAIN, "spread_pips": SPREAD_PIPS,
                          "walk_forward": True})
    d_start = str(df.index[0].date())
    d_end   = str(df.index[-1].date())

    gate3_rows = [g for g in get_gates("HMM-001") if g["gate_number"] == 3]
    attempt = max((g["attempt"] for g in gate3_rows), default=0) + 1
    open_gate("HMM-001", 3,
              pass_criteria="raw edge > 0 AND raw t-stat > 1.0 (net + B&H logged for context)",
              attempt=attempt)

    common = dict(idea_id="HMM-001", gate_number=3, stage="walkforward",
                  metric_key="signal_edge_daily_mean", period="daily",
                  n_obs=raw["n"], n_trials=1, data_start=d_start, data_end=d_end,
                  git_sha=git_sha, code_path="research/models/hmm/gate3_markov_signal.py",
                  parameters=params)
    rid_raw = log_result(**common, metric_value=raw["mean"], cost_adjusted=0,
                         notes=f"raw t={raw['tstat']:.2f} sharpe_ann={raw['sharpe_ann']:.2f} "
                               f"vs_BH_sharpe_d={bhst['sharpe_daily']:.4f}")
    rid_net = log_result(**common, metric_value=net["mean"], cost_adjusted=1,
                         notes=f"net t={net['tstat']:.2f} sharpe_ann={net['sharpe_ann']:.2f} "
                               f"flips={n_flips} long_share={pos_share:.2f}")

    answer = (f"raw mean={raw['mean']:.2e} t={raw['tstat']:.2f} | "
              f"net mean={net['mean']:.2e} t={net['tstat']:.2f} | "
              f"B&H sharpe_d={bhst['sharpe_daily']:.4f} beats={beats_bh}")
    if raw_pass:
        pass_gate("HMM-001", 3, gate_answer=answer, answered_by="agent", attempt=attempt)
        print(f"\n>>> GATE 3: PASS (attempt {attempt}) — raw {rid_raw} / net {rid_net}")
    else:
        block_gate("HMM-001", 3, gate_answer=answer, answered_by="agent", attempt=attempt)
        print(f"\n>>> GATE 3: BLOCKED (attempt {attempt}) — raw {rid_raw} / net {rid_net}")
        print("    Protocol says kill on raw t<1.0 — deferring kill decision to human.")

    print("Done.")


if __name__ == "__main__":
    main()
