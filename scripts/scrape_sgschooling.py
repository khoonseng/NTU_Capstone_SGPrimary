"""
ingestion/scrape_sgschooling.py

Step 1: Scrape sgschooling.com for a given year (default: 2025)
Pipeline: sgschooling.com → pandas DataFrame → Parquet → GCS → BigQuery

Usage:
    python scrape_sgschooling.py            # scrapes 2025 only
    python scrape_sgschooling.py 2019 2025  # scrapes 2019 to 2025 inclusive (Step 2)
    python scrape_sgschooling.py 2009 2018  # scrapes 2009 to 2018 inclusive (Step 3)
"""

import os
import re
import sys
import time
import html
import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from io import BytesIO
from dotenv import load_dotenv
from google.cloud import storage

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
GCS_BUCKET   = os.getenv("GCS_BUCKET_NAME")
GCS_PREFIX   = "raw/sgschooling"
BASE_URL     = "https://sgschooling.com/year/{year}/all"
REQUEST_WAIT = 5   # seconds between requests — be polite


# ── Schema — explicit PyArrow schema matching our 13-column design ─────────────
PARQUET_SCHEMA = pa.schema([
    pa.field("school_name",          pa.string()),
    pa.field("total_vacancy",        pa.int64()),
    pa.field("phase",                pa.string()),
    pa.field("vacancy",              pa.int64()),
    pa.field("applied",              pa.int64()),
    pa.field("taken",                pa.int64()),
    pa.field("ballot_scenario_code", pa.string()),
    pa.field("ballot_description",   pa.string()),
    pa.field("ballot_applicants",    pa.int64()),
    pa.field("ballot_vacancies",     pa.int64()),
    pa.field("ballot_chance_pct",    pa.float64()),
    pa.field("registration_year",    pa.int64()),
    pa.field("scraped_at",           pa.timestamp("us", tz="UTC")),
])


# ── Helpers ────────────────────────────────────────────────────────────────────

def parse_int(value: str) -> int | None:
    """Extract integer from a string like '240', '&nbsp;', or empty. Returns None if not parseable."""
    if not value:
        return None
    cleaned = value.replace(",", "").replace("\xa0", "").strip()
    return int(cleaned) if cleaned.isdigit() else None


def parse_float_pct(value: str) -> float | None:
    """Extract float from a string like 'Ballot Chance: 76%'. Returns None if not parseable."""
    match = re.search(r"[\d.]+", value)
    return float(match.group()) if match else None


def parse_ballot_span(span) -> dict:
    """
    Extract ballot fields from a <span class="tt"> element.

    data-tt-title always contains the scenario code e.g. "SC&lt;1" → "SC<1"
    data-tt contains a multiline string:
        Line 0: "SC within 1km needs to ballot"       ← always present
        Line 1: "Applicants: 56"                      ← 2024+ only
        Line 2: "Vacancies: 20"                       ← 2024+ only
        Line 3: "Ballot Chance: 36%"                  ← 2024+ only
    """
    result = {
        "ballot_scenario_code": None,
        "ballot_description":   None,
        "ballot_applicants":    None,
        "ballot_vacancies":     None,
        "ballot_chance_pct":    None,
    }

    if span is None:
        return result

    # Decode HTML entities: "SC&lt;1" → "SC<1"
    raw_title = span.get("data-tt-title", "")
    result["ballot_scenario_code"] = html.unescape(raw_title).strip() if raw_title else None

    raw_tt = span.get("data-tt", "")
    if not raw_tt:
        return result

    lines = [line.strip() for line in raw_tt.strip().splitlines() if line.strip()]

    if len(lines) >= 1:
        result["ballot_description"] = lines[0]

    # 2024+ extended statistics
    for line in lines[1:]:
        lower = line.lower()
        if lower.startswith("applicants:"):
            result["ballot_applicants"] = parse_int(line.split(":")[1].strip())
        elif lower.startswith("vacancies:"):
            result["ballot_vacancies"] = parse_int(line.split(":")[1].strip())
        elif lower.startswith("ballot chance:"):
            result["ballot_chance_pct"] = parse_float_pct(line)

    return result


def parse_total_vacancy(text: str) -> int | None:
    """Extract total vacancy from school name row e.g. '↳ Vacancy (300)' → 300."""
    match = re.search(r"\((\d+)\)", text)
    return int(match.group(1)) if match else None


# ── Core parser ────────────────────────────────────────────────────────────────

def parse_year_page(html_content: str, year: int) -> list[dict]:
    """
    Parse the full HTML page for a given year.
    Returns a list of dicts, one per school-phase combination.

    HTML structure — each school is 4 consecutive <tr> rows:
        Row 0: School name + total vacancy e.g. "Ai Tong" and "(300)"
        Row 1: ↳ Vacancy   — one cell per phase
        Row 2: ↳ Applied   — one cell per phase
        Row 3: ↳ Taken     — one cell per phase, may contain <span> for ballot
    """
    soup = BeautifulSoup(html_content, "html.parser")
    scraped_at = datetime.now(timezone.utc)

    first_table = soup.find("table")

    # Extract phase headers from <thead>
    headers = []
    for th in first_table.select("thead th"):
        text = th.get_text(strip=True)
        if text and text.lower() != "school":
            headers.append(text)
    # headers = ["Phase 1", "2A", "2B", "2C", "2C(S)", "3"] for 2022+
    # headers = ["Phase 1", "2A(1)", "2A(2)", "2B", "2C", "2C(S)", "3"] for pre-2022

    rows = first_table.select("tbody tr")
    records = []

    # Group rows into blocks of 4 (one block per school)
    # Row 0: school name row — identified by absence of "↳" prefix
    i = 0
    while i < len(rows):
        cells = rows[i].find_all("td")

        # Detect start of a new school block — first cell has no "↳"
        first_cell_text = cells[0].get_text(strip=True) if cells else ""
        if "↳" not in first_cell_text:
            # This is a school name row — expect 3 more rows to follow
            if i + 3 >= len(rows):
                break  # malformed tail, stop

            school_row    = rows[i]
            vacancy_row   = rows[i + 1]
            applied_row   = rows[i + 2]
            taken_row     = rows[i + 3]

            # School name: strip the link and bold tags
            school_name_tag = school_row.find("strong")
            school_name = school_name_tag.get_text(strip=True) if school_name_tag else first_cell_text

            # Total vacancy: from the vacancy row's first cell e.g. "↳ Vacancy (300)"
            vacancy_label = vacancy_row.find_all("td")[0].get_text(strip=True)
            total_vacancy = parse_total_vacancy(vacancy_label)

            vacancy_cells = vacancy_row.find_all("td")[1:]
            applied_cells = applied_row.find_all("td")[1:]
            taken_cells   = taken_row.find_all("td")[1:]

            for col_idx, phase in enumerate(headers):
                # Guard against ragged rows (shouldn't happen but be defensive)
                v_cell = vacancy_cells[col_idx] if col_idx < len(vacancy_cells) else None
                a_cell = applied_cells[col_idx] if col_idx < len(applied_cells) else None
                t_cell = taken_cells[col_idx]   if col_idx < len(taken_cells)   else None

                vacancy = parse_int(v_cell.get_text(strip=True)) if v_cell else None
                applied = parse_int(a_cell.get_text(strip=True)) if a_cell else None

                # Taken: extract only the first number — ignore <br> and <span> text
                taken = None
                if t_cell:
                    # Get direct text nodes only, ignoring span content
                    raw_taken = t_cell.find(string=True, recursive=False)
                    if raw_taken:
                        taken = parse_int(raw_taken.strip())
                    # Fallback: first number in the cell text
                    if taken is None:
                        taken = parse_int(re.search(r"\d+", t_cell.get_text()).group()
                                          if re.search(r"\d+", t_cell.get_text()) else "")

                # Ballot: from <span class="tt"> if present
                span = t_cell.find("span", class_="tt") if t_cell else None
                ballot = parse_ballot_span(span)

                records.append({
                    "school_name":          school_name,
                    "total_vacancy":        total_vacancy,
                    "phase":                phase,
                    "vacancy":              vacancy,
                    "applied":              applied,
                    "taken":                taken,
                    "ballot_scenario_code": ballot["ballot_scenario_code"],
                    "ballot_description":   ballot["ballot_description"],
                    "ballot_applicants":    ballot["ballot_applicants"],
                    "ballot_vacancies":     ballot["ballot_vacancies"],
                    "ballot_chance_pct":    ballot["ballot_chance_pct"],
                    "registration_year":    year,
                    "scraped_at":           scraped_at,
                })

            i += 4  # advance past all 4 rows for this school
        else:
            i += 1  # unexpected row, skip

    return records


# ── Scrape one year ────────────────────────────────────────────────────────────

def scrape_year(year: int) -> pd.DataFrame:
    url = BASE_URL.format(year=year)
    print(f"  Fetching {url} ...")
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    records = parse_year_page(response.text, year)
    df = pd.DataFrame(records)

    # Enforce correct dtypes before writing Parquet
    int_cols   = ["total_vacancy", "vacancy", "applied", "taken",
                  "ballot_applicants", "ballot_vacancies", "registration_year"]
    float_cols = ["ballot_chance_pct"]
    for col in int_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in float_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    print(f"  Parsed {len(df)} rows across {df['school_name'].nunique()} schools.")
    return df


# ── GCS upload ─────────────────────────────────────────────────────────────────

def upload_to_gcs(df: pd.DataFrame, year: int) -> str:
    blob_name = f"{GCS_PREFIX}/sgschooling_{year}.parquet"
    table = pa.Table.from_pandas(df, schema=PARQUET_SCHEMA, preserve_index=False)
    buffer = BytesIO()
    pq.write_table(table, buffer)
    buffer.seek(0)

    client = storage.Client()
    blob = client.bucket(GCS_BUCKET).blob(blob_name)
    blob.upload_from_file(buffer, content_type="application/octet-stream")

    gcs_uri = f"gs://{GCS_BUCKET}/{blob_name}"
    print(f"  Uploaded to {gcs_uri}")
    # print(df.head(20))
    return gcs_uri

# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Parse year range from CLI args
    # Default: 2025 only
    # Usage: python scrape_sgschooling.py 2019 2025
    args = sys.argv[1:]
    if len(args) == 0:
        years = [2025]
    elif len(args) == 2:
        start_year, end_year = int(args[0]), int(args[1])
        years = list(range(start_year, end_year + 1))
    else:
        print("Usage: python scrape_sgschooling.py [start_year end_year]")
        sys.exit(1)

    print(f"=== Scraping sgschooling.com for years: {years} ===\n")

    gcs_uris = []
    for year in years:
        print(f"[{year}]")
        df = scrape_year(year)
        gcs_uri = upload_to_gcs(df, year)
        gcs_uris.append(gcs_uri)
        if year != years[-1]:
            time.sleep(REQUEST_WAIT)

    print(gcs_uris)
    print("\n=== Done ===")
