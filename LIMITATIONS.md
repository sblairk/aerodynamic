# Limitations

Aerodynamic is a historical research project built from public disclosure data and public market-price data. It is not an institutional-grade execution or factor-research platform, and its conclusions should be interpreted accordingly.

## Corporate Insider Study

The insider study depends on historical SEC Form 4 data and Yahoo Finance price history. Historical 10b5-1 identification is incomplete, particularly before more standardized disclosure requirements. Price-history coverage is also incomplete for some securities, which can introduce survivorship and missing-data bias. The event study uses SPY as a broad benchmark rather than a factor-matched benchmark and does not control for size, value, momentum, sector or liquidity exposures.

The insider analysis is an event study rather than a fully investable portfolio simulation. It does not model portfolio-level capital allocation, overlapping positions, borrowing constraints, slippage or realistic execution beyond next-open entry assumptions.

## Congressional Disclosure Coverage

The Congressional dataset intentionally excludes disclosures that cannot be parsed reliably without OCR or manual transcription. Approximately 15.8% of House PTR PDFs in the sample were image-only and were excluded. Senate paper filings were also excluded, leaving 855 machine-readable electronic PTRs out of 988 identified Senate PTR filings.

The dataset therefore does not represent every Congressional transaction during the period. Missing filings may not be random, and the resulting coverage limitation could affect estimated returns.

## Disclosure Timing

The backtest uses filing date rather than filing timestamp. A trade is eligible only when the filing date is strictly earlier than the rebalance date, which is conservative and avoids assuming same-day filings were available before the market open. However, exact intraday information timing is not modeled.

Congressional filings can also be made long after the underlying transaction. Late disclosures remain eligible only after publication, but their signal life is measured using transaction date, so very late-filed trades may have little remaining time in the rolling window.

## Transaction Amounts

STOCK Act disclosures provide amount ranges rather than exact transaction values. The base strategy uses the lower bound of each reported range as a conservative proxy. Midpoint weighting is included as a robustness test. Neither measure represents the true transaction size.

A small number of House rows contained malformed or misaligned amount fields and were excluded rather than manually repaired.

## Market Data

Historical prices are sourced from Yahoo Finance and therefore inherit Yahoo's coverage, symbol-history and survivorship limitations. Genuine same-security ticker renames can be mapped, but acquired companies are not mapped into acquiring-company securities because that would splice different instruments.

When a target holding cannot be priced, the intended allocation remains in cash rather than being redistributed. The base Congressional portfolio therefore averaged 91.15% invested and 8.85% cash. This is a conservative treatment, but missing market data may still bias results if unavailable securities differ systematically from the securities with complete histories.

Delisting and acquisition proceeds are not reconstructed from an institutional delisting-return database. The final backtest required only one fallback exit and had zero unresolved exits, but the broader price-history limitation remains relevant.

## Backtest Assumptions

The Congressional base case assumes 10 bps one-way transaction costs. Actual execution costs vary by liquidity, broker, order size and period. The strategy is rebalanced weekly and does not model market impact, taxes or borrowing constraints.

The reported Sharpe ratios use a zero risk-free rate rather than contemporaneous Treasury-bill rates. SPY is used as the benchmark instead of a factor-neutral or sector-matched benchmark.

The robustness grid contains 54 specifications, but these are highly correlated sensitivity tests rather than 54 independent statistical experiments. The percentage of specifications beating SPY should therefore not be interpreted as a formal significance test.

## Research Interpretation

Backtested performance is not evidence that the strategy will perform similarly in the future. The study is best interpreted as a transparent test of whether these public-disclosure signals showed historical return patterns under a defined set of assumptions. The Congressional result is strongest for House disclosures and materially weaker for Senate disclosures and longer signal windows, so the evidence does not support a broad claim that all Congressional trading predicts excess returns.