import pandas as pd
import numpy as np
from collections import defaultdict


# ============================================================
# CONFIG
# ============================================================

INPUT_FILE = "historical_form4_purchases_2021_2025.csv"
OUTPUT_FILE = "historical_scored_buys_2021_2025.csv"

CLUSTER_WINDOW_DAYS = 14
MAX_FILING_LAG_DAYS = 10

MIN_PRICE = 0.01
MAX_PRICE = 10_000

MIN_PURCHASE_VALUE = 10_000
MAX_PURCHASE_VALUE = 100_000_000


# ============================================================
# LOAD
# ============================================================

print("Loading historical SEC data...")

df = pd.read_csv(
    INPUT_FILE,
    low_memory=False
)

print(f"Raw rows: {len(df):,}")


# ============================================================
# CLEAN DATES
# ============================================================

print("Cleaning dates...")

df["TRANS_DATE"] = pd.to_datetime(
    df["TRANS_DATE"],
    errors="coerce"
)

df["FILING_DATE"] = pd.to_datetime(
    df["FILING_DATE"],
    errors="coerce"
)

df = df.dropna(
    subset=[
        "ISSUERTRADINGSYMBOL",
        "TRANS_DATE",
        "FILING_DATE",
        "RPTOWNERNAME"
    ]
).copy()


# ============================================================
# FILING LAG
# ============================================================

df["FILING_LAG_DAYS"] = (
    df["FILING_DATE"]
    - df["TRANS_DATE"]
).dt.days

df = df[
    (
        df["FILING_LAG_DAYS"] >= 0
    )
    &
    (
        df["FILING_LAG_DAYS"]
        <= MAX_FILING_LAG_DAYS
    )
].copy()

print(
    f"Rows after filing-lag filter: "
    f"{len(df):,}"
)


# ============================================================
# CLEAN TICKERS
# ============================================================

df["ISSUERTRADINGSYMBOL"] = (
    df["ISSUERTRADINGSYMBOL"]
    .astype(str)
    .str.strip()
    .str.upper()
)

# Keep simple exchange-style ticker formats:
# letters/numbers plus . or -
df = df[
    df["ISSUERTRADINGSYMBOL"].str.match(
        r"^[A-Z0-9]{1,6}([.-][A-Z0-9]{1,3})?$",
        na=False
    )
].copy()

print(
    f"Rows after ticker-format filter: "
    f"{len(df):,}"
)


# ============================================================
# NUMERIC FIELDS
# ============================================================

print("Converting numeric fields...")

numeric_columns = [
    "TRANS_SHARES",
    "TRANS_PRICEPERSHARE",
    "SHRS_OWND_FOLWNG_TRANS"
]

for column in numeric_columns:

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )


# ============================================================
# REMOVE DUPLICATES
# ============================================================

print("Removing duplicate SEC rows...")

duplicate_columns = [
    col
    for col in [
        "ACCESSION_NUMBER",
        "RPTOWNERCIK",
        "TRANS_DATE",
        "TRANS_SHARES",
        "TRANS_PRICEPERSHARE"
    ]
    if col in df.columns
]

if duplicate_columns:

    df = df.drop_duplicates(
        subset=duplicate_columns
    )

print(
    f"Rows after deduplication: "
    f"{len(df):,}"
)


# ============================================================
# RAW TRANSACTION SANITY FILTERS
# ============================================================

print("Applying transaction sanity filters...")

df = df[
    df["TRANS_SHARES"].notna()
    &
    df["TRANS_PRICEPERSHARE"].notna()
    &
    (df["TRANS_SHARES"] > 0)
    &
    (df["TRANS_PRICEPERSHARE"] >= MIN_PRICE)
    &
    (df["TRANS_PRICEPERSHARE"] <= MAX_PRICE)
].copy()

df["VALUE"] = (
    df["TRANS_SHARES"]
    * df["TRANS_PRICEPERSHARE"]
)

df = df[
    (df["VALUE"] >= MIN_PURCHASE_VALUE)
    &
    (df["VALUE"] <= MAX_PURCHASE_VALUE)
].copy()

print(
    f"Rows after price/value filters: "
    f"{len(df):,}"
)


# ============================================================
# HOLDINGS
# ============================================================

df["SHARES_BEFORE"] = (
    df["SHRS_OWND_FOLWNG_TRANS"]
    - df["TRANS_SHARES"]
)

df["HOLDINGS_CHANGE_PCT"] = np.where(
    df["SHARES_BEFORE"] > 0,
    df["TRANS_SHARES"]
    / df["SHARES_BEFORE"],
    np.nan
)


# ============================================================
# 10b5-1
# ============================================================

def parse_10b5(value):

    if pd.isna(value):
        return False

    return (
        str(value)
        .strip()
        .lower()
        in [
            "1",
            "true",
            "yes"
        ]
    )


if "AFF10B5ONE" in df.columns:

    df["IS_10B5_1"] = (
        df["AFF10B5ONE"]
        .apply(parse_10b5)
    )

else:

    df["IS_10B5_1"] = False


# ============================================================
# ROLE CLASSIFICATION
# ============================================================

print("Classifying insiders...")


def classify_role(row):

    relationship = str(
        row.get(
            "RPTOWNER_RELATIONSHIP",
            ""
        )
    ).lower()

    title = str(
        row.get(
            "RPTOWNER_TITLE",
            ""
        )
    ).lower()

    if (
        "chief executive" in title
        or "ceo" in title
    ):
        return "Management", "CEO"

    if (
        "chief financial" in title
        or "cfo" in title
    ):
        return "Management", "CFO"

    if (
        "chief operating" in title
        or "coo" in title
    ):
        return "Management", "COO"

    if "president" in title:
        return "Management", "President"

    if (
        "chairman" in title
        or "chair" in title
    ):
        return "Management", "Chairman"

    if "officer" in relationship:
        return "Management", "Other Executive"

    if (
        "director" in relationship
        and
        "tenpercentowner"
        not in relationship
    ):
        return "Director", "Director"

    if "tenpercentowner" in relationship:
        return "Large Shareholder", "10% Owner"

    return "Other", "Other"


roles = df.apply(
    classify_role,
    axis=1,
    result_type="expand"
)

roles.columns = [
    "INSIDER_CATEGORY",
    "ROLE"
]

df[
    [
        "INSIDER_CATEGORY",
        "ROLE"
    ]
] = roles


# ============================================================
# STRATEGY UNIVERSE
# ============================================================

df = df[
    df[
        "INSIDER_CATEGORY"
    ].isin(
        [
            "Management",
            "Director"
        ]
    )
].copy()

print(
    f"Management/director rows: "
    f"{len(df):,}"
)


# ============================================================
# NORMALIZE INSIDER
# ============================================================

df["INSIDER_NORMALIZED"] = (
    df["RPTOWNERNAME"]
    .astype(str)
    .str.upper()
    .str.replace(
        r"\s+",
        " ",
        regex=True
    )
    .str.strip()
)


# ============================================================
# AGGREGATE SAME INSIDER / SAME DAY
# ============================================================

print("Aggregating same-day purchases...")

group_columns = [
    "ISSUERTRADINGSYMBOL",
    "ISSUERNAME",
    "ISSUERCIK",
    "RPTOWNERCIK",
    "RPTOWNERNAME",
    "INSIDER_NORMALIZED",
    "RPTOWNER_TITLE",
    "INSIDER_CATEGORY",
    "ROLE",
    "TRANS_DATE",
    "FILING_DATE",
    "IS_10B5_1"
]


signals = (
    df.groupby(
        group_columns,
        dropna=False,
        sort=False
    )
    .agg(
        Shares=(
            "TRANS_SHARES",
            "sum"
        ),
        Value=(
            "VALUE",
            "sum"
        ),
        Shares_Before=(
            "SHARES_BEFORE",
            "first"
        ),
        Shares_After=(
            "SHRS_OWND_FOLWNG_TRANS",
            "last"
        ),
        Filing_Lag_Days=(
            "FILING_LAG_DAYS",
            "min"
        )
    )
    .reset_index()
)


signals = signals.rename(
    columns={
        "ISSUERTRADINGSYMBOL":
            "Ticker",
        "ISSUERNAME":
            "Company",
        "ISSUERCIK":
            "Issuer CIK",
        "RPTOWNERCIK":
            "Insider CIK",
        "RPTOWNERNAME":
            "Insider",
        "INSIDER_NORMALIZED":
            "Insider Normalized",
        "RPTOWNER_TITLE":
            "Title",
        "INSIDER_CATEGORY":
            "Insider Category",
        "ROLE":
            "Role",
        "TRANS_DATE":
            "Transaction Date",
        "FILING_DATE":
            "Filing Date",
        "IS_10B5_1":
            "10b5-1",
        "Shares_Before":
            "Shares Before",
        "Shares_After":
            "Shares After",
        "Filing_Lag_Days":
            "Filing Lag Days"
    }
)


# ============================================================
# RECOMPUTE AGGREGATED HOLDINGS CHANGE
# ============================================================

signals[
    "Holdings Change %"
] = np.where(
    signals[
        "Shares Before"
    ] > 0,
    signals[
        "Shares"
    ]
    /
    signals[
        "Shares Before"
    ],
    np.nan
)


# ============================================================
# POST-AGGREGATION SANITY CHECK
# ============================================================

signals = signals[
    (signals["Value"] >= MIN_PURCHASE_VALUE)
    &
    (signals["Value"] <= MAX_PURCHASE_VALUE)
].copy()


# ============================================================
# SORT BY INFORMATION DATE
# ============================================================

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
    f"Aggregated clean signals: "
    f"{len(signals):,}"
)


# ============================================================
# BACKWARD-LOOKING CLUSTERS
# ============================================================

print(
    "Calculating backward-looking "
    "14-day filing clusters..."
)

cluster_insider_count = np.ones(
    len(signals),
    dtype=int
)

cluster_value = np.zeros(
    len(signals),
    dtype=float
)

cluster_ceo = np.zeros(
    len(signals),
    dtype=bool
)

cluster_cfo = np.zeros(
    len(signals),
    dtype=bool
)


ticker_groups = list(
    signals.groupby(
        "Ticker",
        sort=False
    )
)

total_tickers = len(
    ticker_groups
)


for ticker_number, (
    ticker,
    group
) in enumerate(
    ticker_groups,
    start=1
):

    if ticker_number % 250 == 0:

        print(
            f"  Cluster progress: "
            f"{ticker_number:,}/"
            f"{total_tickers:,} tickers"
        )

    idx = group.index.to_numpy()

    filing_dates = (
        group[
            "Filing Date"
        ]
        .values
        .astype(
            "datetime64[D]"
        )
    )

    insiders = (
        group[
            "Insider Normalized"
        ]
        .astype(str)
        .to_numpy()
    )

    values = (
        group["Value"]
        .fillna(0)
        .to_numpy(
            dtype=float
        )
    )

    roles_array = (
        group["Role"]
        .fillna("")
        .to_numpy()
    )

    n = len(group)

    left = 0

    insider_counts = defaultdict(
        int
    )

    unique_insiders = 0
    current_value = 0.0
    ceo_count = 0
    cfo_count = 0


    for i in range(n):

        current_date = (
            filing_dates[i]
        )

        lower_bound = (
            current_date
            - np.timedelta64(
                CLUSTER_WINDOW_DAYS,
                "D"
            )
        )

        insider = insiders[i]

        if (
            insider_counts[
                insider
            ] == 0
        ):
            unique_insiders += 1

        insider_counts[
            insider
        ] += 1

        current_value += (
            values[i]
        )

        if roles_array[i] == "CEO":
            ceo_count += 1

        if roles_array[i] == "CFO":
            cfo_count += 1


        while (
            left <= i
            and
            filing_dates[left]
            < lower_bound
        ):

            old_insider = (
                insiders[left]
            )

            insider_counts[
                old_insider
            ] -= 1

            if (
                insider_counts[
                    old_insider
                ] == 0
            ):
                unique_insiders -= 1

            current_value -= (
                values[left]
            )

            if (
                roles_array[left]
                == "CEO"
            ):
                ceo_count -= 1

            if (
                roles_array[left]
                == "CFO"
            ):
                cfo_count -= 1

            left += 1


        global_index = idx[i]

        cluster_insider_count[
            global_index
        ] = unique_insiders

        cluster_value[
            global_index
        ] = current_value

        cluster_ceo[
            global_index
        ] = (
            ceo_count > 0
        )

        cluster_cfo[
            global_index
        ] = (
            cfo_count > 0
        )


signals[
    "Cluster Insider Count"
] = cluster_insider_count

signals[
    "Cluster Value"
] = cluster_value

signals[
    "Cluster CEO"
] = cluster_ceo

signals[
    "Cluster CFO"
] = cluster_cfo


# ============================================================
# SCORE FUNCTIONS
# ============================================================

print("Calculating conviction scores...")


def score_value(value):

    if pd.isna(value):
        return 0

    if value < 100_000:
        return 0

    if value < 250_000:
        return 1

    if value < 500_000:
        return 2

    if value < 1_000_000:
        return 3

    if value < 5_000_000:
        return 4

    return 5


def score_holdings(value):

    if pd.isna(value):
        return 0

    if value < 0.02:
        return 0

    if value < 0.05:
        return 1

    if value < 0.10:
        return 2

    if value < 0.25:
        return 3

    if value < 0.50:
        return 4

    return 5


ROLE_SCORES = {
    "CEO": 4,
    "CFO": 4,
    "Chairman": 3,
    "President": 3,
    "COO": 3,
    "Other Executive": 2,
    "Director": 1
}


signals[
    "Value Score"
] = (
    signals["Value"]
    .apply(
        score_value
    )
)

signals[
    "Holdings Score"
] = (
    signals[
        "Holdings Change %"
    ]
    .apply(
        score_holdings
    )
)

signals[
    "Role Score"
] = (
    signals["Role"]
    .map(
        ROLE_SCORES
    )
    .fillna(0)
    .astype(int)
)


# ============================================================
# CLUSTER SCORE
# ============================================================

n = signals[
    "Cluster Insider Count"
]

signals[
    "Cluster Score"
] = np.select(
    [
        n >= 4,
        n == 3,
        n == 2
    ],
    [
        5,
        4,
        2
    ],
    default=0
)

executive_cluster = (
    signals[
        "Cluster CEO"
    ]
    |
    signals[
        "Cluster CFO"
    ]
)

signals.loc[
    (
        signals[
            "Cluster Score"
        ] > 0
    )
    &
    executive_cluster,
    "Cluster Score"
] += 1

signals[
    "Cluster Score"
] = (
    signals[
        "Cluster Score"
    ]
    .clip(
        upper=5
    )
)


# ============================================================
# 10b5-1
# ============================================================

signals[
    "10b5-1 Penalty"
] = np.where(
    signals["10b5-1"],
    -5,
    0
)


# ============================================================
# TOTAL SCORE
# ============================================================

signals[
    "Conviction Score"
] = (
    signals[
        "Value Score"
    ]
    +
    signals[
        "Holdings Score"
    ]
    +
    signals[
        "Role Score"
    ]
    +
    signals[
        "Cluster Score"
    ]
    +
    signals[
        "10b5-1 Penalty"
    ]
)


signals[
    "Conviction"
] = pd.cut(
    signals[
        "Conviction Score"
    ],
    bins=[
        -np.inf,
        5,
        8,
        11,
        14,
        np.inf
    ],
    labels=[
        "Ignore",
        "Weak",
        "Moderate",
        "Strong",
        "Very Strong"
    ]
)


signals[
    "Holdings Change % Display"
] = (
    signals[
        "Holdings Change %"
    ]
    * 100
)


# ============================================================
# SAVE
# ============================================================

signals = signals.sort_values(
    by=[
        "Conviction Score",
        "Filing Date",
        "Value"
    ],
    ascending=[
        False,
        True,
        False
    ]
)

signals.to_csv(
    OUTPUT_FILE,
    index=False
)


print(
    "\n"
    + "=" * 60
)

print(
    "CLEAN HISTORICAL SCORING COMPLETE"
)

print(
    "=" * 60
)

print(
    f"\nSignals: "
    f"{len(signals):,}"
)

print(
    "\nConviction distribution:"
)

print(
    signals[
        "Conviction"
    ]
    .value_counts(
        sort=False
    )
)

print(
    "\nValue statistics:"
)

print(
    signals["Value"]
    .describe(
        percentiles=[
            0.50,
            0.90,
            0.95,
            0.99
        ]
    )
)

print(
    f"\nSaved to: "
    f"{OUTPUT_FILE}"
)
