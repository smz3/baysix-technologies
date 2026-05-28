"""
CUSUM-001 — Offline changepoint detection on XAUUSD IS daily log returns.
Detects structural breaks to produce stationary segments for HMM-001.
"""

import sys
import numpy as np
import pandas as pd
import ruptures as rpt
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from scipy import stats
from pathlib import Path
from tqdm import tqdm

# research/code/ is the shared DB layer
sys.path.insert(0, str(Path(__file__).parents[2] / "code"))
from pipeline import log_metric

TICK_DIR    = Path(__file__).parents[3] / "data" / "parquet" / "CS-GOLD-DUKAS-TICK"
DAILY_CACHE = Path(__file__).parents[3] / "data" / "parquet" / "daily" / "xauusd_daily.parquet"
OUTPUTS_DIR = Path(__file__).parents[2] / "outputs" / "cusum"
IS_SEAL     = "2024-05-02"
IS_YEARS    = list(range(2016, 2025))
IDEA_ID     = 1  # HMM-001 in pipeline (CUSUM-001 gates it)


# ── Data ─────────────────────────────────────────────────────────────────────

def build_daily_cache() -> pd.DataFrame:
    """Load tick data year by year, resample to daily close, cache to parquet."""
    print("Building daily cache from tick data...")
    frames = []
    for year in IS_YEARS:
        folder = TICK_DIR / f"year={year}"
        if not folder.exists():
            continue
        df = pd.read_parquet(folder, columns=["ts_utc", "bid", "ask"])
        df["mid"]  = (df["bid"] + df["ask"]) / 2
        df["date"] = pd.to_datetime(df["ts_utc"]).dt.date
        daily = df.groupby("date")["mid"].last().rename("close")
        frames.append(daily)
        print(f"  {year}: {len(daily)} trading days")

    result = pd.concat(frames).sort_index()
    result.index = pd.to_datetime(result.index)
    result = result[result.index <= IS_SEAL]
    DAILY_CACHE.parent.mkdir(parents=True, exist_ok=True)
    result.to_frame().to_parquet(DAILY_CACHE)
    print(f"Cached {len(result)} trading days -> {DAILY_CACHE}")
    return result


def load_is_returns(rebuild: bool = False) -> tuple:
    """
    Returns (log_returns, close_prices) filtered to IS window.
    Builds daily cache on first run.
    """
    if rebuild or not DAILY_CACHE.exists():
        close = build_daily_cache()
    else:
        close = pd.read_parquet(DAILY_CACHE)["close"]

    close   = close[close.index <= IS_SEAL].sort_index()
    returns = np.log(close / close.shift(1)).dropna()
    return returns, close.loc[returns.index]


# ── Detection ─────────────────────────────────────────────────────────────────

def detect_breakpoints(returns: pd.Series, penalty: float) -> list:
    """
    Run Pelt (rbf cost) on returns. Returns list of breakpoint indices.
    Last element is always len(returns) — the series end.
    min_size=15: no regime shorter than 15 trading days.
    """
    signal = returns.values.reshape(-1, 1)
    algo   = rpt.Pelt(model="rbf", min_size=15, jump=1).fit(signal)
    return algo.predict(pen=penalty)


def regime_stats(returns: pd.Series, breakpoints: list) -> dict:
    """Compute R², per-regime table, min regime length, max t-stat."""
    dates  = returns.index
    vals   = returns.values
    starts = [0] + breakpoints[:-1]
    ends   = breakpoints

    rows = []
    for i, (s, e) in enumerate(zip(starts, ends)):
        seg = vals[s:e]
        rows.append({
            "regime":   i + 1,
            "start":    dates[s].date(),
            "end":      dates[e - 1].date(),
            "n_days":   len(seg),
            "mean_ann": round(seg.mean() * 252, 4),
            "std_ann":  round(seg.std() * np.sqrt(252), 4),
            "skew":     round(float(pd.Series(seg).skew()), 3),
            "kurt":     round(float(pd.Series(seg).kurt()), 3),
        })

    table      = pd.DataFrame(rows)
    mu_global  = vals.mean()
    ss_total   = ((vals - mu_global) ** 2).sum()
    ss_between = sum(
        r["n_days"] * (vals[s:e].mean() - mu_global) ** 2
        for r, (s, e) in zip(rows, zip(starts, ends))
    )
    r_squared = ss_between / ss_total if ss_total > 0 else 0.0

    t_stats = []
    for i in range(len(rows) - 1):
        s1, e1 = starts[i], ends[i]
        s2, e2 = starts[i + 1], ends[i + 1]
        t, _ = stats.ttest_ind(vals[s1:e1], vals[s2:e2], equal_var=False)
        t_stats.append(abs(t))

    return {
        "table":     table,
        "r_squared": round(r_squared, 4),
        "min_regime": int(table["n_days"].min()),
        "max_tstat": round(max(t_stats), 3) if t_stats else 0.0,
        "k":         len(rows),
    }


def elbow_curve(returns: pd.Series, n_steps: int = 25) -> pd.DataFrame:
    """Sweep penalty on log scale; return DataFrame of penalty, K, RSS."""
    signal    = returns.values.reshape(-1, 1)
    sig_var   = float(np.var(returns.values))
    penalties = sig_var * np.logspace(-1, 3, n_steps)
    algo      = rpt.Pelt(model="l2", min_size=15, jump=5).fit(signal)
    rows = []
    for pen in tqdm(penalties, desc="Elbow sweep", unit="pen"):
        bkps = algo.predict(pen=pen)
        k    = len(bkps) - 1
        cost = algo.cost.sum_of_costs(bkps)
        rows.append({"penalty": round(pen, 6), "k": k, "rss": round(cost, 6)})
        tqdm.write(f"  pen={pen:.2e} | k={k:2d} | rss={cost:.4f}")
    return pd.DataFrame(rows).drop_duplicates("k").reset_index(drop=True)


def random_r2_benchmark(returns: pd.Series, k: int, n_draws: int = 100) -> dict:
    """Randomly place k breakpoints 100x; return mean R² and p99."""
    vals      = returns.values
    mu_global = vals.mean()
    ss_total  = ((vals - mu_global) ** 2).sum()
    n         = len(vals)
    r2_draws  = []

    for _ in range(n_draws):
        pts = sorted(np.random.choice(range(15, n - 15), size=k - 1, replace=False))
        pts = [0] + list(pts) + [n]
        ss_b = sum(
            len(vals[pts[i]:pts[i+1]]) * (vals[pts[i]:pts[i+1]].mean() - mu_global) ** 2
            for i in range(len(pts) - 1)
        )
        r2_draws.append(ss_b / ss_total)

    return {
        "r2_random_mean": round(np.mean(r2_draws), 4),
        "r2_random_p99":  round(np.percentile(r2_draws, 99), 4),
    }


def calendar_r2_benchmark(returns: pd.Series) -> float:
    """R² using calendar year segmentation (naive baseline)."""
    vals      = returns.values
    years     = returns.index.year
    mu_global = vals.mean()
    ss_total  = ((vals - mu_global) ** 2).sum()
    ss_between = sum(
        len(vals[years == y]) * (vals[years == y].mean() - mu_global) ** 2
        for y in np.unique(years)
    )
    return round(ss_between / ss_total, 4)


# ── Plots ─────────────────────────────────────────────────────────────────────

def _breakpoint_dates(returns: pd.Series, breakpoints: list) -> list:
    return [returns.index[b - 1] for b in breakpoints[:-1]]


def plot_price_breakpoints(close: pd.Series, returns: pd.Series, breakpoints: list) -> go.Figure:
    """Plot 1: XAUUSD daily price + vertical breakpoint lines."""
    bkp_dates = _breakpoint_dates(returns, breakpoints)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=close.index, y=close.values,
        mode="lines", name="XAUUSD Close",
        line=dict(color="#F5A623", width=1.5)
    ))
    for d in bkp_dates:
        fig.add_vline(x=d, line_dash="dash", line_color="red", opacity=0.7)
    fig.update_layout(
        title="CUSUM-001 | XAUUSD Price + Detected Breakpoints",
        xaxis_title="Date", yaxis_title="Price (USD)",
        template="plotly_dark", height=500,
    )
    return fig


def plot_vol_breakpoints(returns: pd.Series, breakpoints: list) -> go.Figure:
    """Plot 2: Rolling 21-day volatility + breakpoint lines."""
    rolling_vol = returns.rolling(21).std() * np.sqrt(252)
    bkp_dates   = _breakpoint_dates(returns, breakpoints)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=rolling_vol.index, y=rolling_vol.values,
        mode="lines", name="21d Realised Vol (ann.)",
        line=dict(color="#4A90D9", width=1.5)
    ))
    for d in bkp_dates:
        fig.add_vline(x=d, line_dash="dash", line_color="red", opacity=0.7)
    fig.update_layout(
        title="CUSUM-001 | Rolling Volatility + Breakpoints",
        xaxis_title="Date", yaxis_title="Annualised Vol",
        template="plotly_dark", height=500,
    )
    return fig


def plot_regime_distributions(returns: pd.Series, breakpoints: list) -> plt.Figure:
    """Plot 3: Return distribution per regime (Seaborn KDE)."""
    starts  = [0] + breakpoints[:-1]
    ends    = breakpoints
    dates   = returns.index
    palette = sns.color_palette("tab10", n_colors=len(starts))

    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    for i, (s, e) in enumerate(zip(starts, ends)):
        seg   = returns.values[s:e]
        label = f"R{i+1} ({dates[s].year}-{dates[e-1].year})"
        sns.kdeplot(seg, ax=ax, label=label, color=palette[i], linewidth=2, fill=True, alpha=0.15)

    ax.set_xlabel("Daily Log Return", color="white")
    ax.set_ylabel("Density", color="white")
    ax.set_title("CUSUM-001 | Regime Return Distributions", color="white", pad=12)
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("#444")
    ax.legend(facecolor="#2a2a3e", labelcolor="white", fontsize=9)
    plt.tight_layout()
    return fig


# ── Main ──────────────────────────────────────────────────────────────────────

def run(penalty: float = None, save_plots: bool = True) -> dict:
    """
    Full CUSUM-001 run:
    1. Load IS returns
    2. Elbow curve to select penalty
    3. Detect breakpoints
    4. Compute stats + benchmarks
    5. Save plots
    6. Log IS_SIGNAL_tstat to pipeline
    """
    print("=" * 60)
    print("CUSUM-001 -- Changepoint Detection")
    print("=" * 60)

    returns, close = load_is_returns()
    print(f"IS returns: {len(returns)} days | {returns.index[0].date()} to {returns.index[-1].date()}")

    print("\n[1] Elbow curve...")
    elbow_df = elbow_curve(returns)
    print(elbow_df.to_string(index=False))

    if penalty is None:
        sig_var = float(np.var(returns.values))
        penalty = sig_var * np.log(len(returns))
        print(f"\nAuto-selected penalty (BIC): {penalty:.2e}")

    print(f"\n[2] Detecting breakpoints (penalty={penalty})...")
    breakpoints = detect_breakpoints(returns, penalty)
    k = len(breakpoints) - 1
    print(f"K={k} breakpoints detected")

    print("\n[3] Regime statistics...")
    stats_out = regime_stats(returns, breakpoints)
    print(stats_out["table"].to_string(index=False))
    print(f"\nR-squared : {stats_out['r_squared']}")
    print(f"Min regime: {stats_out['min_regime']} days")
    print(f"Max t-stat: {stats_out['max_tstat']}")

    print("\n[4] Benchmarks...")
    cal_r2  = calendar_r2_benchmark(returns)
    rand_bm = random_r2_benchmark(returns, k=k)
    print(f"Calendar year R2      : {cal_r2}")
    print(f"Random R2 mean / p99  : {rand_bm['r2_random_mean']} / {rand_bm['r2_random_p99']}")
    print(f"Beats calendar        : {'YES' if stats_out['r_squared'] > cal_r2 else 'NO'}")
    print(f"Beats random p99      : {'YES' if stats_out['r_squared'] > rand_bm['r2_random_p99'] else 'NO'}")

    if save_plots:
        print("\n[5] Saving plots...")
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

        fig1 = plot_price_breakpoints(close, returns, breakpoints)
        fig1.write_html(str(OUTPUTS_DIR / "01_price_breakpoints.html"))

        fig2 = plot_vol_breakpoints(returns, breakpoints)
        fig2.write_html(str(OUTPUTS_DIR / "02_vol_breakpoints.html"))

        fig3 = plot_regime_distributions(returns, breakpoints)
        fig3.savefig(str(OUTPUTS_DIR / "03_regime_distributions.png"), dpi=150, bbox_inches="tight")
        plt.close(fig3)

        print(f"  Plots saved -> {OUTPUTS_DIR}")

    print("\n[6] Logging to pipeline...")
    log_metric(
        idea_id=IDEA_ID,
        metric_key="IS_SIGNAL_tstat",
        metric_value=stats_out["max_tstat"],
        metric_unit="t-stat",
        test_type="t_test",
        triggered_by="cusum_module",
        summary=f"K={k} | R2={stats_out['r_squared']} | penalty={penalty}",
    )

    print("\n" + "=" * 60)
    print("CUSUM-001 complete.")

    return {
        "k":           k,
        "penalty":     penalty,
        "r_squared":   stats_out["r_squared"],
        "max_tstat":   stats_out["max_tstat"],
        "min_regime":  stats_out["min_regime"],
        "cal_r2":      cal_r2,
        "rand_r2_p99": rand_bm["r2_random_p99"],
        "table":       stats_out["table"],
        "breakpoints": breakpoints,
        "elbow_df":    elbow_df,
    }


if __name__ == "__main__":
    run()
