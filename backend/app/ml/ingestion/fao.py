"""FAO connector.

The proposal names FAO (Food and Agriculture Organization) alongside IOTC and NOAA as a
data source. In practice, for Indian-Ocean tuna catch specifically, IOTC (iotc.py) is
the authoritative, fleet-level, monthly-resolution operative source, and it is what this
project's forecasting models are trained on.

FAO's own fishery statistics (FishStatJ / the FAO "Global Production" dataset) do not
have a stable public bulk-download or REST endpoint: FishStatJ is a desktop-only
application, and the FAO Data Explorer / statistics-query tool at fao.org is a
session-based single-page app with no documented static CSV/API export (verified: the
listing page returns an empty SPA shell over HTTP, and the bulk-download host used by
older FAO tools now returns 403 Forbidden). Because of that, this project does not treat
FAO as an automated ingestion source -- doing so would mean silently faking the fetch.

Instead, FAO is used the same way Chapter 2 (Literature Review) already uses it: as a
documented statistical/contextual reference (e.g. FAO, 2022, "The State of World
Fisheries and Aquaculture") describing global and regional fishing trends, cited in
docs/DATA_SOURCES.md and the report references. If FAO later publishes a stable
programmatic export, `fetch_fao_reference_stats()` below is the place to implement it.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

FAO_LIMITATION_NOTE = (
    "FAO fishery statistics have no stable public API/bulk-CSV endpoint (FishStatJ is "
    "desktop-only; the FAO Data Explorer is a session-based SPA). FAO is therefore used "
    "as a contextual/statistical reference in this project, not as an automated data "
    "feed -- IOTC is the operative, higher-resolution source for Indian Ocean tuna catch. "
    "See docs/DATA_SOURCES.md."
)


def fetch_fao_reference_stats() -> None:
    """Not implemented -- see module docstring. Raises to make the limitation explicit
    rather than silently returning fabricated data."""
    raise NotImplementedError(FAO_LIMITATION_NOTE)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(FAO_LIMITATION_NOTE)
