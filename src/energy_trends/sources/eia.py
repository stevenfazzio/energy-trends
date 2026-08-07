"""US Energy Information Administration, Monthly Energy Review.

The MER's table browser exports plain CSV with no API key, which the v2 JSON API
does require. The series run monthly from 1949, which is by a wide margin the
longest high-frequency record of a whole national energy system available for
free -- and the United States is a big enough share of the world total that its
sectoral split is worth having even though no equivalent exists globally.

Rows are keyed by MSN (EIA's series code) and YYYYMM, where month 13 is the
annual total and has to be dropped or every year would be counted twice.
"""

from __future__ import annotations

from functools import lru_cache

from ..http import get_csv, parse_float
from ..model import Line

BROWSER_CSV = "https://www.eia.gov/totalenergy/data/browser/csv.php?tbl={table}"

# 1 trillion Btu = 0.29307 TWh.
TWH_PER_TRILLION_BTU = 0.293071

# Each sector's total-consumption series lives in its own table.
SECTORS = [
    ("T02.05", "TEACBUS", "Transportation"),
    ("T02.04", "TEICBUS", "Industrial"),
    ("T02.02", "TERCBUS", "Residential"),
    ("T02.03", "TECCBUS", "Commercial"),
]


@lru_cache(maxsize=8)
def _table(table: str) -> tuple[dict[str, str], ...]:
    return tuple(get_csv(BROWSER_CSV.format(table=table)))


def _monthly_points(table: str, msn: str, *, scale: float) -> list[tuple[str, float]]:
    points = []
    for row in _table(table):
        if row.get("MSN") != msn:
            continue
        stamp = (row.get("YYYYMM") or "").strip()
        if len(stamp) != 6 or stamp[4:] == "13":  # 13 = the year's own total
            continue
        value = parse_float(row.get("Value"))
        if value is not None:
            points.append((f"{stamp[:4]}-{stamp[4:]}-01", value * scale))
    return sorted(points)


def us_energy_by_sector() -> list[Line]:
    """US energy consumption by end-use sector, monthly since 1949."""
    lines = []
    for table, msn, label in SECTORS:
        points = _monthly_points(table, msn, scale=TWH_PER_TRILLION_BTU)
        if points:
            lines.append(Line(label, points))
    return lines
