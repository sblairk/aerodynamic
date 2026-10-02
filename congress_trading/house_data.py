from __future__ import annotations

import argparse
import io
import os
import re
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests
from pypdf import PdfReader


START_YEAR = 2020
END_YEAR = 2026

BASE_URL = (
    "https://disclosures-clerk.house.gov/"
    "public_disc/financial-pdfs/"
)
PDF_BASE_URL = (
    "https://disclosures-clerk.house.gov/"
    "public_disc/ptr-pdfs/"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 Aerodynamic congressional trading research"
    )
}

REQUEST_DELAY = 0.10

STOCK_TAG_PATTERN = re.compile(
    r"\[\s*S\s*T\s*\]",
    flags=re.I,
)

TICKER_PATTERN = re.compile(
    r"\("
    r"([A-Za-z][A-Za-z0-9.\-]{0,11})"
    r"\)"
    r"\s*$",
    flags=re.I,
)

TRANSACTION_PATTERN = re.compile(
    r"^\s*"
    r"(?P<transaction_type>P|S|E)"
    r"(?:\s*\((?P<transaction_detail>[^)]{1,30})\))?"
    r"\s+"
    r"(?P<transaction_date>\d{1,2}/\d{1,2}/\d{2,4})"
    r"\s+"
    r"(?P<notification_date>\d{1,2}/\d{1,2}/\d{2,4})"
    r"\s+"
    r"(?P<amount>"
    r"(?:"
    r"\$[\d,]+\s*-\s*\$[\d,]+"
    r"|Over\s+\$[\d,]+"
    r"|>\s*\$[\d,]+"
    r"|\$[\d,]+\s*\+"
    r"|\$[\d,]+"
    r")"
    r")",
    flags=re.I,
)


def project_root() -> Path:
    here = Path(__file__).resolve().parent
    return here.parent if here.name == "congress_trading" else here


ROOT = project_root()
DOWNLOAD_FOLDER = ROOT / "congress_house_data"
PDF_CACHE_FOLDER = ROOT / "congress_house_pdf_cache"

FILINGS_FILE = ROOT / "congress_house_filings_2020_2026.csv"
PTR_FILE = ROOT / "congress_house_ptr_index_2020_2026.csv"
TRANSACTIONS_FILE = ROOT / "congress_house_stock_transactions_2020_2026.csv"
CLEAN_FILE = ROOT / "congress_house_clean_purchases_2020_2026.csv"


def download_year(year: int) -> Path:
    DOWNLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

    filename = f"{year}FD.zip"
    url = BASE_URL + filename
    local_path = DOWNLOAD_FOLDER / filename

    if local_path.exists():
        print(f"Already downloaded: {filename}")
        return local_path

    print(f"Downloading House disclosures for {year}...")
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=120,
    )
    response.raise_for_status()
    local_path.write_bytes(response.content)
    return local_path


def read_year_index(zip_path: Path, year: int) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path, "r") as archive:
        filenames = archive.namelist()
        txt_files = [
            name
            for name in filenames
            if name.lower().endswith(".txt")
        ]

        if not txt_files:
            raise RuntimeError(
                f"No TXT filing index found in {zip_path.name}"
            )

        index_name = txt_files[0]
        with archive.open(index_name) as file:
            df = pd.read_csv(
                file,
                sep="\t",
                dtype=str,
                low_memory=False,
            )

    df["FILING_YEAR"] = year
    return df


def build_filing_index(reuse_existing: bool = True) -> pd.DataFrame:
    if reuse_existing and FILINGS_FILE.exists():
        print(f"Reusing: {FILINGS_FILE.name}")
        return pd.read_csv(FILINGS_FILE, low_memory=False)

    all_years = []

    for year in range(START_YEAR, END_YEAR + 1):
        print(f"\nProcessing House {year}")
        zip_path = download_year(year)
        year_df = read_year_index(zip_path, year)
        print(f"Rows loaded: {len(year_df):,}")
        all_years.append(year_df)

    if not all_years:
        raise RuntimeError("No House filings collected.")

    house = pd.concat(
        all_years,
        ignore_index=True,
        sort=False,
    )

    house.columns = [
        str(column)
        .strip()
        .upper()
        .replace(" ", "_")
        for column in house.columns
    ]

    house.to_csv(FILINGS_FILE, index=False)

    print("\n" + "=" * 70)
    print("HOUSE DISCLOSURE INDEX COMPLETE")
    print("=" * 70)
    print(f"Total filings: {len(house):,}")
    print(f"Saved to: {FILINGS_FILE.name}")

    return house


def build_name(row: pd.Series) -> str:
    parts = []

    if pd.notna(row.get("FIRST")):
        parts.append(str(row["FIRST"]).strip())

    if pd.notna(row.get("LAST")):
        parts.append(str(row["LAST"]).strip())

    return " ".join(parts)


def build_ptr_index(
    filings: pd.DataFrame,
    reuse_existing: bool = True,
) -> pd.DataFrame:
    if reuse_existing and PTR_FILE.exists():
        print(f"Reusing: {PTR_FILE.name}")
        ptr = pd.read_csv(PTR_FILE, low_memory=False)
        ptr["FILINGDATE"] = pd.to_datetime(
            ptr["FILINGDATE"],
            errors="coerce",
        )
        return ptr

    ptr = filings[
        filings["FILINGTYPE"]
        .astype(str)
        .str.strip()
        .str.upper()
        .eq("P")
    ].copy()

    ptr["FILINGDATE"] = pd.to_datetime(
        ptr["FILINGDATE"],
        errors="coerce",
    )

    ptr = ptr.dropna(
        subset=["FILINGDATE", "DOCID"]
    ).copy()

    ptr["POLITICIAN"] = ptr.apply(
        build_name,
        axis=1,
    )

    ptr["DOCID"] = (
        ptr["DOCID"]
        .astype(str)
        .str.replace(".0", "", regex=False)
        .str.strip()
    )

    ptr["SOURCE_URL"] = (
        PDF_BASE_URL
        + ptr["FILING_YEAR"].astype(str)
        + "/"
        + ptr["DOCID"]
        + ".pdf"
    )

    output_columns = [
        "POLITICIAN",
        "FIRST",
        "LAST",
        "STATEDST",
        "FILINGDATE",
        "DOCID",
        "FILING_YEAR",
        "SOURCE_URL",
    ]

    ptr = (
        ptr[output_columns]
        .sort_values("FILINGDATE")
        .reset_index(drop=True)
    )

    ptr.to_csv(PTR_FILE, index=False)

    print("\n" + "=" * 70)
    print("HOUSE PTR INDEX COMPLETE")
    print("=" * 70)
    print(f"PTR filings: {len(ptr):,}")
    print(
        f"Date range: "
        f"{ptr['FILINGDATE'].min().date()} "
        f"to {ptr['FILINGDATE'].max().date()}"
    )
    print(f"Saved to: {PTR_FILE.name}")

    return ptr


def get_pdf_bytes(docid: str, url: str) -> bytes:
    PDF_CACHE_FOLDER.mkdir(parents=True, exist_ok=True)

    local_path = PDF_CACHE_FOLDER / f"{docid}.pdf"

    if local_path.exists():
        return local_path.read_bytes()

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=60,
    )
    response.raise_for_status()

    pdf_bytes = response.content
    local_path.write_bytes(pdf_bytes)
    time.sleep(REQUEST_DELAY)

    return pdf_bytes


def extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))

    pages = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append(text)

    return "\n".join(pages)


def normalize_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = text.replace("\r", "\n")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_stock_transactions(raw_text: str):
    text = normalize_text(raw_text)
    results = []

    stock_tags = list(
        STOCK_TAG_PATTERN.finditer(text)
    )

    for tag in stock_tags:
        after = text[
            tag.end():
            tag.end() + 300
        ]

        transaction_match = (
            TRANSACTION_PATTERN.match(after)
        )

        if not transaction_match:
            continue

        before = text[
            max(0, tag.start() - 350):
            tag.start()
        ]

        ticker_match = TICKER_PATTERN.search(before)

        ticker = None
        if ticker_match:
            ticker = (
                ticker_match
                .group(1)
                .upper()
                .strip()
            )

        asset_context = before[-220:].strip()

        if ticker_match:
            start_position = max(
                0,
                ticker_match.start() - 170,
            )
            asset_context = before[
                start_position:
            ].strip()

        transaction_type = (
            transaction_match
            .group("transaction_type")
            .upper()
        )

        detail = (
            transaction_match
            .group("transaction_detail")
        )
        if detail:
            detail = detail.strip()

        results.append(
            {
                "TICKER": ticker,
                "TRANSACTION_TYPE": transaction_type,
                "TRANSACTION_DETAIL": detail,
                "TRANSACTION_DATE":
                    transaction_match.group(
                        "transaction_date"
                    ),
                "NOTIFICATION_DATE":
                    transaction_match.group(
                        "notification_date"
                    ),
                "AMOUNT_RANGE":
                    transaction_match.group(
                        "amount"
                    ),
                "ASSET_CONTEXT": asset_context,
            }
        )

    return results, len(stock_tags)


def parse_ptrs(
    ptr: pd.DataFrame,
    reuse_existing: bool = True,
) -> pd.DataFrame:
    if reuse_existing and TRANSACTIONS_FILE.exists():
        print(f"Reusing: {TRANSACTIONS_FILE.name}")
        return pd.read_csv(
            TRANSACTIONS_FILE,
            low_memory=False,
        )

    ptr = ptr.copy()
    ptr["FILINGDATE"] = pd.to_datetime(
        ptr["FILINGDATE"],
        errors="coerce",
    )

    ptr = ptr.dropna(
        subset=[
            "DOCID",
            "SOURCE_URL",
            "FILINGDATE",
        ]
    ).copy()

    ptr["DOCID"] = (
        ptr["DOCID"]
        .astype(str)
        .str.replace(".0", "", regex=False)
        .str.strip()
    )

    all_transactions = []
    failed_documents = 0
    no_text_documents = 0
    total_stock_tags = 0

    for number, (_, filing) in enumerate(
        ptr.iterrows(),
        start=1,
    ):
        if number == 1 or number % 50 == 0:
            print(
                f"Parsing {number:,}/{len(ptr):,} "
                f"DOCID {filing['DOCID']}"
            )

        try:
            pdf_bytes = get_pdf_bytes(
                filing["DOCID"],
                filing["SOURCE_URL"],
            )
            text = extract_pdf_text(pdf_bytes)

            if not text.strip():
                no_text_documents += 1
                continue

            transactions, stock_tag_count = (
                parse_stock_transactions(text)
            )
            total_stock_tags += stock_tag_count

            for transaction in transactions:
                transaction["POLITICIAN"] = (
                    filing["POLITICIAN"]
                )
                transaction["STATE_DISTRICT"] = (
                    filing["STATEDST"]
                )
                transaction["FILING_DATE"] = (
                    filing["FILINGDATE"]
                )
                transaction["DOCID"] = (
                    filing["DOCID"]
                )
                transaction["FILING_YEAR"] = (
                    filing["FILING_YEAR"]
                )
                transaction["SOURCE_URL"] = (
                    filing["SOURCE_URL"]
                )
                all_transactions.append(transaction)

        except Exception as error:
            failed_documents += 1
            print(
                f"FAILED {filing['DOCID']}: "
                f"{error}"
            )

    transactions = pd.DataFrame(
        all_transactions
    )

    if transactions.empty:
        raise RuntimeError(
            "No House stock transactions parsed."
        )

    for column in [
        "FILING_DATE",
        "TRANSACTION_DATE",
        "NOTIFICATION_DATE",
    ]:
        transactions[column] = pd.to_datetime(
            transactions[column],
            errors="coerce",
        )

    transactions["TICKER"] = (
        transactions["TICKER"]
        .astype("string")
        .str.upper()
        .str.strip()
    )

    transactions.to_csv(
        TRANSACTIONS_FILE,
        index=False,
    )

    purchases = (
        transactions["TRANSACTION_TYPE"]
        .eq("P")
        .sum()
    )

    print("\n" + "=" * 70)
    print("HOUSE TRANSACTION PARSING COMPLETE")
    print("=" * 70)
    print(f"PTR documents: {len(ptr):,}")
    print(f"Parsed stock transactions: {len(transactions):,}")
    print(f"Purchases: {purchases:,}")
    print(f"Total [ST] tags seen: {total_stock_tags:,}")
    print(f"Image-only / no-text PDFs: {no_text_documents:,}")
    print(f"PDF failures: {failed_documents:,}")
    print(f"Saved to: {TRANSACTIONS_FILE.name}")

    return transactions


def clean_house_purchases(
    transactions: pd.DataFrame,
) -> pd.DataFrame:
    df = transactions.copy()

    for col in [
        "FILING_DATE",
        "TRANSACTION_DATE",
        "NOTIFICATION_DATE",
    ]:
        df[col] = pd.to_datetime(
            df[col],
            errors="coerce",
        )

    df = df[
        df["TRANSACTION_TYPE"].eq("P")
    ].copy()

    df["TICKER"] = (
        df["TICKER"]
        .astype("string")
        .str.upper()
        .str.strip()
    )

    df["VALID_TICKER"] = (
        df["TICKER"]
        .fillna("")
        .str.match(
            r"^[A-Z0-9]{1,6}"
            r"([.-][A-Z0-9]{1,4})?$"
        )
    )

    df["BAD_TRANSACTION_DATE"] = (
        df["TRANSACTION_DATE"].isna()
        |
        (
            df["TRANSACTION_DATE"]
            >
            df["FILING_DATE"]
        )
    )

    df["BAD_NOTIFICATION_DATE"] = (
        df["NOTIFICATION_DATE"].isna()
        |
        (
            df["NOTIFICATION_DATE"]
            >
            df["FILING_DATE"]
        )
    )

    df["NOTIFICATION_BEFORE_TRANSACTION"] = (
        df["NOTIFICATION_DATE"]
        <
        df["TRANSACTION_DATE"]
    )

    df["AMOUNT_RANGE_CLEAN"] = (
        df["AMOUNT_RANGE"]
        .astype(str)
        .str.replace(
            r"\s+",
            " ",
            regex=True,
        )
        .str.strip()
    )

    economic_key = [
        "POLITICIAN",
        "TICKER",
        "TRANSACTION_DATE",
        "TRANSACTION_TYPE",
        "AMOUNT_RANGE_CLEAN",
    ]

    df = (
        df
        .sort_values(
            [
                *economic_key,
                "FILING_DATE",
                "DOCID",
            ]
        )
        .reset_index(drop=True)
    )

    df["FIRST_DOCID"] = (
        df.groupby(
            economic_key,
            dropna=False,
        )["DOCID"]
        .transform("first")
    )

    df["IS_CROSS_DOCUMENT_REPEAT"] = (
        df["DOCID"].astype(str)
        !=
        df["FIRST_DOCID"].astype(str)
    )

    clean = df[
        df["VALID_TICKER"]
        &
        ~df["BAD_TRANSACTION_DATE"]
        &
        ~df["BAD_NOTIFICATION_DATE"]
        &
        ~df["NOTIFICATION_BEFORE_TRANSACTION"]
        &
        ~df["IS_CROSS_DOCUMENT_REPEAT"]
    ].copy()

    clean["SIGNAL_DATE"] = (
        clean["FILING_DATE"]
    )

    clean = (
        clean
        .sort_values(
            [
                "SIGNAL_DATE",
                "POLITICIAN",
                "TICKER",
                "TRANSACTION_DATE",
            ]
        )
        .reset_index(drop=True)
    )

    clean.to_csv(
        CLEAN_FILE,
        index=False,
    )

    print("\n" + "=" * 70)
    print("HOUSE PURCHASE CLEANING COMPLETE")
    print("=" * 70)
    print(f"Clean House purchases: {len(clean):,}")
    print(
        f"Cross-document redisclosures removed: "
        f"{df['IS_CROSS_DOCUMENT_REPEAT'].sum():,}"
    )
    print(
        f"Filing lag >90 days: "
        f"{(
            (
                clean['FILING_DATE']
                -
                clean['TRANSACTION_DATE']
            ).dt.days
            > 90
        ).sum():,}"
    )
    print(f"Saved to: {CLEAN_FILE.name}")

    return clean


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Download, parse, and clean official "
            "House Periodic Transaction Reports."
        )
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help=(
            "Ignore existing intermediate CSV outputs. "
            "Downloaded ZIPs and cached PDFs are still reused."
        ),
    )
    args = parser.parse_args()

    reuse_existing = not args.rebuild

    filings = build_filing_index(
        reuse_existing=reuse_existing,
    )
    ptr = build_ptr_index(
        filings,
        reuse_existing=reuse_existing,
    )
    transactions = parse_ptrs(
        ptr,
        reuse_existing=reuse_existing,
    )
    clean_house_purchases(transactions)


if __name__ == "__main__":
    main()
