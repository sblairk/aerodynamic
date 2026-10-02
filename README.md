# Aerodynamic

Aerodynamic is a quantitative research project testing publicly observable trading signals from corporate insiders and U.S. congressional disclosures.

## Overview

The project compares two signals:

1. Corporate insider open-market purchases reported through SEC Form 4 filings
2. U.S. Congressional stock purchases reported through House and Senate financial disclosures

Both studies are designed around point-in-time information so that a trade is only considered after the relevant filing became public.

For a concise explanation of the research design, results and caveats, see:

- `METHODOLOGY.md`
- `RESULTS.md`
- `LIMITATIONS.md`

## Part I — Corporate Insider Trading

Historical insider transactions are sourced from official SEC Form 4 / Insider Transactions data for 2021–2025. The study focuses on genuine open-market purchases (`P`) by management and directors, excludes pure 10% owners, and uses the SEC filing date rather than transaction date as the signal date.

Each signal is scored using purchase value, percentage increase in holdings, insider role, cluster buying and identified 10b5-1 status. The final event study uses signals scoring at least 12, applies a 14-calendar-day ticker cooldown, enters at the next trading-day open and compares 20, 60 and 120 trading-day forward returns with SPY.

### Final Insider Results

| Holding period | Observations | Avg. stock return | Avg. excess vs SPY | Beat SPY |
|---|---:|---:|---:|---:|
| 20 trading days | 943 | 1.20% | +0.14% | 48.04% |
| 60 trading days | 894 | 1.83% | -1.31% | 42.95% |
| 120 trading days | 839 | -1.46% | -6.73% | 37.78% |

The final point-in-time event study did not show robust standalone alpha. Performance was approximately market-like over 20 trading days and weaker over 60 and 120 trading days.

Core files:

- `insider_trading/historical_sec.py`
- `insider_trading/historical_score.py`
- `insider_trading/event_backtest.py`

## Part II — Congressional Trading

Congressional transactions are sourced from official House and Senate financial-disclosure systems for 2020–2026. The cleaned investable universe contains 15,818 purchases across 185 politicians and 2,190 tickers.

The base strategy is rebalanced weekly. A transaction is only eligible when its filing date is earlier than the rebalance date. The base specification uses a 365-day transaction-date rolling window, weights purchases by the lower bound of the disclosed amount range, caps any single security at 50%, leaves unpriceable allocations in cash, assumes 10 bps one-way transaction costs and benchmarks against SPY.

### Final Congressional Base Case

| Metric | Congress Net | SPY |
|---|---:|---:|
| Total return | 139.90% | 121.03% |
| CAGR | 16.50% | 14.84% |
| Annualized volatility | 19.43% | 16.32% |
| Sharpe | 0.88 | 0.93 |
| Max drawdown | -23.13% | -23.31% |

Net CAGR exceeded SPY by 1.65 percentage points annually, but volatility was higher and the Sharpe ratio was slightly lower.

### Robustness

The Congressional strategy was tested across 54 specifications covering 180, 365 and 730-day windows; lower-bound and midpoint weighting; 0, 10 and 25 bps transaction costs; and combined, House-only and Senate-only portfolios.

- 34 / 54 specifications beat SPY CAGR
- Median excess CAGR: +1.28%
- House-only median excess CAGR: +3.15%
- Senate-only median excess CAGR: -6.65%

The main Congressional finding is therefore concentrated in House disclosures rather than Senate disclosures, and it weakens materially at longer signal horizons.

## Overall Conclusion

The corporate insider signal did not retain robust excess returns after correcting repeated-event counting and enforcing point-in-time methodology. Congressional purchases produced modest positive historical excess returns under the base portfolio specification and several reasonable sensitivity tests, but without consistently superior risk-adjusted performance. The effect was primarily driven by House disclosures.

## Reproducing the Analysis

Install dependencies:

```powershell
pip install -r requirements.txt
```

Before accessing SEC endpoints, set a descriptive SEC user agent with your own contact email:

```powershell
$env:SEC_USER_AGENT="Aerodynamic research project your-email@example.com"
```

Run the insider study:

```powershell
python insider_trading/historical_sec.py
python insider_trading/historical_score.py
python insider_trading/event_backtest.py
```

The consolidated Congressional pipeline consists of:

```text
house_data.py
senate_data.py
prepare_data.py
backtest.py
robustness.py
```

Run them in that order after placing the Congressional files in the repository structure described in the methodology documentation.
