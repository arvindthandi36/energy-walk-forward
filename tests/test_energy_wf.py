import numpy as np
import pandas as pd
import pytest
import energy_wf as e


def _prices(n=600, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2000-01-03", periods=n)
    return pd.Series(50 * np.exp(np.cumsum(rng.normal(0, 0.02, n))), index=idx)


def test_no_lookahead_in_positions():
    p = _prices()
    base = e.positions(p, 20)
    q = p.copy(); q.iloc[400:] *= 3.0          # change the future only
    alt = e.positions(q, 20)
    pd.testing.assert_series_equal(base.iloc[:401], alt.iloc[:401])


def test_position_uses_previous_close():
    p = _prices()
    pos = e.positions(p, 20)
    t = p.index[100]
    expected = np.sign(p.iloc[99] / p.iloc[79] - 1)
    assert pos.loc[t] == expected


def test_flip_costs_twenty_bp():
    idx = pd.bdate_range("2000-01-03", periods=6)
    p = pd.Series([10, 11, 12, 11, 10, 9], index=idx, dtype=float)
    r = e.strategy_returns(p, 1, cost_bp=10)
    pos = e.positions(p, 1).reindex(r.index)
    flips = pos.diff().abs() == 2
    raw = pos * e.daily_returns(p).reindex(r.index)
    assert np.allclose((raw - r)[flips], 0.002)


def test_walk_forward_ignores_test_year_data():
    p = _prices(n=2600)
    folds_a, _ = e.walk_forward(p, years=range(2008, 2010))
    q = p.copy(); q[q.index.year == 2009] *= np.linspace(1, 5, int((q.index.year == 2009).sum()))
    folds_b, _ = e.walk_forward(q, years=range(2008, 2010))
    assert folds_a.lookback.tolist() == folds_b.lookback.tolist()


def test_non_positive_prices_dropped(tmp_path):
    f = tmp_path / "p.csv"
    f.write_text("Date,Price\n2020-04-17,18.27\n2020-04-20,-37.63\n2020-04-21,10.01\n")
    s = e.load_prices(f)
    assert (s > 0).all() and len(s) == 2


def test_sharpe_and_drawdown_known_values():
    r = pd.Series([0.1, -0.5, 0.2])
    assert e.max_drawdown(r) == pytest.approx(-0.5)
    assert np.isnan(e.sharpe(pd.Series([0.01, 0.01, 0.01])))
