"""Fetch real historical fish catch data for the Maldives fleet from the IOTC
(Indian Ocean Tuna Commission).

IOTC publishes its "Catch by Area" (CA) dataset as a static, versioned zip file linked
from https://iotc.org/data/datasets/latest/CE/All (verified live: the link resolves to
https://iotc.org/sites/default/files/documents/<date>/IOTC-DATASETS-<date>-CE-<years>.zip).
The CA CSV inside has monthly-resolution retained catch (metric tons, see
CATCH_UNIT_CODE) broken down by year, quarter, month, IOTC/CWP grid cell
(FISHING_GROUND_CODE), fleet, gear, and species, for every IOTC member fleet (the full
file is ~500MB uncompressed). We stream through it and keep only FLEET_CODE == "MDV"
(Maldives), which is the real fleet-level dataset this project forecasts.
"""
from __future__ import annotations

import csv
import io
import logging
import re
import zipfile
from pathlib import Path

import pandas as pd
import requests

from app.core.config import DATA_RAW_DIR
from app.ml.ingestion.regions import region_for_grid_code

logger = logging.getLogger(__name__)

IOTC_LISTING_URL = "https://iotc.org/data/datasets/latest/CE/All"
CA_FILENAME_IN_ZIP = re.compile(r".*-CA-\d{4}-\d{4}\.csv$", re.IGNORECASE)

FLEET_CODE = "MDV"  # Maldives, per IOTC's FLEET_CODE vocabulary


def _resolve_zip_url() -> str:
    resp = requests.get(IOTC_LISTING_URL, timeout=30)
    resp.raise_for_status()
    match = re.search(r'href="(https://iotc\.org/sites/default/files/documents/[^"]+\.zip)"', resp.text)
    if not match:
        raise RuntimeError(
            f"Could not find the IOTC CE dataset zip link on {IOTC_LISTING_URL}. "
            "IOTC may have restructured their datasets page."
        )
    return match.group(1)


def fetch_maldives_catch(force_download: bool = False) -> pd.DataFrame:
    """Download the IOTC Catch-by-Area zip, stream-filter it to the Maldives fleet, and
    write data/raw/iotc_maldives_catch.csv. Returns the filtered DataFrame."""
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_RAW_DIR / "iotc_maldives_catch.csv"
    zip_cache_path = DATA_RAW_DIR / "_iotc_ce_all_cache.zip"

    if force_download or not zip_cache_path.exists():
        zip_url = _resolve_zip_url()
        logger.info("Downloading IOTC dataset from %s (this is a large file, ~20MB zipped)", zip_url)
        resp = requests.get(zip_url, timeout=300, stream=True)
        resp.raise_for_status()
        with open(zip_cache_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    else:
        logger.info("Using cached IOTC zip at %s", zip_cache_path)

    with zipfile.ZipFile(zip_cache_path) as zf:
        ca_name = next(n for n in zf.namelist() if CA_FILENAME_IN_ZIP.match(n))
        logger.info("Streaming %s from the zip and filtering FLEET_CODE == %s", ca_name, FLEET_CODE)
        rows: list[dict] = []
        with zf.open(ca_name) as raw:
            text_stream = io.TextIOWrapper(raw, encoding="utf-8")
            reader = csv.DictReader(text_stream)
            for row in reader:
                if row.get("FLEET_CODE") == FLEET_CODE:
                    rows.append(row)

    df = pd.DataFrame(rows)
    logger.info("Filtered %s Maldives rows out of the full IOTC CA dataset", len(df))

    df["YEAR"] = df["YEAR"].astype(int)
    df["MONTH_START"] = df["MONTH_START"].astype(int)
    df["CATCH"] = pd.to_numeric(df["CATCH"], errors="coerce")
    df["region"] = df["FISHING_GROUND_CODE"].map(region_for_grid_code)

    df.to_csv(out_path, index=False)
    logger.info("Wrote %s rows to %s", len(df), out_path)
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    df = fetch_maldives_catch()
    print("Year range:", df["YEAR"].min(), "-", df["YEAR"].max())
    print("Rows with a resolved region:", df["region"].notna().sum(), "/", len(df))
    print(df.groupby("region")["CATCH"].sum().sort_values(ascending=False))
    print(df.groupby("SPECIES")["CATCH"].sum().sort_values(ascending=False).head(10))
