"""Core data model shared by every source adapter and the build pipeline."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

# A point is (ISO date, value). Values may be None to represent a genuine gap in
# the series -- Plotly renders those as a break in the line rather than
# interpolating across them.
Point = tuple[str, float | None]

# (ISO date, low, high). Used only by sources that publish a range rather than a
# single figure.
BandPoint = tuple[str, float | None, float | None]


@dataclass
class Line:
    """One plotted line. A series with a geographic or categorical dimension
    contributes several of these; a plain series contributes exactly one."""

    name: str
    points: list[Point]

    # An uncertainty band drawn behind the line. Present only where the upstream
    # publishes bounds of its own -- Cambridge's Bitcoin index is the case in
    # point, where the plausible range spans a factor of three and drawing the
    # central estimate alone would assert a precision the source disclaims.
    # We never synthesise one.
    band: list[BandPoint] | None = None

    def sorted(self) -> Line:
        return Line(
            self.name,
            sorted(self.points, key=lambda p: p[0]),
            sorted(self.band, key=lambda p: p[0]) if self.band else None,
        )

    def to_dict(self) -> dict:
        out: dict = {"name": self.name, "points": [list(p) for p in self.points]}
        if self.band:
            out["band"] = [list(p) for p in self.band]
        return out


@dataclass
class Axis:
    title: str = ""
    log: bool = False
    # Plotly d3-format string, e.g. ".2s" for SI prefixes, "$,.0f", ".1%"
    tickformat: str | None = None
    # "tozero" pins a linear axis at 0 so growth isn't visually exaggerated.
    rangemode: str | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v not in (None, "", False)}


@dataclass
class Source:
    name: str
    url: str
    license: str | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class SeriesSpec:
    """Everything needed to fetch, store and render one chart.

    Adding a chart to the site means adding one of these to the registry.
    """

    id: str
    title: str
    description: str
    group: str
    # Usually one, but a series assembled from several publications deserves a
    # link to each.
    sources: list[Source]
    fetch: Callable[[], list[Line]]
    y: Axis = field(default_factory=Axis)

    # "recompute": the upstream source holds full history, so every run rebuilds
    #   the series from scratch and picks up any upstream revisions.
    # "append":    the upstream source only exposes a current value, so each run
    #   appends today's observation to whatever we have already recorded.
    mode: str = "recompute"

    # Whether to draw the shared event markers from events.toml.
    annotations: bool = True

    # "line" draws one trace per Line. "area" declares the series a
    # decomposition of a whole, which earns it three views in the front end --
    # stacked, normalised to 100%, and plain lines with a computed total -- so
    # one chart answers what used to take three.
    chart: str = "line"

    # Months in the moving average offered on monthly series; 0 hides the
    # control. Twelve is the useful one: it takes out the seasonal cycle, which
    # on this data is large enough to hide the trend entirely.
    smooth_months: int = 0
    smooth_default: bool = True

    # Plotly line shape. "hv" draws a staircase, which is the honest rendering
    # for a running maximum: the value holds until something beats it.
    line_shape: str = "linear"

    # Caveats worth showing the reader directly under the chart. On this site
    # that is mostly accounting convention, which moves some of these numbers by
    # more than a factor of two.
    notes: str = ""

    def meta(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "group": self.group,
            "sources": [source.to_dict() for source in self.sources],
            "y": self.y.to_dict(),
            "mode": self.mode,
            "annotations": self.annotations,
            "chart": self.chart,
            "smooth_months": self.smooth_months,
            "smooth_default": self.smooth_default,
            "line_shape": self.line_shape,
            "notes": self.notes,
        }


@dataclass
class Group:
    id: str
    title: str
    blurb: str = ""
