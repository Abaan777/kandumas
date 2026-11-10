# Data Sources

This project uses **real, live-fetched data** -- nothing in `data/raw/` or
`data/processed/` is synthetic or hand-entered. This document records exactly where
each number comes from, the queries used, and the honest limitations of each source, so
the report/viva can cite this directly.

## 1. IOTC (Indian Ocean Tuna Commission) -- historical catch data

**Script:** `backend/app/ml/ingestion/iotc.py`

- Listing page: https://iotc.org/data/datasets/latest/CE/All
- Resolves to a static zip, e.g. `https://iotc.org/sites/default/files/documents/2026/08/IOTC-DATASETS-2026-08-13-CE-1952-2025.zip`
- Inside: `IOTC-DATASETS-<date>-CA-1952-2025.csv`, the **Catch by Area** dataset --
  monthly-resolution retained catch (metric tons) by year, quarter, month,
  `FISHING_GROUND_CODE` (a 1x1 or 5x5 degree CWP grid cell), fleet, gear and species,
  for every IOTC member fleet (~500MB uncompressed, millions of rows).
- We stream-filter this to `FLEET_CODE == "MDV"` (Maldives) only: **106,999 real rows**,
  1970-2025, covering skipjack tuna, yellowfin tuna, kawakawa, frigate tuna, bigeye tuna,
  billfish, etc. Rows reported as a count of fish (`CATCH_UNIT_CODE == "NO"`, mostly
  incidental billfish bycatch) are excluded from the weight-based series used for
  forecasting (see `preprocess.py`) because they cannot be summed with metric-ton rows.
- Output: `data/raw/iotc_maldives_catch.csv` (all species, unfiltered -- kept as the raw
  source of truth). `preprocess.py` then narrows the **forecasting target** down to just
  skipjack tuna and yellowfin tuna, the Maldives' two main commercial tuna species; every
  other species/bycatch category is excluded from the processed table, the DB, and the
  trained models.

### Region decoding

`FISHING_GROUND_CODE` is a 7-digit IOTC/CWP grid code (e.g. `5104073`). The decode rule
(`backend/app/ml/ingestion/regions.py`), verified against IOTC's own published examples
for the 5x5 grid (`6100065` = 0-5N/65-70E, `6200065` = 0-5S/65-70E, `6115065` =
15-20N/65-70E):

| digit(s) | meaning |
|---|---|
| 1 | square size: `5` = 1x1 deg, `6` = 5x5 deg |
| 2 | quadrant: `1`=NE, `2`=SE, `3`=SW, `4`=NW |
| 3-4 | latitude degree band start |
| 5-7 | longitude degree band start |

Applying this to the Maldives fleet's actual codes lands them at 72-75 deg E, -1 to 7
deg N -- the real Maldives archipelago -- which independently confirms the decoding.
Grid cells are grouped into three named regions by decoded latitude: **North Maldives**
(>=5 deg N), **Central Maldives (Male)** (1-5 deg N, contains Male's real ~4.17N), and
**South Maldives** (<1 deg N, includes the Addu/equator-crossing area). ~86% of Maldives
catch rows resolve to one of these three regions; the rest are far-water grid cells and
are excluded from region-level totals (but not from the national totals).

## 2. NOAA ERDDAP -- environmental data (SST, wind speed, salinity)

**Script:** `backend/app/ml/ingestion/noaa.py`

All three are free, public, no-API-key REST endpoints on
`https://coastwatch.pfeg.noaa.gov/erddap/griddap/`, queried for the single nearest 0.25
deg grid point to each region's center:

| Variable | Dataset ID | Native resolution | Real coverage | Fetched window |
|---|---|---|---|---|
| SST | `ncdcOisst21Agg_LonPM180` | daily, 0.25 deg | 1981-09 -> present | 2010-01 -> present |
| Wind speed | `ccmp_31` | 6-hourly, 0.25 deg | 1993-01 -> ~2024-01 | 2010-01 -> 2024-01 |
| Salinity | `coastwatchSMOSv662SSS3day` | 3-day composite, 0.25 deg | 2010-06 -> present | 2010-06 -> present |

**Why 2010 onward, even though SST/wind go back further:** salinity only exists from
2010-06, so starting all three variables in 2010 gives every region one clean,
gap-free multivariate window instead of a longer series with a 17-year hole in one
column. This was also necessary in practice: ERDDAP's multi-decade single-point
daily/6-hourly point-extraction queries were observed (this session) to take minutes
each and occasionally time out; the shorter window keeps requests reliable (a 1-year
query took ~5.5s; the full 2010-present SST query took ~210s).

**Known quirks:**
- The salinity dataset 302-redirects to `coastwatch.noaa.gov`, which returns `403
  Forbidden` to the default `python-requests` User-Agent (a WAF rule -- verified the
  identical URL works with curl's UA). `noaa.py` sends a browser-like User-Agent to
  avoid this. That same redirected host also occasionally returns transient `502
  Proxy Error` on the full-range salinity query; `noaa.py` retries once.
- **SMOS salinity returns 100% NaN when queried exactly at a region's center** (verified
  live: every one of the ~1,900+ rows fetched at 72.5-73.5 deg E was NaN). SMOS is an
  L-band satellite radiometer, and its retrievals are masked out near any land due to
  radio-frequency interference/land contamination in the sensor footprint -- a known,
  documented limitation for small-island regions. A point 2 deg further west (open
  ocean, same latitude, still representative of the surrounding water mass) returns
  real values (verified live: e.g. 32.4 PSU at 6.125N/71.125E on 2024-01-01), so
  `DATASETS["salinity"]["lon_offset"] = -2.0` in `noaa.py` shifts only the salinity
  query westward. SST and wind speed are queried at the true region center -- they
  don't have this masking problem.

Output: `data/raw/noaa_environmental.csv` (long format: timestamp, region, variable,
value). Monthly aggregation happens in `preprocess.py`.

## 3. FAO

The proposal names FAO alongside IOTC and NOAA. In practice, FAO's fishery statistics
(FishStatJ, the FAO "Global Production" dataset) have **no stable public bulk-download
or REST endpoint** -- FishStatJ is a desktop-only application, and the FAO Data Explorer
/ statistics-query tool at fao.org is a session-based single-page app (verified: it
returns an empty JS-shell over plain HTTP, and the older bulk-download host now returns
`403 Forbidden`/CloudFront errors).

Rather than fabricate a fetch, this project treats FAO the same way Chapter 2
(Literature Review) already does: as a **documented statistical/contextual reference**
(FAO, 2022, "The State of World Fisheries and Aquaculture"), cited in the report
references. **IOTC is the actual operative, higher-resolution source for Indian Ocean
tuna catch** -- which is the more precise source for this exact use case regardless.
See `backend/app/ml/ingestion/fao.py` for the connector stub and this same explanation
in code.

## Reproducing the data pull

```
cd backend
python -m app.ml.ingestion.iotc      # ~15s (with the zip cached after first run)
python -m app.ml.ingestion.noaa      # ~20-25 min (9 slow ERDDAP queries)
python -m app.ml.pipeline.preprocess # builds data/processed/monthly_features.csv
```
