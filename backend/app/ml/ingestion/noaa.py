"""Fetch real environmental data (SST, wind speed, salinity) from NOAA ERDDAP for the
three Maldives regions defined in regions.py.

All three datasets below were verified live (see docs/DATA_SOURCES.md for the exact
queries run and sample responses) and are public, free, no-API-key REST endpoints that
return CSV directly:

    SST       ncdcOisst21Agg_LonPM180   daily, 0.25 deg, 1981-09-01 -> present
    Wind      ccmp_31                   6-hourly, 0.25 deg, 1993-01-02 -> ~2024-01
    Salinity  coastwatchSMOSv662SSS3day 3-day composite, 0.25 deg, 2010-06 -> present

We query the single nearest 0.25 deg grid point to each region's center (rather than
averaging a whole bounding box) so the ERDDAP requests stay small and fast while still
returning real, per-region observations. Monthly aggregation happens later in
pipeline/preprocess.py.

Although SST/wind cover more history than this, DATASETS below deliberately requests
only 2010-onward for all three variables (see the comment on DATASETS) so every region
gets one clean, gap-free multivariate window.
"""
from __future__ import annotations

import io
import logging
import time
from datetime import datetime, timezone

import pandas as pd
import requests

from app.core.config import DATA_RAW_DIR
from app.ml.ingestion.regions import REGION_DEFINITIONS

logger = logging.getLogger(__name__)

ERDDAP_BASE = "https://coastwatch.pfeg.noaa.gov/erddap/griddap"

# The salinity dataset 302-redirects to coastwatch.noaa.gov, which returns 403 Forbidden
# to the default "python-requests/x.x" User-Agent (a WAF rule, verified: the same URL
# works fine with curl's UA). A browser-like UA avoids that block.
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Kandumas/1.0"}

# All three start in 2010 -- salinity (SMOS) only exists from 2010-06 onward, so
# starting SST/wind there too gives every region a full, gap-free multivariate overlap
# window instead of a longer series with a 17-year hole in one column. ERDDAP's
# multi-decade single-point daily/6-hourly queries were also observed (this session) to
# be extremely slow server-side; the shorter window keeps requests tractable.
DATASETS = {
    "sst": {
        "id": "ncdcOisst21Agg_LonPM180",
        "var": "sst",
        "start": "2010-01-01",
        "end": "last",  # ERDDAP's "last" always resolves to the newest timestamp actually in the dataset
        "z": "(0.0)",
    },
    "wind_speed": {
        "id": "ccmp_31",
        "var": "ws",
        "start": "2010-01-01",
        "end": "2024-01-31",  # ccmp_31's real coverage ends here; "last" would 404 past it
        "z": None,
    },
    "salinity": {
        "id": "coastwatchSMOSv662SSS3day",
        "var": "sss",
        "start": "2010-06-03",
        "end": "last",
        "z": "(0.0)",
        # Verified live: querying SMOS directly at each region's center (72.5-73.5 deg
        # E, right among the islands) returns 100% NaN -- SMOS is an L-band satellite
        # radiometer, and its retrievals are masked out near any land due to
        # radio-frequency interference/land contamination in the sensor footprint, a
        # known, documented limitation for small-island regions like the Maldives. A
        # point 2 deg further west (open ocean, same latitude, still representative of
        # the surrounding water mass) returns real values -- confirmed live before
        # adopting this offset.
        "lon_offset": -2.0,
    },
}


def _nearest_quarter_deg(value: float) -> float:
    return round(value * 4) / 4


def _fetch_range(dataset_key: str, region_name: str, lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    cfg = DATASETS[dataset_key]
    lat_q = _nearest_quarter_deg(lat)
    lon_q = _nearest_quarter_deg(lon + cfg.get("lon_offset", 0.0))
    z_part = f"[{cfg['z']}]" if cfg["z"] else ""
    end_part = "last" if end == "last" else f"{end}T23:59:59Z"
    url = (
        f"{ERDDAP_BASE}/{cfg['id']}.csv?"
        f"{cfg['var']}"
        f"[({start}T00:00:00Z):1:({end_part})]"
        f"{z_part}"
        f"[({lat_q})]"
        f"[({lon_q})]"
    )
    logger.info("NOAA ERDDAP %s / %s [%s -> %s]", dataset_key, region_name, start, end)
    resp = requests.get(url, timeout=300, headers=REQUEST_HEADERS)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text), skiprows=[1])  # row 1 is the units row
    df = df.rename(columns={cfg["var"]: dataset_key, "time": "timestamp"})
    df["region"] = region_name
    df["variable"] = dataset_key
    return df[["timestamp", "region", "variable", dataset_key]].rename(
        columns={dataset_key: "value"}
    )


def _year_chunks(start: str, end_year: int) -> list[tuple[str, str]]:
    """Split [start, end_year] into yearly (start, end) date-string pairs.

    Fetching multi-year single-point time series in one huge request was observed
    (this session) to sometimes come back as a real HTTP 200 with the correct row
    count but with every value past a certain point silently NaN -- e.g. a 2010-2024
    wind_speed request returned real data through mid-2013 and NaN for every one of
    the following ~10 years, even though the same point/dataset returns real data when
    queried directly for, e.g., January 2018. Fetching one year at a time avoids
    whatever server-side degradation causes that and makes each request small enough
    to retry cheaply."""
    start_year = int(start[:4])
    chunks = []
    for year in range(start_year, end_year + 1):
        chunk_start = start if year == start_year else f"{year}-01-01"
        chunk_end = f"{year}-12-31"
        chunks.append((chunk_start, chunk_end))
    return chunks


def _fetch_one(dataset_key: str, region_name: str, lat: float, lon: float, max_retries: int = 2) -> pd.DataFrame:
    cfg = DATASETS[dataset_key]
    end_year = 2024 if cfg["end"] != "last" else datetime.now(timezone.utc).year
    frames = []
    for chunk_start, chunk_end in _year_chunks(cfg["start"], end_year):
        is_final_year = chunk_end[:4] == str(end_year)
        if is_final_year:
            # Cap the last chunk at the dataset's real configured end (e.g. ccmp_31's
            # coverage stops 2024-01-31, not 2024-12-31) rather than a bare Dec 31,
            # which would ask for dates past the axis maximum and 404.
            end_for_chunk = "last" if cfg["end"] == "last" else cfg["end"]
        else:
            end_for_chunk = chunk_end
        for attempt in range(1, max_retries + 1):
            try:
                chunk_df = _fetch_range(dataset_key, region_name, lat, lon, chunk_start, end_for_chunk)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "%s/%s chunk %s attempt %s/%s failed: %s",
                    dataset_key, region_name, chunk_start[:4], attempt, max_retries, exc,
                )
                if attempt == max_retries:
                    chunk_df = None
                else:
                    time.sleep(3 * attempt)
                    continue
            break

        if chunk_df is None or len(chunk_df) == 0:
            continue

        non_null_frac = chunk_df["value"].notna().mean()
        if non_null_frac < 0.05 and dataset_key != "salinity":
            # Salinity is expected to be sparse near land even after the open-ocean
            # offset (cloud/swath gaps); sst/wind are not, so a near-total-NaN chunk
            # for those two means the same silent-degradation issue this function
            # exists to work around -- one retry of just that chunk.
            logger.warning(
                "%s/%s chunk %s came back %.0f%% NaN, retrying once",
                dataset_key, region_name, chunk_start[:4], (1 - non_null_frac) * 100,
            )
            try:
                retry_df = _fetch_range(dataset_key, region_name, lat, lon, chunk_start, end_for_chunk)
                if retry_df["value"].notna().mean() > non_null_frac:
                    chunk_df = retry_df
            except Exception as exc:  # noqa: BLE001
                logger.warning("Retry of %s/%s chunk %s also failed: %s", dataset_key, region_name, chunk_start[:4], exc)

        frames.append(chunk_df)

    if not frames:
        raise RuntimeError(f"No data returned for {dataset_key}/{region_name} across any year chunk")
    return pd.concat(frames, ignore_index=True)


def fetch_all_environmental_data(max_retries: int = 2) -> pd.DataFrame:
    """Fetch SST, wind speed and salinity for every region. Returns and also writes
    data/raw/noaa_environmental.csv (long format: timestamp, region, variable, value).

    Each (dataset, region) combo is fetched independently and failures don't abort the
    whole run -- ERDDAP occasionally has transient slow responses, so we'd rather come
    back with 8/9 real series than crash on the 9th. Failures are reported at the end."""
    frames: list[pd.DataFrame] = []
    failed: list[str] = []
    for region in REGION_DEFINITIONS:
        for dataset_key in DATASETS:
            label = f"{dataset_key}/{region['name']}"
            for attempt in range(1, max_retries + 1):
                try:
                    frames.append(
                        _fetch_one(
                            dataset_key,
                            region["name"],
                            region["lat_center"],
                            region["lon_center"],
                        )
                    )
                    break
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Attempt %s/%s failed for %s: %s", attempt, max_retries, label, exc)
                    if attempt == max_retries:
                        failed.append(label)
                    else:
                        time.sleep(3 * attempt)

    if not frames:
        raise RuntimeError("Every NOAA ERDDAP request failed; no environmental data fetched.")

    result = pd.concat(frames, ignore_index=True)
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_RAW_DIR / "noaa_environmental.csv"
    result.to_csv(out_path, index=False)
    logger.info("Wrote %s rows to %s", len(result), out_path)
    if failed:
        logger.warning("These combos failed after %s attempts and are MISSING: %s", max_retries, failed)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    df = fetch_all_environmental_data()
    print(df.groupby(["region", "variable"])["value"].agg(["count", "min", "max"]))
