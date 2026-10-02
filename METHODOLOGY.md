# Methodology

Aerodynamic compares two publicly observable trading signals using point-in-time information: corporate insider purchases and U.S. Congressional purchases. The objective is not to reproduce any third-party product exactly, but to test whether the underlying public disclosures contain a usable historical return signal under explicit, reproducible rules.

## Corporate Insider Purchases

Historical insider transactions are sourced from official SEC Form 4 / Insider Transactions data for 2021–2025. The sample is restricted to genuine open-market purchases (`P`) by management and directors, with pure 10% owners excluded. The signal date is the SEC filing date rather than the transaction date so the test only uses information that was public at the time.

Each purchase receives a conviction score based on purchase value, percentage increase in holdings, insider seniority, cluster buying, and identified 10b5-1 status. The final study uses signals scoring at least 12, takes the first qualifying ticker-level event, applies a 14-calendar-day cooldown to avoid repeatedly counting the same buying episode, and enters at the next trading-day open.

The insider study is an event study rather than a portfolio simulation. Forward stock returns are measured over 20, 60 and 120 trading days and compared with SPY over the same periods.

## Congressional Purchases

Congressional transactions are collected from official House and Senate financial-disclosure systems for 2020–2026. House Periodic Transaction Reports are sourced from the Clerk of the House disclosure archives. Senate Periodic Transaction Reports are collected from the Senate eFD system. Only machine-readable disclosures are used; image-only House PDFs and paper-only Senate filings are excluded rather than OCR-transcribed.

The cleaned investable universe contains 15,818 purchases across 185 politicians and 2,190 tickers. The pipeline standardizes House and Senate schemas, validates ticker and date fields, removes cross-document or cross-report redisclosures while retaining same-report rows, and excludes non-standard disclosure amount fields that cannot be interpreted reliably.

The base portfolio is rebalanced weekly on the first U.S. trading day of each week. A purchase is eligible only when its filing date is earlier than the rebalance date, preventing same-day look-ahead. The base signal uses purchases from the prior 365 calendar days by transaction date. Position weights are proportional to the lower bound of each disclosed purchase range, aggregated by ticker, with a 50% single-security cap.

Historical prices are sourced from Yahoo Finance. Genuine ticker renames can be mapped across the same security, but acquisitions are not mapped into the acquirer. If a target allocation cannot be priced, that weight remains in cash rather than being redistributed. The base case assumes 10 bps one-way transaction costs and is benchmarked against SPY using adjusted open-to-open returns.

## Robustness Testing

The Congressional result is tested across 54 specifications: 180, 365 and 730-day rolling windows; lower-bound and midpoint purchase-size weighting; 0, 10 and 25 bps transaction costs; and combined, House-only and Senate-only portfolios. These specifications are sensitivity tests rather than 54 statistically independent experiments.

## Interpretation

The study is designed as reproducible historical research, not as an institutional-grade execution model. Results remain subject to public-disclosure coverage, historical market-data availability, survivorship and delisting limitations, benchmark choice, and the absence of factor-neutral portfolio construction.