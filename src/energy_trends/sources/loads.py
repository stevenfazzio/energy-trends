"""Comparisons that span two upstreams.

A load's electricity consumption means little on its own -- the useful question
is what it is comparable to. These functions put Cambridge's Bitcoin estimate
next to Ember's measured national and world demand, so the answer to "is this a
lot?" is a chart rather than an intuition.
"""

from __future__ import annotations

from collections import defaultdict

from ..model import Line
from . import cbeci, ember

# Chosen to bracket the Bitcoin network's current draw from both sides, so the
# comparison stays legible whichever way the estimate moves.
COMPARISON_COUNTRIES = ["Poland", "Argentina", "Sweden", "Netherlands"]

# Before this the network's consumption rounds to nothing on a linear axis.
FROM_YEAR = 2014


def _bitcoin_by_year() -> dict[str, float]:
    """Mean of the year's monthly annualised estimates.

    A single month-end reading would make the series track the hash rate's
    short-term noise; the mean is the better summary of what the network drew
    over the year.
    """
    monthly = cbeci.annualised_guess_by_month()
    grouped: dict[str, list[float]] = defaultdict(list)
    for month, value in monthly.items():
        grouped[month[:4]].append(value)
    return {year: sum(values) / len(values) for year, values in grouped.items()}


def bitcoin_vs_countries() -> list[Line]:
    """The Bitcoin network's draw against whole national electricity demands."""
    bitcoin = _bitcoin_by_year()
    demand = ember.annual_demand_by_area()

    years = sorted(year for year in bitcoin if int(year) >= FROM_YEAR)
    lines = [Line("Bitcoin network", [(f"{y}-01-01", bitcoin[y]) for y in years])]

    for country in COMPARISON_COUNTRIES:
        by_year = demand.get(country, {})
        points = [(f"{y}-01-01", by_year[y]) for y in years if y in by_year]
        if points:
            lines.append(Line(country, points))
    return lines


def bitcoin_share_of_world_electricity() -> list[Line]:
    """The Bitcoin network as a percentage of world electricity demand."""
    bitcoin = _bitcoin_by_year()
    world = ember.annual_demand_by_area().get("World", {})

    points = []
    for year in sorted(set(bitcoin) & set(world)):
        if int(year) >= FROM_YEAR and world[year] > 0:
            points.append((f"{year}-01-01", bitcoin[year] / world[year] * 100))
    return [Line("Bitcoin network", points)]
