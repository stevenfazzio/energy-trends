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
# comparison stays legible whichever way the estimate moves -- plus the United
# States, which is off that scale by more than an order of magnitude and is
# there to keep the whole comparison in proportion. Read it on the log scale.
COMPARISON_COUNTRIES = [
    "United States of America",
    "Poland",
    "Argentina",
    "Sweden",
    "Netherlands",
]

# Ember spells the US out in full; the rest of the site does not.
COUNTRY_LABELS = {"United States of America": "United States"}

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
            lines.append(Line(COUNTRY_LABELS.get(country, country), points))
    return lines
