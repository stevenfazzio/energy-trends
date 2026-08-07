"""Ember's electricity data.

Ember publishes two full releases as plain CSVs on a public bucket, no key
required: a monthly file running from 2019 and a yearly one from 2000. Both are
long format -- Area, Date/Year, Category, Subcategory, Variable, Unit, Value --
so every series here is a filter over the same shape.

The files are large (70 MB and 49 MB), which is why both loaders are memoised
and why the HTTP layer caches to disk. A build touches each URL once.

Ember measures generation directly, in terawatt-hours sent out. None of the
substitution-method scaling that applies to OWID's primary energy figures
applies here, so electricity numbers on this site are all at face value.
"""

from __future__ import annotations

import csv
import io
from functools import lru_cache

from ..http import get_text, parse_float
from ..model import Line

BUCKET = "https://storage.googleapis.com/emb-prod-bkt-publicdata/public-downloads"
MONTHLY_CSV = f"{BUCKET}/monthly_full_release_long_format.csv"
YEARLY_CSV = f"{BUCKET}/yearly_full_release_long_format.csv"

HOURS_PER_YEAR = 8760.0

# Fossils at the bottom, then the low-carbon sources, with the two that are
# actually moving on top where their growth is legible against the stack.
FUEL_ORDER = [
    "Coal",
    "Gas",
    "Other Fossil",
    "Nuclear",
    "Hydro",
    "Bioenergy",
    "Other Renewables",
    "Wind",
    "Solar",
]

# Ember's own area labels, paired with the names used elsewhere on the site.
# Ember spells the US out in full and abbreviates the EU; OWID does the reverse.
REGIONS = [
    ("World", "World"),
    ("China", "China"),
    ("United States of America", "United States"),
    ("EU", "European Union"),
    ("India", "India"),
]


@lru_cache(maxsize=1)
def _monthly() -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(get_text(MONTHLY_CSV))))


@lru_cache(maxsize=1)
def _yearly() -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(get_text(YEARLY_CSV))))


def _monthly_points(
    area: str, category: str, subcategory: str, variable: str, unit: str
) -> list[tuple[str, float]]:
    points = []
    for row in _monthly():
        if (
            row["Area"] == area
            and row["Category"] == category
            and row["Subcategory"] == subcategory
            and row["Variable"] == variable
            and row["Unit"] == unit
        ):
            value = parse_float(row["Value"])
            if value is not None:
                points.append((row["Date"], value))
    return sorted(points)


def _yearly_values(
    area: str, category: str, subcategory: str, unit: str
) -> dict[str, dict[str, float]]:
    """-> {variable: {year: value}} for one area/category/unit combination."""
    out: dict[str, dict[str, float]] = {}
    for row in _yearly():
        if (
            row["Area"] == area
            and row["Category"] == category
            and row["Subcategory"] == subcategory
            and row["Unit"] == unit
        ):
            value = parse_float(row["Value"])
            if value is not None:
                out.setdefault(row["Variable"], {})[row["Year"]] = value
    return out


def _year_date(year: str) -> str:
    return f"{year}-01-01"


# ---- generation ---------------------------------------------------------


def world_electricity_mix() -> list[Line]:
    """Monthly world generation by fuel, as a stack.

    Monthly rather than annual because the seasonal swing is real: hydro peaks
    with the melt, solar with the northern summer, and smoothing that away
    would hide how much of the grid's shape is weather.
    """
    lines = []
    for fuel in FUEL_ORDER:
        points = _monthly_points("World", "Electricity generation", "Fuel", fuel, "TWh")
        if points:
            lines.append(Line(fuel, points))
    return lines


def solar_wind_share() -> list[Line]:
    """Wind and solar as a share of generation, monthly, by region."""
    lines = []
    for area, label in REGIONS:
        points = _monthly_points(
            area, "Electricity generation", "Aggregate fuel", "Wind and Solar", "%"
        )
        if points:
            lines.append(Line(label, points))
    return lines


def annual_demand_by_area() -> dict[str, dict[str, float]]:
    """-> {area: {year: TWh}} electricity demand, for cross-source comparisons."""
    out: dict[str, dict[str, float]] = {}
    for row in _yearly():
        if (
            row["Category"] == "Electricity demand"
            and row["Subcategory"] == "Demand"
            and row["Unit"] == "TWh"
        ):
            value = parse_float(row["Value"])
            if value is not None:
                out.setdefault(row["Area"], {})[row["Year"]] = value
    return out


def world_electricity_demand() -> list[Line]:
    """Total electricity demand, monthly."""
    lines = []
    for area, label in REGIONS:
        points = _monthly_points(area, "Electricity demand", "Demand", "Demand", "TWh")
        if points:
            lines.append(Line(label, points))
    return lines


# ---- capacity -----------------------------------------------------------


def installed_capacity() -> list[Line]:
    """World installed generating capacity by fuel, as a stack."""
    capacity = _yearly_values("World", "Capacity", "Fuel", "GW")

    lines = []
    for fuel in FUEL_ORDER:
        by_year = capacity.get(fuel)
        if not by_year:
            continue
        lines.append(Line(fuel, [(_year_date(y), v) for y, v in sorted(by_year.items())]))
    return lines


# "Other Renewables" is a residual bucket -- geothermal, wave, tidal and
# whatever else does not fit -- and Ember's capacity and generation series for
# it plainly do not cover the same set of plant: the ratio reaches 133% in the
# early 2000s, which is not a capacity factor but a coverage mismatch. Rather
# than plot a physical impossibility, the category is left off this chart.
NO_MEANINGFUL_CAPACITY_FACTOR = {"Other Renewables"}


def capacity_factors() -> list[Line]:
    """What fraction of its nameplate rating each fleet actually delivers.

    Generation divided by capacity times hours in the year. This is the
    conversion between the two numbers that public discussion routinely
    conflates: solar's installed gigawatts exceed nuclear's several times over
    while producing less electricity, and the whole of that gap is here.
    """
    capacity = _yearly_values("World", "Capacity", "Fuel", "GW")
    generation = _yearly_values("World", "Electricity generation", "Fuel", "TWh")

    lines = []
    for fuel in FUEL_ORDER:
        if fuel in NO_MEANINGFUL_CAPACITY_FACTOR:
            continue
        caps, gens = capacity.get(fuel, {}), generation.get(fuel, {})
        points = []
        for year in sorted(set(caps) & set(gens)):
            gigawatts = caps[year]
            if gigawatts <= 0:
                continue
            factor = gens[year] * 1000 / (gigawatts * HOURS_PER_YEAR)
            # A fleet cannot deliver more than its nameplate over a full year.
            # Anything above 1 means the two series disagree about what plant
            # they cover, so the point is not a measurement of anything.
            if 0 < factor <= 1:
                points.append((_year_date(year), factor))
        if points:
            lines.append(Line(fuel, points))
    return lines


# ---- emissions ----------------------------------------------------------


def grid_carbon_intensity() -> list[Line]:
    """Grams of CO2 per kilowatt-hour generated, monthly, by region."""
    lines = []
    for area, label in REGIONS:
        points = _monthly_points(
            area, "Power sector emissions", "CO2 intensity", "CO2 intensity", "gCO2/kWh"
        )
        if points:
            lines.append(Line(label, points))
    return lines


def power_sector_emissions() -> list[Line]:
    """Monthly CO2 from electricity generation, by fuel, as a stack."""
    lines = []
    for fuel in ("Coal", "Gas", "Other Fossil", "Bioenergy"):
        points = _monthly_points("World", "Power sector emissions", "Fuel", fuel, "mtCO2")
        if points and any(v for _, v in points):
            lines.append(Line(fuel, points))
    return lines
