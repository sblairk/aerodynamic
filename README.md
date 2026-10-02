# Aerodynamic

Aerodynamic is a quantitative research project testing publicly observable trading signals from corporate insiders and U.S. congressional disclosures.

## Part I — Corporate Insider Trading

## What This Project Does

Aerodynamic tests whether publicly disclosed insider purchases reported through SEC Form 4 filings can be used to generate excess stock returns.

The strategy focuses on open-market insider purchases and scores each signal based on:

- Purchase value
- Increase in insider holdings
- Insider role
- Cluster buying by multiple insiders
- 10b5-1 status

The historical test uses SEC Form 4 data from 2021–2025 and compares subsequent stock performance against SPY.

## Data and Signal Rules

Historical insider transactions are sourced from the SEC Insider Transactions Data Sets.

Only open-market purchases are included:

- SEC transaction code: `P`
- Management and directors only
- Filing lag: 0–10 calendar days
- Transaction price: $0.01–$10,000
- Purchase value: $10,000–$100 million
- Minimum stock entry price: $5.00

Signals are based on the SEC filing date rather than the transaction date to avoid look-ahead bias.

## Conviction Score

Each purchase receives an Aerodynamic Conviction Score.

### Purchase Value
- <$100k: 0
- $100k–$250k: 1
- $250k–$500k: 2
- $500k–$1m: 3
- $1m–$5m: 4
- $5m+: 5

### Holdings Increase
- <2%: 0
- 2–5%: 1
- 5–10%: 2
- 10–25%: 3
- 25–50%: 4
- 50%+: 5

### Role
- CEO: 4
- CFO: 4
- Chairman: 3
- President: 3
- COO: 3
- Other Executive: 2
- Director: 1

### Cluster Buying
- 1 insider: 0
- 2 insiders: 2
- 3 insiders: 4
- 4+ insiders: 5
- CEO/CFO involvement can add 1 point, capped at 5

### 10b5-1
- Identified 10b5-1 transaction: -5

### Conviction Classification
- 15+: Very Strong
- 12–14: Strong
- 9–11: Moderate
- 6–8: Weak
- <6: Ignore

The historical backtest uses signals with a score of at least 12.

## Final Backtest Methodology

The final test is a point-in-time event-level backtest.

For each ticker:

1. Take the first qualifying signal with Conviction Score ≥12
2. Freeze all information available on that filing date
3. Buy at the next trading-day open
4. Ignore additional qualifying signals in the same ticker for 14 calendar days
5. Measure returns after 20, 60 and 120 trading days
6. Compare performance with SPY over the same period

This avoids repeatedly counting multiple insider filings from the same event as separate independent trades.

## Final Results

### 20 Trading Days
- Observations: 943
- Average stock return: 1.20%
- Median stock return: 0.38%
- Positive return rate: 51.43%
- Average excess return vs SPY: 0.14%
- Median excess return vs SPY: -0.43%
- Beat SPY rate: 48.04%

### 60 Trading Days
- Observations: 894
- Average stock return: 1.83%
- Median stock return: 0.15%
- Positive return rate: 50.34%
- Average excess return vs SPY: -1.31%
- Median excess return vs SPY: -3.42%
- Beat SPY rate: 42.95%

### 120 Trading Days
- Observations: 839
- Average stock return: -1.46%
- Median stock return: -2.38%
- Positive return rate: 45.53%
- Average excess return vs SPY: -6.73%
- Median excess return vs SPY: -7.93%
- Beat SPY rate: 37.78%

## Results by Insider Role

Selected 20D / 60D excess-return results:

- CEO: 0.01% / -1.31%
- CFO: 1.48% / 3.26%
- COO: 0.90% / -1.91%
- Chairman: -0.66% / -2.61%
- Director: -0.91% / -5.28%
- Other Executive: 1.30% / 2.58%
- President: 0.58% / -0.17%

CFO and Other Executive purchases showed relatively better results, while Director purchases were consistently weak.

## Results by Conviction Score

The score was not consistently monotonic.

Examples:

- Score 12: 20D excess +0.14%, 60D excess -2.87%
- Score 13: 20D excess +1.59%, 60D excess +0.49%
- Score 14: 20D excess -1.63%, 60D excess +1.87%
- Score 15: 20D excess -1.86%, 60D excess -3.48%
- Score 16: 20D excess -4.03%, 60D excess -8.07%
- Score 18: 20D excess +7.75%, 60D excess +7.66%

Score 18 performed strongly, but only had 10 observations at 20D and 9 at 60D, so the sample was too small to treat as reliable evidence.

## Coverage

Final point-in-time backtest:

- Eligible filing-level signals: 3,040
- Point-in-time events after 14-day cooldown: 1,583
- Valid backtest observations: 960
- Event coverage rate: 60.64%
- Failed Yahoo Finance tickers: 277
- Skipped for missing price/history: 442
- Skipped because entry price was below $5: 181

The relatively low price-history coverage is an important limitation and may introduce survivorship bias.

## Conclusion

The final point-in-time backtest did not show a robust standalone alpha signal from the current Aerodynamic insider-purchase scoring framework.

The strategy was approximately market-neutral over 20 trading days and underperformed SPY over 60 and 120 trading days.

The earlier stronger results were materially reduced after correcting for repeated observations from the same insider-buying event and ensuring all signal information was available at the actual trading date.

The project therefore does not support using the current Aerodynamic insider-purchase score as a standalone automated trading strategy.

## Reproducing the Analysis

Install dependencies:

```powershell
pip install -r requirements.txt
```

Before accessing SEC endpoints, set a descriptive SEC user agent with your own contact email:

```powershell
$env:SEC_USER_AGENT="Aerodynamic research project your-email@example.com"
```

Run:

```powershell
python insider_trading/historical_sec.py
python insider_trading/historical_score.py
python insider_trading/event_backtest.py
```

Core files:

- `insider_trading/historical_sec.py` — downloads and processes historical SEC Form 4 data
- `insider_trading/historical_score.py` — cleans transactions and calculates conviction scores
- `insider_trading/event_backtest.py` — runs the final point-in-time event-level backtest

## Part II — Congressional Trading

In progress.
