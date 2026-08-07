"""Cambridge Bitcoin Electricity Consumption Index.

The Cambridge Centre for Alternative Finance estimates the Bitcoin network's
power draw from its hash rate and an assumed mix of mining hardware. Because
neither the hardware mix nor its efficiency is observable, they publish a lower
bound, an upper bound and a best guess, and the bounds are far apart -- often a
factor of three. Plotting the best guess alone would assert a precision the
authors explicitly disclaim, so this is the one source on the site that carries
its band through to the chart.

The endpoint serves gzipped CSV under a text/html content type, hence
`allow_html`. Its first line is a note about the assumed electricity price
rather than a header row.
"""

from __future__ import annotations

import csv
import io
from functools import lru_cache

from ..http import get_text, parse_float
from ..model import Line

CBECI_CSV = "https://ccaf.io/cbeci/api/v1.2.0/download/data"

GUESS = "annualised consumption GUESS, TWh"
LOWER = "annualised consumption MIN, TWh"
UPPER = "annualised consumption MAX, TWh"


@lru_cache(maxsize=1)
def _rows() -> list[dict[str, str]]:
    text = get_text(CBECI_CSV, allow_html=True)
    lines = text.splitlines()
    header = next((i for i, line in enumerate(lines) if line.startswith("Timestamp")), None)
    if header is None:
        raise ValueError("CBECI download has no Timestamp header row")
    return list(csv.DictReader(io.StringIO("\n".join(lines[header:]))))


def _monthly() -> list[dict[str, str]]:
    """One observation per month -- the last of each.

    The index is published daily, but it measures an annualised rate: sixteen
    years of daily points would be ~5,900 values per line carrying no
    information a month-end sample doesn't already have.
    """
    by_month: dict[str, dict[str, str]] = {}
    for row in _rows():
        day = (row.get("Date and Time") or "")[:10]
        if len(day) == 10:
            by_month[day[:7]] = row
    return [by_month[month] for month in sorted(by_month)]


def bitcoin_electricity() -> list[Line]:
    """Annualised electricity consumption of the Bitcoin network, with bounds."""
    points: list[tuple[str, float | None]] = []
    band: list[tuple[str, float | None, float | None]] = []

    for row in _monthly():
        day = row["Date and Time"][:10]
        guess = parse_float(row.get(GUESS))
        low = parse_float(row.get(LOWER))
        high = parse_float(row.get(UPPER))
        if guess is None:
            continue
        points.append((day, guess))
        if low is not None and high is not None:
            band.append((day, low, high))

    return [Line("Bitcoin network", points, band=band or None)]


def annualised_guess_by_month() -> dict[str, float]:
    """{YYYY-MM: best-guess annualised TWh}, for comparisons in `loads`."""
    out = {}
    for row in _monthly():
        guess = parse_float(row.get(GUESS))
        if guess is not None:
            out[row["Date and Time"][:7]] = guess
    return out
