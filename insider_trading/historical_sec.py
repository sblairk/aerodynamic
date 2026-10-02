import os
import io
import zipfile
import requests
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

SEC_USER_AGENT = os.getenv("SEC_USER_AGENT")

if not SEC_USER_AGENT:
    raise RuntimeError(
        "Set SEC_USER_AGENT to a descriptive user agent "
        "including a contact email before running this script."
    )

HEADERS = {
    "User-Agent": SEC_USER_AGENT
}

START_YEAR = 2021
END_YEAR = 2025

DOWNLOAD_FOLDER = "sec_insider_data"
OUTPUT_FILE = "historical_form4_purchases_2021_2025.csv"

BASE_URL = (
    "https://www.sec.gov/files/structureddata/data/"
    "insider-transactions-data-sets/"
)


# ============================================================
# CREATE DOWNLOAD FOLDER
# ============================================================

os.makedirs(
    DOWNLOAD_FOLDER,
    exist_ok=True
)


# ============================================================
# DOWNLOAD ONE QUARTER
# ============================================================

def download_quarter(year, quarter):

    filename = (
        f"{year}q{quarter}_form345.zip"
    )

    url = BASE_URL + filename

    local_path = os.path.join(
        DOWNLOAD_FOLDER,
        filename
    )

    if os.path.exists(local_path):

        print(
            f"Already downloaded: {filename}"
        )

        return local_path

    print(
        f"Downloading {year} Q{quarter}..."
    )

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=120
    )

    response.raise_for_status()

    with open(
        local_path,
        "wb"
    ) as file:

        file.write(
            response.content
        )

    return local_path


# ============================================================
# LIST FILES INSIDE ZIP
# ============================================================

def inspect_zip(zip_path):

    with zipfile.ZipFile(
        zip_path,
        "r"
    ) as z:

        return z.namelist()


# ============================================================
# READ TAB FILE FROM ZIP
# ============================================================

def read_tab_file(
    zip_path,
    filename
):

    with zipfile.ZipFile(
        zip_path,
        "r"
    ) as z:

        with z.open(
            filename
        ) as file:

            df = pd.read_csv(
                file,
                sep="\t",
                dtype=str,
                low_memory=False
            )

    return df


# ============================================================
# FIND FILE BY NAME
# ============================================================

def find_file(
    file_list,
    keyword
):

    keyword = keyword.lower()

    for filename in file_list:

        if keyword in filename.lower():
            return filename

    return None


# ============================================================
# PROCESS ONE QUARTER
# ============================================================

def process_quarter(
    year,
    quarter
):

    zip_path = download_quarter(
        year,
        quarter
    )

    file_list = inspect_zip(
        zip_path
    )

    print(
        f"Files inside {year} Q{quarter}:"
    )

    for filename in file_list:
        print("  ", filename)

    submission_file = find_file(
        file_list,
        "submission"
    )

    owner_file = find_file(
        file_list,
        "reportingowner"
    )

    transaction_file = find_file(
        file_list,
        "nonderiv_trans"
    )

    if transaction_file is None:

        transaction_file = find_file(
            file_list,
            "nonderivative"
        )

    if (
        submission_file is None
        or owner_file is None
        or transaction_file is None
    ):

        print(
            f"Could not identify required files "
            f"for {year} Q{quarter}"
        )

        return pd.DataFrame()

    submissions = read_tab_file(
        zip_path,
        submission_file
    )

    owners = read_tab_file(
        zip_path,
        owner_file
    )

    transactions = read_tab_file(
        zip_path,
        transaction_file
    )

    print(
        f"Loaded {year} Q{quarter}: "
        f"{len(submissions):,} submissions, "
        f"{len(owners):,} owners, "
        f"{len(transactions):,} transactions"
    )

    submissions.columns = [
        c.upper().strip()
        for c in submissions.columns
    ]

    owners.columns = [
        c.upper().strip()
        for c in owners.columns
    ]

    transactions.columns = [
        c.upper().strip()
        for c in transactions.columns
    ]

    print("\nSubmission columns:")
    print(submissions.columns.tolist())

    print("\nOwner columns:")
    print(owners.columns.tolist())

    print("\nTransaction columns:")
    print(transactions.columns.tolist())

    if "ACCESSION_NUMBER" not in submissions.columns:

        print(
            "ACCESSION_NUMBER not found in submissions"
        )

        return pd.DataFrame()

    if "DOCUMENT_TYPE" in submissions.columns:

        submissions = submissions[
            submissions[
                "DOCUMENT_TYPE"
            ].astype(str).str.strip() == "4"
        ].copy()

    transaction_code_column = None

    possible_transaction_columns = [
        "TRANS_CODE",
        "TRANSACTION_CODE",
        "TRANSCODE"
    ]

    for col in possible_transaction_columns:

        if col in transactions.columns:
            transaction_code_column = col
            break

    if transaction_code_column is None:

        print(
            "Transaction code column not found."
        )

        return pd.DataFrame()

    transactions = transactions[
        transactions[
            transaction_code_column
        ].astype(str).str.strip() == "P"
    ].copy()

    if (
        "ACCESSION_NUMBER"
        not in transactions.columns
    ):

        print(
            "ACCESSION_NUMBER not found "
            "in transactions."
        )

        return pd.DataFrame()

    merged = transactions.merge(
        submissions,
        on="ACCESSION_NUMBER",
        how="inner",
        suffixes=(
            "_TRANS",
            "_SUB"
        )
    )

    if (
        "ACCESSION_NUMBER"
        in owners.columns
    ):

        merged = merged.merge(
            owners,
            on="ACCESSION_NUMBER",
            how="left",
            suffixes=(
                "",
                "_OWNER"
            )
        )

    merged[
        "SOURCE_YEAR"
    ] = year

    merged[
        "SOURCE_QUARTER"
    ] = quarter

    print(
        f"Open-market purchase rows: "
        f"{len(merged):,}"
    )

    return merged


# ============================================================
# MAIN
# ============================================================

all_quarters = []

for year in range(
    START_YEAR,
    END_YEAR + 1
):

    for quarter in range(
        1,
        5
    ):

        print(
            "\n"
            + "=" * 70
        )

        print(
            f"PROCESSING {year} Q{quarter}"
        )

        print(
            "=" * 70
        )

        try:

            quarter_df = process_quarter(
                year,
                quarter
            )

            if not quarter_df.empty:

                all_quarters.append(
                    quarter_df
                )

        except Exception as error:

            print(
                f"ERROR {year} Q{quarter}: "
                f"{error}"
            )


# ============================================================
# COMBINE HISTORY
# ============================================================

if not all_quarters:

    print(
        "\nNo data collected."
    )

    raise SystemExit


history = pd.concat(
    all_quarters,
    ignore_index=True,
    sort=False
)


duplicate_columns = [
    col
    for col in [
        "ACCESSION_NUMBER",
        "TRANS_DATE",
        "TRANS_SHARES",
        "TRANS_PRICEPERSHARE",
        "RPTOWNERCIK"
    ]
    if col in history.columns
]

if duplicate_columns:

    history = history.drop_duplicates(
        subset=duplicate_columns
    )


history.to_csv(
    OUTPUT_FILE,
    index=False
)


print(
    "\n"
    + "=" * 70
)

print(
    "HISTORICAL SEC DATA COMPLETE"
)

print(
    "=" * 70
)

print(
    f"Total open-market purchase rows: "
    f"{len(history):,}"
)

print(
    f"Saved to: {OUTPUT_FILE}"
)

print(
    "\nYears:"
)

print(
    history[
        "SOURCE_YEAR"
    ].value_counts()
    .sort_index()
)

print(
    "\nDone."
)
