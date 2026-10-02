import pandas as pd
import numpy as np
import yfinance as yf


# ============================================================
# CONFIG
# ============================================================

INPUT_FILE = "historical_scored_buys_2021_2025.csv"
OUTPUT_FILE = "event_backtest_results.csv"

MIN_SCORE = 12
MIN_ENTRY_PRICE = 5.00

BENCHMARK = "SPY"

START_DATE = "2021-01-01"
END_DATE = "2026-01-01"

COOLDOWN_DAYS = 14

FORWARD_WINDOWS = {
    "20D": 20,
    "60D": 60,
    "120D": 120
}


# ============================================================
# LOAD SIGNALS
# ============================================================

print("Loading scored signals...")

signals = pd.read_csv(
    INPUT_FILE,
    low_memory=False
)

signals["Filing Date"] = pd.to_datetime(
    signals["Filing Date"],
    errors="coerce"
)

signals = signals.dropna(
    subset=[
        "Ticker",
        "Filing Date",
        "Conviction Score"
    ]
).copy()

signals["Ticker"] = (
    signals["Ticker"]
    .astype(str)
    .str.strip()
    .str.upper()
)

signals = signals[
    signals["Conviction Score"] >= MIN_SCORE
].copy()

signals = signals.sort_values(
    by=[
        "Ticker",
        "Filing Date",
        "Transaction Date"
    ]
).reset_index(
    drop=True
)

print(
    f"Eligible filing-level signals: "
    f"{len(signals):,}"
)


# ============================================================
# NORMALIZE YAHOO TICKERS
# ============================================================

def normalize_yf_ticker(ticker):

    return (
        ticker
        .strip()
        .upper()
        .replace(".", "-")
    )


signals["YF Ticker"] = (
    signals["Ticker"]
    .apply(normalize_yf_ticker)
)


# ============================================================
# CREATE POINT-IN-TIME EVENTS
# ============================================================

print(
    "Creating point-in-time events "
    "with 14-day ticker cooldown..."
)

event_rows = []

for ticker, group in signals.groupby(
    "Ticker",
    sort=False
):

    group = group.sort_values(
        by=[
            "Filing Date",
            "Transaction Date"
        ]
    )

    cooldown_until = None

    for _, signal in group.iterrows():

        filing_date = signal[
            "Filing Date"
        ]

        if (
            cooldown_until is not None
            and filing_date <= cooldown_until
        ):
            continue

        event = signal.to_dict()

        event[
            "Signal Date"
        ] = filing_date

        event[
            "Cooldown Until"
        ] = (
            filing_date
            + pd.Timedelta(
                days=COOLDOWN_DAYS
            )
        )

        event_rows.append(
            event
        )

        cooldown_until = (
            filing_date
            + pd.Timedelta(
                days=COOLDOWN_DAYS
            )
        )


events = pd.DataFrame(
    event_rows
)

print(
    f"Point-in-time events created: "
    f"{len(events):,}"
)


# ============================================================
# PRICE DOWNLOAD
# ============================================================

unique_tickers = sorted(
    events[
        "YF Ticker"
    ]
    .dropna()
    .unique()
)

print(
    f"Unique tickers to download: "
    f"{len(unique_tickers):,}"
)

price_cache = {}
failed_tickers = []

for i, ticker in enumerate(
    unique_tickers,
    start=1
):

    if (
        i % 50 == 0
        or i == 1
    ):
        print(
            f"Downloading "
            f"{i:,}/"
            f"{len(unique_tickers):,}: "
            f"{ticker}"
        )

    try:
        data = yf.download(
            ticker,
            start=START_DATE,
            end=END_DATE,
            auto_adjust=False,
            progress=False,
            multi_level_index=False
        )

        if data.empty:
            failed_tickers.append(ticker)
            continue

        data = data.sort_index()
        data.index = pd.to_datetime(data.index)
        price_cache[ticker] = data

    except Exception as error:
        print(f"Failed {ticker}: {error}")
        failed_tickers.append(ticker)

print(
    f"\nDownloaded price history for "
    f"{len(price_cache):,} tickers"
)

print(
    f"Failed tickers: "
    f"{len(failed_tickers):,}"
)


# ============================================================
# DOWNLOAD BENCHMARK
# ============================================================

print(
    f"\nDownloading benchmark "
    f"{BENCHMARK}..."
)

benchmark_data = yf.download(
    BENCHMARK,
    start=START_DATE,
    end=END_DATE,
    auto_adjust=False,
    progress=False,
    multi_level_index=False
)

benchmark_data = benchmark_data.sort_index()
benchmark_data.index = pd.to_datetime(benchmark_data.index)


# ============================================================
# HELPERS
# ============================================================

def get_price(data, column, position):
    try:
        value = data[column].iloc[position]
        return float(value)
    except Exception:
        return None


def find_next_trading_day(data, signal_date):
    dates = data.index.normalize()
    target_date = pd.Timestamp(signal_date).normalize()
    positions = np.where(dates > target_date)[0]

    if len(positions) == 0:
        return None

    return int(positions[0])


def find_date_position(data, target_date):
    dates = data.index.normalize()
    target_date = pd.Timestamp(target_date).normalize()
    positions = np.where(dates >= target_date)[0]

    if len(positions) == 0:
        return None

    return int(positions[0])


def adverse_excursion_from_entry(
    data,
    entry_position,
    trading_days
):
    end_position = entry_position + trading_days

    if end_position >= len(data):
        return None

    closes = (
        data["Close"]
        .iloc[entry_position:end_position + 1]
        .astype(float)
    )

    if len(closes) == 0:
        return None

    entry_price = get_price(
        data,
        "Open",
        entry_position
    )

    if entry_price is None or entry_price <= 0:
        return None

    minimum_price = float(closes.min())

    return minimum_price / entry_price - 1


# ============================================================
# RUN BACKTEST
# ============================================================

print("\nRunning point-in-time event backtest...")

results = []

skipped_missing_price = 0
skipped_low_price = 0
skipped_missing_benchmark = 0

for i, event in events.iterrows():

    if (i + 1) % 250 == 0:
        print(
            f"Progress: "
            f"{i + 1:,}/"
            f"{len(events):,}"
        )

    ticker = event["YF Ticker"]

    if ticker not in price_cache:
        skipped_missing_price += 1
        continue

    stock_data = price_cache[ticker]
    signal_date = event["Signal Date"]

    entry_position = find_next_trading_day(
        stock_data,
        signal_date
    )

    if entry_position is None:
        skipped_missing_price += 1
        continue

    entry_date = stock_data.index[entry_position]
    entry_price = get_price(
        stock_data,
        "Open",
        entry_position
    )

    if entry_price is None or entry_price <= 0:
        skipped_missing_price += 1
        continue

    if entry_price < MIN_ENTRY_PRICE:
        skipped_low_price += 1
        continue

    benchmark_entry_position = find_date_position(
        benchmark_data,
        entry_date
    )

    if benchmark_entry_position is None:
        skipped_missing_benchmark += 1
        continue

    benchmark_entry_price = get_price(
        benchmark_data,
        "Open",
        benchmark_entry_position
    )

    if (
        benchmark_entry_price is None
        or benchmark_entry_price <= 0
    ):
        skipped_missing_benchmark += 1
        continue

    result = event.to_dict()
    result["Entry Date"] = entry_date.date()
    result["Entry Price"] = entry_price

    for label, days in FORWARD_WINDOWS.items():

        stock_exit_position = entry_position + days
        benchmark_exit_position = (
            benchmark_entry_position + days
        )

        if (
            stock_exit_position >= len(stock_data)
            or benchmark_exit_position >= len(benchmark_data)
        ):
            result[f"{label} Return"] = np.nan
            result[f"{label} SPY Return"] = np.nan
            result[f"{label} Excess Return"] = np.nan
            result[f"{label} Adverse Excursion"] = np.nan
            continue

        stock_exit_price = get_price(
            stock_data,
            "Close",
            stock_exit_position
        )

        benchmark_exit_price = get_price(
            benchmark_data,
            "Close",
            benchmark_exit_position
        )

        if (
            stock_exit_price is None
            or benchmark_exit_price is None
        ):
            result[f"{label} Return"] = np.nan
            result[f"{label} SPY Return"] = np.nan
            result[f"{label} Excess Return"] = np.nan
            result[f"{label} Adverse Excursion"] = np.nan
            continue

        stock_return = stock_exit_price / entry_price - 1
        benchmark_return = (
            benchmark_exit_price
            / benchmark_entry_price
            - 1
        )
        excess_return = stock_return - benchmark_return

        result[f"{label} Return"] = stock_return
        result[f"{label} SPY Return"] = benchmark_return
        result[f"{label} Excess Return"] = excess_return
        result[f"{label} Adverse Excursion"] = (
            adverse_excursion_from_entry(
                stock_data,
                entry_position,
                days
            )
        )

    results.append(result)


# ============================================================
# RESULTS DATAFRAME
# ============================================================

backtest = pd.DataFrame(results)

if backtest.empty:
    print("\nNo valid point-in-time backtest results.")
    raise SystemExit

backtest.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# OVERALL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("POINT-IN-TIME EVENT BACKTEST")
print("=" * 70)

for label in FORWARD_WINDOWS:
    return_col = f"{label} Return"
    excess_col = f"{label} Excess Return"

    valid = backtest.dropna(
        subset=[return_col, excess_col]
    )

    if valid.empty:
        continue

    positive_rate = (valid[return_col] > 0).mean()
    beat_rate = (valid[excess_col] > 0).mean()

    print(f"\n{label}")
    print(f"N: {len(valid):,}")
    print(f"Average Return: {valid[return_col].mean():.2%}")
    print(f"Median Return: {valid[return_col].median():.2%}")
    print(f"Positive Hit Rate: {positive_rate:.2%}")
    print(
        f"Average Excess vs SPY: "
        f"{valid[excess_col].mean():.2%}"
    )
    print(
        f"Median Excess vs SPY: "
        f"{valid[excess_col].median():.2%}"
    )
    print(f"Beat SPY Rate: {beat_rate:.2%}")


# ============================================================
# SUMMARY FUNCTION
# ============================================================

def make_summary(data, group_column):
    metrics = [
        "20D Return",
        "20D Excess Return",
        "60D Return",
        "60D Excess Return",
        "120D Return",
        "120D Excess Return"
    ]

    return (
        data.groupby(group_column)[metrics]
        .agg(["count", "mean", "median"])
    )


# ============================================================
# GROUPED SUMMARIES
# ============================================================

print("\n" + "=" * 70)
print("BY CONVICTION SCORE")
print("=" * 70)
score_summary = make_summary(
    backtest,
    "Conviction Score"
)
print(score_summary.to_string())
score_summary.to_csv("event_summary_by_score.csv")

print("\n" + "=" * 70)
print("BY ROLE")
print("=" * 70)
role_summary = make_summary(
    backtest,
    "Role"
)
print(role_summary.to_string())
role_summary.to_csv("event_summary_by_role.csv")

print("\n" + "=" * 70)
print("BY CLUSTER INSIDER COUNT")
print("=" * 70)
cluster_summary = make_summary(
    backtest,
    "Cluster Insider Count"
)
print(cluster_summary.to_string())
cluster_summary.to_csv("event_summary_by_cluster.csv")


# ============================================================
# COVERAGE
# ============================================================

print("\n" + "=" * 70)
print("POINT-IN-TIME COVERAGE")
print("=" * 70)

print(
    f"Eligible filing-level signals: "
    f"{len(signals):,}"
)
print(
    f"Point-in-time events after cooldown: "
    f"{len(events):,}"
)
print(
    f"Valid backtest observations: "
    f"{len(backtest):,}"
)

coverage_rate = (
    len(backtest) / len(events)
    if len(events) > 0
    else 0
)

print(f"Event coverage rate: {coverage_rate:.2%}")
print(f"Failed Yahoo tickers: {len(failed_tickers):,}")
print(
    f"Skipped for missing price/history: "
    f"{skipped_missing_price:,}"
)
print(
    f"Skipped for entry price below "
    f"${MIN_ENTRY_PRICE:.2f}: "
    f"{skipped_low_price:,}"
)
print(
    f"Skipped for benchmark issue: "
    f"{skipped_missing_benchmark:,}"
)
print(
    f"Minimum entry price in results: "
    f"${backtest['Entry Price'].min():,.2f}"
)
print(
    f"Maximum signal purchase value: "
    f"${backtest['Value'].max():,.2f}"
)

print("\nSaved:")
print("event_backtest_results.csv")
print("event_summary_by_score.csv")
print("event_summary_by_role.csv")
print("event_summary_by_cluster.csv")
