"""Decode IOTC/CWP fishing-ground grid codes into real lat/lon and group them into
named Maldives regions.

The IOTC "Catch by Area" dataset (see iotc.py) reports catch against 7-digit CWP grid
codes such as "5100073". The coding rule (verified against IOTC's own published
examples for the 5x5 grid: "6100065" = 00-05 deg N, 065-070 deg E; "6200065" = 00-05 deg
S, 065-070 deg E; "6115065" = 15-20 deg N, 065-070 deg E) is:

    digit 1   : square size code  -> "5" = 1x1 degree square, "6" = 5x5 degree square
    digit 2   : quadrant          -> 1 = NE (lat N, lon E)
                                      2 = SE (lat S, lon E)
                                      3 = SW (lat S, lon W)
                                      4 = NW (lat N, lon W)
    digits3-4 : latitude degree band start (00-90)
    digits5-7 : longitude degree band start (000-180)

Applying this rule to the codes that actually appear for FLEET_CODE == "MDV" (Maldives)
in the IOTC data lands them at lon 72-75 deg E, lat -1 to 7 deg N — exactly the Maldives
archipelago -- which independently confirms the decoding is correct.
"""
from dataclasses import dataclass

SIZE_BY_CODE = {"5": 1, "6": 5}
QUADRANT_LAT_SIGN = {"1": 1, "2": -1, "3": -1, "4": 1}  # N=+1, S=-1
QUADRANT_LON_SIGN = {"1": 1, "2": 1, "3": -1, "4": -1}  # E=+1, W=-1


@dataclass(frozen=True)
class GridCell:
    code: str
    size_deg: int
    lat_start: float
    lon_start: float

    @property
    def lat_center(self) -> float:
        return self.lat_start + self.size_deg / 2 * QUADRANT_LAT_SIGN[self.code[1]]

    @property
    def lon_center(self) -> float:
        return self.lon_start + self.size_deg / 2 * QUADRANT_LON_SIGN[self.code[1]]


def decode_iotc_grid_code(code: str) -> GridCell:
    code = str(code).strip().zfill(7)
    size_deg = SIZE_BY_CODE.get(code[0])
    if size_deg is None:
        raise ValueError(f"Unknown IOTC grid size code in '{code}'")
    quadrant = code[1]
    lat_deg = int(code[2:4])
    lon_deg = int(code[4:7])
    lat_start = QUADRANT_LAT_SIGN[quadrant] * lat_deg
    lon_start = QUADRANT_LON_SIGN[quadrant] * lon_deg
    return GridCell(code=code, size_deg=size_deg, lat_start=lat_start, lon_start=lon_start)


# --- Named Maldives regions, derived from decoded latitude bands -----------------
# North / Central / South follow the natural N-S shape of the Maldives archipelago.
# Boundaries chosen from the decoded latitude of the grid cells that actually carry
# Maldives fleet catch (see docs/DATA_SOURCES.md for the full derivation).
REGION_DEFINITIONS = [
    {"name": "North Maldives", "min_lat": 5.0, "max_lat": 8.0, "lat_center": 6.0, "lon_center": 73.0},
    {"name": "Central Maldives (Male)", "min_lat": 1.0, "max_lat": 5.0, "lat_center": 3.0, "lon_center": 73.4},
    {"name": "South Maldives", "min_lat": -2.0, "max_lat": 1.0, "lat_center": -0.2, "lon_center": 73.3},
]


def region_for_latitude(lat: float) -> str:
    for region in REGION_DEFINITIONS:
        if region["min_lat"] <= lat < region["max_lat"]:
            return region["name"]
    # Anything outside the Maldives EEZ band (distant-water grid cells occasionally
    # reported against the Maldives flag) is bucketed into the nearest boundary region.
    if lat >= REGION_DEFINITIONS[0]["max_lat"]:
        return REGION_DEFINITIONS[0]["name"]
    return REGION_DEFINITIONS[-1]["name"]


def region_for_grid_code(code: str) -> str | None:
    """Return a named region only for grid cells within the Maldives longitude band
    (72-75 deg E). Codes outside that band are far-water fishing grounds, and codes
    that don't follow the standard 1x1/5x5 CWP scheme (e.g. IOTC's "9000020" catch-all
    code for unclassified/aggregated areas) can't be decoded at all -- both cases are
    excluded from region-level aggregation but still counted in the national total."""
    try:
        cell = decode_iotc_grid_code(code)
    except (ValueError, KeyError):
        return None
    if not (71.0 <= cell.lon_center <= 76.0):
        return None
    return region_for_latitude(cell.lat_center)
