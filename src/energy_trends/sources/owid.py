"""Our World in Data's energy compilation.

Two distinct products are used here, and they do not agree with each other.
That is not a mistake in either: they count non-fossil electricity differently,
and the gap between them is one of the more consequential facts on this site.

`owid-energy-data.csv` -- the complete dataset, 1965 onward, built mainly on the
Energy Institute's Statistical Review. It uses the **substitution method**:
electricity from nuclear, hydro, solar and wind is scaled up by roughly 1/0.4 to
express the fossil fuel that would have been burned to generate it. Solar in
2024 reads about 5,150 TWh.

`global-energy-substitution.csv` -- despite the slug, this one is titled "Global
primary energy use by source" and measured as **total energy supply**, the IEA
convention: renewable electricity counted directly at face value, nuclear at its
heat input. Solar in 2024 reads about 2,170 TWh, a factor of 2.4 lower. Its
compensating virtue is reach: the World series is extended back to 1800 with
Vaclav Smil's historical estimates, and it is the only long run available.

So: the long-run chart comes from the second file, everything else from the
first, and no chart mixes them. `accounting_comparison` exists to show the size
of the discrepancy rather than bury it.
"""

from __future__ import annotations

import csv
import io
from functools import lru_cache

from ..http import get_text, parse_float
from ..model import Line

COMPLETE_CSV = "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv"
LONG_RUN_CSV = "https://ourworldindata.org/grapher/global-energy-substitution.csv"
CO2_CSV = "https://ourworldindata.org/grapher/co2-by-source.csv"
CALORIES_CSV = "https://ourworldindata.org/grapher/daily-per-capita-caloric-supply.csv"
POPULATION_CSV = "https://ourworldindata.org/grapher/population.csv"

# Regions chosen to explain the global line rather than to rank countries: the
# two that dominate the level, the one that dominates the growth, the bloc that
# is falling, and the continent whose absence from the chart is the point.
REGIONS = [
    ("World", "World"),
    ("China", "China"),
    ("United States", "United States"),
    ("European Union (27)", "European Union"),
    ("India", "India"),
    ("Africa", "Africa"),
]

CONTINENTS = ["Asia", "North America", "Europe", "Africa", "South America", "Oceania"]

HOURS_PER_YEAR = 8760.0


@lru_cache(maxsize=1)
def _complete() -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(get_text(COMPLETE_CSV))))


@lru_cache(maxsize=1)
def _long_run() -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(get_text(LONG_RUN_CSV))))


def _rows_for(country: str) -> list[dict[str, str]]:
    return [row for row in _complete() if row["country"] == country]


def _year_date(year: str) -> str:
    return f"{year}-01-01"


def _column(country: str, column: str, *, scale: float = 1.0) -> list[tuple[str, float]]:
    points = []
    for row in _rows_for(country):
        value = parse_float(row.get(column))
        if value is not None:
            points.append((_year_date(row["year"]), value * scale))
    return points


# ---- throughput ---------------------------------------------------------


# Ordered oldest-technology-first so the stack reads as layers laid down over
# time: biomass at the bottom, then coal, then oil and gas, then the rest.
LONG_RUN_SOURCES = [
    "Traditional biomass",
    "Coal",
    "Oil",
    "Gas",
    "Nuclear",
    "Hydropower",
    "Wind",
    "Solar",
    "Biofuels",
    "Other renewables",
]


def long_run_primary_energy() -> list[Line]:
    """Global primary energy by source since 1800, as a stack."""
    world = [row for row in _long_run() if row["Entity"] == "World"]

    lines = []
    for name in LONG_RUN_SOURCES:
        points: list[tuple[str, float]] = []
        for row in world:
            value = parse_float(row.get(name))
            # Stacked areas cannot carry gaps -- a missing year in one band
            # would silently shift every band above it -- so a source reads as
            # zero until it exists.
            points.append((_year_date(row["Year"]), value or 0.0))
        if any(value for _, value in points):
            lines.append(Line(name, points))
    return lines


def power_per_person() -> list[Line]:
    """Average continuous power drawn per person, in watts.

    OWID publishes kWh per person per year; dividing by the hours in a year
    turns an annual quantity into the rate it actually is, which is the form
    that can be compared with a human body's own throughput.
    """
    lines = []
    for entity, label in REGIONS:
        points = _column(entity, "energy_per_capita", scale=1000.0 / HOURS_PER_YEAR)
        if points:
            lines.append(Line(label, points))
    return lines


@lru_cache(maxsize=1)
def _calories() -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(get_text(CALORIES_CSV))))


@lru_cache(maxsize=1)
def _world_population() -> dict[str, float]:
    """{year: world population}. Reaches back to 10,000 BC; we use 1800 on."""
    out: dict[str, float] = {}
    for row in csv.DictReader(io.StringIO(get_text(POPULATION_CSV))):
        if row["Entity"] == "World":
            value = parse_float(row.get("Population"))
            if value is not None:
                out[row["Year"]] = value
    return out


@lru_cache(maxsize=1)
def _long_run_world_totals() -> dict[str, float]:
    """{year: total primary energy, TWh} summed across the long-run sources."""
    out: dict[str, float] = {}
    for row in _long_run():
        if row["Entity"] != "World":
            continue
        total = 0.0
        for key, raw in row.items():
            if key in ("Entity", "Code", "Year"):
                continue
            value = parse_float(raw)
            if value is not None:
                total += value
        if total > 0:
            out[row["Year"]] = total
    return out


# 1 kcal = 4184 J; a day is 86,400 s.
WATTS_PER_KCAL_PER_DAY = 4184.0 / 86400.0


def food_versus_all_energy() -> list[Line]:
    """What a person eats, against what a person uses. Both in watts.

    The measurement that makes the rest of this site a question about an
    organism rather than an industry: dietary intake is the energy humans
    actually run on, and everything above it is energy they have arranged to
    have burned on their behalf.

    The upper line is computed here rather than taken from OWID's
    `energy_per_capita`, which starts in 1965. Dividing the long-run supply
    series by population carries it back to 1800, where the interesting thing
    is: a person in 1800 commanded something like 650 W, so the ratio to
    dietary intake was nearer six than seventeen. Most of what this site
    measures was built in those two centuries.
    """
    totals = _long_run_world_totals()
    population = _world_population()

    energy = []
    for year in sorted(set(totals) & set(population)):
        people = population[year]
        if people > 0:
            # TWh/year -> W: 1e12 Wh spread over the hours in a year.
            energy.append((_year_date(year), totals[year] * 1e12 / HOURS_PER_YEAR / people))

    food = []
    for row in _calories():
        if row["Entity"] != "World":
            continue
        kcal = parse_float(row.get("Daily calorie supply per person"))
        if kcal is not None:
            food.append((_year_date(row["Year"]), kcal * WATTS_PER_KCAL_PER_DAY))

    return [
        Line("All energy per person", energy),
        Line("Dietary energy per person", food),
    ]


# OWID publishes no GDP for its own continental and bloc aggregates, so the two
# the site wants are built here from member states. Numerator and denominator
# are summed over the *same* members in each year -- a country with energy but
# no GDP that year is dropped from both -- so patchy coverage changes which
# countries the ratio describes rather than biasing the ratio itself.
EU27_ISO = """AUT BEL BGR HRV CYP CZE DNK EST FIN FRA DEU GRC HUN IRL ITA LVA LTU LUX MLT
NLD POL PRT ROU SVK SVN ESP SWE""".split()

AFRICA_ISO = """DZA AGO BEN BWA BFA BDI CPV CMR CAF TCD COM COD COG CIV DJI EGY GNQ ERI SWZ
ETH GAB GMB GHA GIN GNB KEN LSO LBR LBY MDG MWI MLI MRT MUS MAR MOZ NAM NER NGA RWA STP SEN
SYC SLE SOM ZAF SSD SDN TZA TGO TUN UGA ZMB ZWE""".split()


# OWID reports energy in TWh and GDP in international dollars, but publishes the
# ratio as kilowatt-hours per dollar. A terawatt-hour is 1e9 kWh.
KWH_PER_TWH = 1e9


def _aggregate_energy_per_gdp(codes: list[str]) -> list[tuple[str, float]]:
    members = set(codes)
    energy: dict[str, float] = {}
    gdp: dict[str, float] = {}

    for row in _complete():
        if (row.get("iso_code") or "").strip() not in members:
            continue
        terawatt_hours = parse_float(row.get("primary_energy_consumption"))
        output = parse_float(row.get("gdp"))
        if terawatt_hours is None or output is None or output <= 0:
            continue
        year = row["year"]
        energy[year] = energy.get(year, 0.0) + terawatt_hours
        gdp[year] = gdp.get(year, 0.0) + output

    return [(_year_date(y), energy[y] * KWH_PER_TWH / gdp[y]) for y in sorted(energy) if gdp.get(y)]


def energy_per_gdp() -> list[Line]:
    """Energy consumed per unit of economic output."""
    lines = []
    for entity, label in REGIONS:
        points = _column(entity, "energy_per_gdp")
        if points:
            lines.append(Line(label, points))

    for label, codes in (("European Union", EU27_ISO), ("Africa", AFRICA_ISO)):
        if any(line.name == label for line in lines):
            continue
        points = _aggregate_energy_per_gdp(codes)
        if points:
            lines.append(Line(label, points))
    return lines


def primary_energy_by_continent() -> list[Line]:
    """Total primary energy consumption, stacked by continent."""
    lines = []
    for continent in CONTINENTS:
        points = _column(continent, "primary_energy_consumption")
        if points:
            lines.append(Line(continent, points))
    return lines


# ---- sources ------------------------------------------------------------


def fossil_vs_low_carbon() -> list[Line]:
    """The two halves of the world's supply, in absolute terms.

    Kept absolute rather than as shares because the point is that low-carbon
    growth has so far been added on top of fossil consumption rather than
    subtracted from it, and a share chart hides that.
    """
    return [
        Line("Fossil fuels", _column("World", "fossil_fuel_consumption")),
        Line("Low-carbon", _column("World", "low_carbon_consumption")),
    ]


CHANGE_SOURCES = [
    ("coal_cons_change_twh", "Coal"),
    ("oil_cons_change_twh", "Oil"),
    ("gas_cons_change_twh", "Gas"),
    ("nuclear_cons_change_twh", "Nuclear"),
    ("hydro_cons_change_twh", "Hydro"),
    ("wind_cons_change_twh", "Wind"),
    ("solar_cons_change_twh", "Solar"),
    ("biofuel_cons_change_twh", "Biofuels"),
    ("other_renewables_cons_change_twh", "Other renewables"),
]


def annual_change_by_source() -> list[Line]:
    """Year-on-year change in world consumption, by source.

    The chart where solar's growth is visible: against a 175,000 TWh stock its
    share barely moves, but measured as the annual increment it now rivals the
    fossil fuels.
    """
    lines = []
    for column, label in CHANGE_SOURCES:
        points = _column("World", column)
        if points:
            lines.append(Line(label, points))
    return lines


def solar_wind_nuclear() -> list[Line]:
    """The three non-hydro low-carbon sources, on a log axis."""
    return [
        Line("Solar", _column("World", "solar_consumption")),
        Line("Wind", _column("World", "wind_consumption")),
        Line("Nuclear", _column("World", "nuclear_consumption")),
        Line("Hydro", _column("World", "hydro_consumption")),
    ]


# One of the two series reaches back to 1800, where solar and wind are zero and
# the two conventions trivially agree. The comparison only exists once there is
# something to disagree about.
COMPARISON_FROM = "1985"


def accounting_comparison() -> list[Line]:
    """Solar and wind as a share of world energy, under both conventions.

    Same technologies, same year, same publisher -- two answers differing by a
    factor of about 2.4, depending only on whether renewable electricity is
    counted at face value or scaled up to the fossil fuel it displaces. Most
    figures quoted in public are one of these two without saying which.
    """
    substitution = []
    for row in _rows_for("World"):
        solar = parse_float(row.get("solar_consumption"))
        wind = parse_float(row.get("wind_consumption"))
        total = parse_float(row.get("primary_energy_consumption"))
        if solar is not None and wind is not None and total and row["year"] >= COMPARISON_FROM:
            substitution.append((_year_date(row["year"]), (solar + wind) / total * 100))

    direct = []
    for row in _long_run():
        if row["Entity"] != "World" or row["Year"] < COMPARISON_FROM:
            continue
        values = {
            key: parse_float(value)
            for key, value in row.items()
            if key not in ("Entity", "Code", "Year")
        }
        total = sum(v for v in values.values() if v)
        solar, wind = values.get("Solar"), values.get("Wind")
        if total and solar is not None and wind is not None:
            direct.append((_year_date(row["Year"]), (solar + wind) / total * 100))

    return [
        Line("Substitution method (Energy Institute)", substitution),
        Line("Total energy supply (IEA convention)", direct),
    ]


# ---- conversion ---------------------------------------------------------


def electrification() -> list[Line]:
    """Electricity's share of final energy consumption."""
    lines = []
    for entity, label in REGIONS:
        points = _column(entity, "electricity_share_energy")
        if points:
            lines.append(Line(label, points))
    return lines


# ---- exhaust ------------------------------------------------------------


@lru_cache(maxsize=1)
def _co2() -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(get_text(CO2_CSV))))


# Same principle as the long-run stack: oldest fuel at the bottom.
CO2_SOURCES = ["Coal", "Oil", "Gas", "Flaring", "Cement", "Other industry"]


def co2_by_source() -> list[Line]:
    """World CO2 emissions by source, as a stack.

    The other end of the flow: what comes out after the energy has been used.
    Cement and other industry are included because they are in the source data
    and are not energy emissions at all -- they come from the chemistry of
    making the material, and no change to the energy system removes them.
    """
    world = [row for row in _co2() if row["Entity"] == "World"]

    lines = []
    for name in CO2_SOURCES:
        points = []
        for row in world:
            value = parse_float(row.get(name))
            # Published in tonnes; billions of tonnes is the unit the totals are
            # actually discussed in.
            points.append((_year_date(row["Year"]), (value or 0.0) / 1e9))
        if any(value for _, value in points):
            lines.append(Line(name, points))
    return lines
