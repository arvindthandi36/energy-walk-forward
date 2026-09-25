# Pre-registration (fixed before any result was computed)

Question: does a simple time-series momentum rule, with its lookback re-selected each year
using only past data, beat buy-and-hold on daily Brent and WTI spot prices out of sample,
after costs?

Data: EIA daily spot prices for Brent (from 1987-05-20) and WTI (from 1986-01-02), via the
public datasets/oil-prices repository, snapshot to 2026-09-22. Prices at or below zero
(WTI, 20 April 2020) are excluded and the return is taken from the last valid price.

Rule: position on day t = sign of the trailing L-day return measured at the close of day t-1,
long or short one unit. Lookback set L = {20, 60, 120, 250} trading days.

Walk-forward: for each test year 1993 to 2025, choose the L with the highest annualised
Sharpe net of costs on all data before 1 January of that year (expanding window), then
trade that L for the whole test year. No parameter touches test-year data.

Costs: 10 basis points per unit of position change, so a flip from long to short costs 20.

Benchmark: buy-and-hold, long one unit, same days.

Reported, whatever they show: out-of-sample annualised return, volatility, Sharpe and maximum
drawdown for both, the share of test years momentum beat buy-and-hold, the gap between the
chosen lookback's in-sample and out-of-sample Sharpe, and a 1,000-draw block-bootstrap 95%
interval for the Sharpe difference. Nothing is re-run with different settings after the fact.
