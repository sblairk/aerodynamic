# Results

## Executive Summary

Aerodynamic tested two public-disclosure signals: corporate insider purchases and U.S. Congressional purchases. The insider signal did not show robust standalone alpha after correcting for repeated-event counting and enforcing point-in-time information. The Congressional strategy produced modest positive historical excess returns in a weekly portfolio simulation, but with higher volatility and slightly weaker risk-adjusted performance than SPY. The Congressional result was driven primarily by House disclosures rather than Senate disclosures.

## Corporate Insider Purchases

The final insider study uses independent ticker-level events with a 14-day cooldown and enters at the next trading-day open after the SEC filing date.

| Holding period | Observations | Avg. stock return | Avg. excess vs SPY | Beat SPY |
|---|---:|---:|---:|---:|
| 20 trading days | 943 | 1.20% | +0.14% | 48.04% |
| 60 trading days | 894 | 1.83% | -1.31% | 42.95% |
| 120 trading days | 839 | -1.46% | -6.73% | 37.78% |

The signal was approximately market-like over 20 trading days and materially weaker over 60 and 120 trading days. Earlier stronger results were reduced after removing repeated observations from the same underlying buying episode and freezing all information point-in-time.

## Congressional Purchases: Base Case

The base case uses both chambers, a 365-day transaction-date rolling window, lower-bound purchase-size weighting, weekly rebalancing, and 10 bps one-way transaction costs.

| Metric | Congress Net | SPY |
|---|---:|---:|
| Total return | 139.90% | 121.03% |
| CAGR | 16.50% | 14.84% |
| Annualized volatility | 19.43% | 16.32% |
| Sharpe | 0.88 | 0.93 |
| Max drawdown | -23.13% | -23.31% |
| Positive weeks | 58.53% | 60.54% |

Net CAGR exceeded SPY by 1.65 percentage points annually. Average invested weight was 91.15%, with 8.85% held in cash because some intended holdings could not be reliably priced historically. Average weekly turnover was 4.16%, equivalent to approximately 2.16x annualized turnover.

### Annual Returns

| Year | Congress Net | SPY | Excess |
|---|---:|---:|---:|
| 2021 | 23.71% | 27.46% | -3.75% |
| 2022 | -16.73% | -17.60% | +0.86% |
| 2023 | 39.49% | 25.73% | +13.76% |
| 2024 | 12.92% | 25.60% | -12.68% |
| 2025 | 24.71% | 18.32% | +6.39% |
| 2026 YTD | 18.55% | 12.63% | +5.92% |

The strategy did not outperform consistently each year. 2023 was the strongest relative year, while 2024 materially underperformed.

## Congressional Robustness

The robustness matrix tested 54 specifications across rolling-window length, purchase-size weighting, transaction costs and chamber selection.

| Robustness statistic | Result |
|---|---:|
| Specifications tested | 54 |
| Beating SPY CAGR | 34 / 54 (63.0%) |
| Beating SPY Sharpe | 11 / 54 (20.4%) |
| Median strategy CAGR | 16.13% |
| Median excess CAGR vs SPY | +1.28% |
| Minimum excess CAGR | -10.98% |
| Maximum excess CAGR | +6.20% |

| Dimension | Median CAGR | Median excess vs SPY | Median Sharpe |
|---|---:|---:|---:|
| 180-day window | 16.53% | +1.69% | 0.84 |
| 365-day window | 16.37% | +1.53% | 0.87 |
| 730-day window | 14.88% | +0.04% | 0.89 |
| Lower-bound weighting | 16.50% | +1.65% | 0.88 |
| Midpoint weighting | 15.88% | +1.03% | 0.86 |
| Both chambers | 16.13% | +1.28% | 0.88 |
| House only | 17.99% | +3.15% | 0.93 |
| Senate only | 8.20% | -6.65% | 0.53 |

The central finding is that the Congressional effect is concentrated in House purchases. Senate-only portfolios materially underperformed SPY. Shorter 180 and 365-day windows retained positive excess returns, while the 730-day window was approximately flat to SPY, suggesting the signal weakens at longer horizons.

## Overall Conclusion

The two signals produced different outcomes. Corporate insider purchases did not retain robust excess returns after methodological tightening. Congressional purchases produced modest positive historical excess returns under the base portfolio specification and across several reasonable sensitivity tests, but the result did not consistently improve risk-adjusted performance and was primarily attributable to House disclosures.

The most defensible conclusion is that publicly disclosed House purchases exhibited a stronger historical return signal than the tested corporate insider-purchase framework, while Senate purchases did not.