"""Series typed in by hand, from sources with no machine-readable feed.

Every row carries its own source and URL. If a number here cannot be traced to a
published release, it does not belong in the file. The loader refuses a row
without a URL rather than letting an uncited figure onto a chart.

Nothing uses this yet. It is here because the two loads most worth adding to the
site -- global data centre consumption and primary aluminium smelting -- have no
free feed between them, and when they are added this is where they go. See the
README.
"""

from __future__ import annotations

import csv
from pathlib import Path

from ..model import Line

MANUAL_DIR = Path(__file__).resolve().parents[3] / "manual"

REQUIRED_COLUMNS = {"date", "line", "value", "source", "url"}


def series(name: str) -> list[Line]:
    """Read manual/<name>.csv into one Line per distinct `line` value."""
    path = MANUAL_DIR / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"no hand-entered data at {path}")

    with path.open() as handle:
        rows = list(csv.DictReader(handle))

    if rows and not REQUIRED_COLUMNS.issubset(rows[0]):
        missing = REQUIRED_COLUMNS - set(rows[0])
        raise ValueError(f"{path.name} is missing column(s): {', '.join(sorted(missing))}")

    grouped: dict[str, list[tuple[str, float]]] = {}
    order: list[str] = []
    for row in rows:
        label = (row.get("line") or "").strip()
        when = (row.get("date") or "").strip()
        if not label or not when:
            continue
        if not row.get("url", "").strip():
            raise ValueError(f"{path.name}: '{label}' at {when} has no source URL")
        if label not in grouped:
            grouped[label] = []
            order.append(label)
        grouped[label].append((when, float(row["value"])))

    return [Line(label, sorted(grouped[label])) for label in order]
