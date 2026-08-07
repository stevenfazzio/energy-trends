"""Ireland's Central Statistics Office, via the PxStat API.

Ireland is the only country that meters data centre electricity as its own
statistical category and publishes it quarterly. Everywhere else the figure is
an estimate assembled from utility filings and hardware shipments. That makes a
small country on the edge of Europe the best available observation of what data
centres actually draw from a grid -- and, because Ireland hosts a
disproportionate share of European capacity, an early look at where a heavily
loaded grid ends up.

PxStat answers in JSON-stat 2.0: a flat `value` array to be indexed by the
Cartesian product of the dimensions, in the order given by `id`.
"""

from __future__ import annotations

from functools import lru_cache

from ..http import get_json
from ..model import Line

DATASET = "MEC02"
URL = f"https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/{DATASET}/JSON-stat/2.0/en"

DATA_CENTRES = "10"
OTHER = "20"


@lru_cache(maxsize=1)
def _cube() -> dict:
    payload = get_json(URL)
    return payload.get("result", payload)


def _quarter_date(label: str) -> str:
    """'2015Q1' -> the first day of that quarter."""
    year, quarter = label.split("Q")
    return f"{year}-{(int(quarter) - 1) * 3 + 1:02d}-01"


def _series() -> dict[str, dict[str, float]]:
    """-> {category code: {ISO date: gigawatt-hours}}."""
    cube = _cube()
    ids: list[str] = cube["id"]
    sizes: list[int] = cube["size"]
    values: list[float | None] = cube["value"]

    # Category order within each dimension is given by its index map, which may
    # be a dict of code -> position or a bare list.
    order = []
    for dim in ids:
        index = cube["dimension"][dim]["category"]["index"]
        if isinstance(index, dict):
            order.append([code for code, _ in sorted(index.items(), key=lambda kv: kv[1])])
        else:
            order.append(list(index))

    quarter_dim = ids.index("TLIST(Q1)")
    category_dim = next(i for i, dim in enumerate(ids) if dim.startswith("C"))

    out: dict[str, dict[str, float]] = {}
    for flat, value in enumerate(values):
        if value is None:
            continue
        # Unflatten a row-major index into one coordinate per dimension.
        coords, rest = [], flat
        for size in reversed(sizes):
            coords.append(rest % size)
            rest //= size
        coords.reverse()

        code = order[category_dim][coords[category_dim]]
        when = _quarter_date(order[quarter_dim][coords[quarter_dim]])
        out.setdefault(code, {})[when] = value
    return out


def irish_data_centre_share() -> list[Line]:
    """Data centres as a percentage of Ireland's metered electricity."""
    series = _series()
    centres = series.get(DATA_CENTRES, {})
    others = series.get(OTHER, {})

    points = []
    for when in sorted(set(centres) & set(others)):
        total = centres[when] + others[when]
        if total > 0:
            points.append((when, centres[when] / total * 100))
    return [Line("Data centres", points)]


def irish_data_centre_consumption() -> list[Line]:
    """Metered electricity in Ireland, data centres against everyone else."""
    series = _series()
    lines = []
    for code, label in ((OTHER, "All other customers"), (DATA_CENTRES, "Data centres")):
        by_date = series.get(code, {})
        if by_date:
            lines.append(Line(label, sorted(by_date.items())))
    return lines
