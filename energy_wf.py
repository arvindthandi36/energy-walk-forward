"""Walk-forward time-series momentum on Brent and WTI spot, pre-registered in PREREGISTRATION.md."""
import json
import numpy as np
import pandas as pd

LOOKBACKS = (20, 60, 120, 250)
COST_BP = 10.0
TEST_YEARS = range(1993, 2026)
ANN = 252


def load_prices(path):
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    df["Date"] = pd.to_datetime(df["Date"])
    s = df.set_index("Date")["Price"].astype(float).sort_index()
    return s[s > 0]                      # pre-registered: drop non-positive prices


def daily_returns(prices):
    return prices.pct_change().dropna()


def positions(prices, lookback):
    """+1/-1 decided at the close of t-1 from the trailing return, applied to day t."""
    trail = prices / prices.shift(lookback) - 1.0
    pos = np.sign(trail).replace(0, np.nan).ffill().shift(1)
    return pos


def strategy_returns(prices, lookback, cost_bp=COST_BP):
    r = daily_returns(prices)
    pos = positions(prices, lookback).reindex(r.index)
    turnover = pos.diff().abs().fillna(pos.abs())
    net = pos * r - turnover * cost_bp / 1e4
    return net.dropna()


def sharpe(r):
    r = pd.Series(r).dropna()
    sd = r.std(ddof=1)
    return float(r.mean() / sd * np.sqrt(ANN)) if sd > 0 else float("nan")


def max_drawdown(r):
    eq = (1 + pd.Series(r).fillna(0)).cumprod()
    return float((eq / eq.cummax() - 1).min())


def ann_return(r):
    r = pd.Series(r).dropna()
    return float((1 + r).prod() ** (ANN / len(r)) - 1)


def walk_forward(prices, years=TEST_YEARS, lookbacks=LOOKBACKS):
    all_strat = {L: strategy_returns(prices, L) for L in lookbacks}
    rows, oos = [], []
    for y in years:
        start = pd.Timestamp(f"{y}-01-01")
        end = pd.Timestamp(f"{y}-12-31")
        ins = {L: sharpe(s[s.index < start]) for L, s in all_strat.items()}
        best = max(ins, key=lambda k: (ins[k] if ins[k] == ins[k] else -1e9))
        test = all_strat[best][(all_strat[best].index >= start) & (all_strat[best].index <= end)]
        bh = daily_returns(prices)
        bh = bh[(bh.index >= start) & (bh.index <= end)]
        rows.append(dict(year=y, lookback=best, in_sample_sharpe=round(ins[best], 3),
                         oos_sharpe=round(sharpe(test), 3), oos_return=round(float((1 + test).prod() - 1), 4),
                         bh_return=round(float((1 + bh).prod() - 1), 4)))
        oos.append(test)
    return pd.DataFrame(rows), pd.concat(oos)


def block_bootstrap_sharpe_diff(a, b, draws=1000, block=20, seed=7):
    rng = np.random.default_rng(seed)
    x = pd.concat([a, b], axis=1, join="inner").dropna().values
    n = len(x)
    out = []
    for _ in range(draws):
        idx = []
        while len(idx) < n:
            s = rng.integers(0, n - block)
            idx.extend(range(s, s + block))
        smp = x[np.array(idx[:n])]
        out.append(sharpe(smp[:, 0]) - sharpe(smp[:, 1]))
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def run(name, path):
    p = load_prices(path)
    folds, oos = walk_forward(p)
    bh = daily_returns(p).reindex(oos.index)
    lo, hi = block_bootstrap_sharpe_diff(oos, bh)
    return folds, oos, bh, dict(
        market=name, test_years=f"{min(TEST_YEARS)}-{max(TEST_YEARS)}", folds=len(folds),
        oos_days=int(len(oos)),
        momentum_ann_return=round(ann_return(oos), 4), bh_ann_return=round(ann_return(bh), 4),
        momentum_ann_vol=round(float(oos.std() * np.sqrt(ANN)), 4), bh_ann_vol=round(float(bh.std() * np.sqrt(ANN)), 4),
        momentum_sharpe=round(sharpe(oos), 3), bh_sharpe=round(sharpe(bh), 3),
        momentum_max_dd=round(max_drawdown(oos), 4), bh_max_dd=round(max_drawdown(bh), 4),
        years_momentum_beat_bh=int((folds.oos_return > folds.bh_return).sum()),
        mean_in_sample_sharpe_of_chosen=round(float(folds.in_sample_sharpe.mean()), 3),
        mean_oos_sharpe_by_year=round(float(folds.oos_sharpe.mean()), 3),
        sharpe_diff_ci95=[round(lo, 3), round(hi, 3)])


if __name__ == "__main__":
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    summary = []
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for name, path in [("Brent", "data/brent-daily.csv"), ("WTI", "data/wti-daily.csv")]:
        folds, oos, bh, s = run(name, path)
        folds.to_csv(f"outputs/folds_{name.lower()}.csv", index=False)
        summary.append(s)
        ax.plot((1 + oos).cumprod(), label=f"{name} momentum, walk-forward")
        ax.plot((1 + bh).cumprod(), label=f"{name} buy-and-hold", alpha=0.6)
    ax.set_yscale("log"); ax.set_title("Out-of-sample equity, 1993 to 2025, net of 10bp costs")
    ax.legend(fontsize=8); ax.grid(alpha=0.3); fig.tight_layout()
    fig.savefig("outputs/equity_curves.png", dpi=160)
    with open("outputs/summary.json", "w") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2))
