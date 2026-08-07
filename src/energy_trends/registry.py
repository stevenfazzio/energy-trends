"""The chart registry: the one file you edit to add a chart.

Each SeriesSpec pairs a fetch function with the metadata the site needs to
render it. Order within a group is the order on the page.

The groups follow the energy flow rather than the technology -- how much moves,
where it comes from, what carries it, what spends it, what comes out -- so that
solar, wind and nuclear appear as components of a larger throughput rather than
as the subject.
"""

from __future__ import annotations

from .model import Axis, Group, SeriesSpec, Source
from .sources import cbeci, cso, eia, ember, loads, owid

OWID_ENERGY = Source(
    "Our World in Data — Energy dataset",
    "https://github.com/owid/energy-data",
    "CC BY 4.0",
)
OWID_LONG_RUN = Source(
    "Our World in Data — Global primary energy use by source",
    "https://ourworldindata.org/grapher/global-energy-substitution",
    "CC BY 4.0",
)
OWID_CO2 = Source(
    "Our World in Data — CO₂ emissions by source",
    "https://ourworldindata.org/grapher/co2-by-source",
    "CC BY 4.0",
)
EMBER_MONTHLY = Source(
    "Ember — Monthly Electricity Data",
    "https://ember-energy.org/data/monthly-electricity-data/",
    "CC BY 4.0",
)
EMBER_YEARLY = Source(
    "Ember — Yearly Electricity Data",
    "https://ember-energy.org/data/yearly-electricity-data/",
    "CC BY 4.0",
)
CBECI = Source(
    "Cambridge Bitcoin Electricity Consumption Index",
    "https://ccaf.io/cbnsi/cbeci",
)
CSO_IRELAND = Source(
    "Central Statistics Office Ireland — MEC02",
    "https://data.cso.ie/table/MEC02",
    "CC BY 4.0",
)
EIA_MER = Source(
    "EIA — Monthly Energy Review",
    "https://www.eia.gov/totalenergy/data/monthly/",
    "public domain",
)

# The caveat that governs half the numbers on this site, worded once.
SUBSTITUTION_NOTE = (
    "Counted by the substitution method: electricity from nuclear, hydro, solar and wind "
    "is scaled up by roughly 1/0.4 to represent the fossil fuel that would have been burned "
    "to generate it. Under the direct method those sources read about 2.4× lower and the "
    "world total is smaller. Neither convention is wrong; see the accounting chart."
)

GROUPS = [
    Group(
        "throughput",
        "Throughput",
        "How much energy humanity moves in a year, over the long run and per person.",
    ),
    Group(
        "sources",
        "Sources",
        "Where it comes from, and which sources are actually growing.",
    ),
    Group(
        "electricity",
        "Electricity",
        "About a fifth of the total, measured monthly rather than annually, and "
        "the part where the mix is changing fastest.",
    ),
    Group(
        "loads",
        "Loads",
        "What the energy is spent on, and whether a given load is large.",
    ),
    Group(
        "exhaust",
        "Exhaust",
        "What comes out the far end.",
    ),
]

SERIES = [
    # ---- throughput ----------------------------------------------------
    SeriesSpec(
        id="long-run-primary-energy",
        title="Global primary energy by source since 1800",
        description=(
            "Total energy supply, stacked by source, over two centuries. The layers "
            "accumulate rather than replace each other: the world burns roughly twice as "
            "much traditional biomass today as it did in 1800."
        ),
        group="throughput",
        sources=[OWID_LONG_RUN],
        fetch=owid.long_run_primary_energy,
        y=Axis(title="Primary energy (TWh/year)", tickformat=".2s", rangemode="tozero"),
        chart="area",
        annotations=False,
        notes=(
            "Measured as total energy supply, the IEA convention: renewable electricity at "
            "face value, nuclear at its heat input. This is not the same convention as the "
            "other charts in this group, and gives solar and wind figures about 2.4× lower — "
            "the comparison chart under Sources shows the gap. Before 1965 the series is "
            "Vaclav Smil's historical estimate, not measurement. Event markers are off here "
            "because two centuries of x-axis crowds them all into the last inch."
        ),
    ),
    SeriesSpec(
        id="power-per-person",
        title="Average power drawn per person",
        description=(
            "Annual energy consumption per head, expressed as the continuous power draw it "
            "actually is. For scale, an adult human's dietary intake runs around 100–150 W, "
            "so the world average is roughly seventeen times what people eat, and the "
            "American figure is nearer sixty."
        ),
        group="throughput",
        sources=[OWID_ENERGY],
        fetch=owid.power_per_person,
        y=Axis(title="Watts per person", tickformat=".3s", rangemode="tozero"),
        notes=SUBSTITUTION_NOTE,
    ),
    SeriesSpec(
        id="food-versus-all-energy",
        title="Dietary energy against all energy, per person",
        description=(
            "What a person eats, next to what a person uses, in the same units. Dietary "
            "intake is the energy a human body actually runs on; everything above it is "
            "energy arranged to be burned on that person's behalf. The ratio is about "
            "seventeen to one, up from thirteen in 1965 — and note that the lower line has "
            "been rising too."
        ),
        group="throughput",
        sources=[
            OWID_ENERGY,
            Source(
                "Our World in Data — Daily supply of calories per person",
                "https://ourworldindata.org/grapher/daily-per-capita-caloric-supply",
                "CC BY 4.0",
            ),
        ],
        fetch=owid.food_versus_all_energy,
        y=Axis(title="Watts per person", log=True, tickformat=".3s"),
        notes=(
            "Food is FAO's dietary energy *supply* — what reaches retail — so it runs above "
            "what people actually eat, by roughly the share that is wasted. Converted at "
            "4,184 J per kcal. A resting adult body dissipates something like 80–100 W, so "
            "the food line sitting near 145 W is the right order of magnitude for a "
            "population that also includes children and the sedentary. " + SUBSTITUTION_NOTE
        ),
    ),
    SeriesSpec(
        id="primary-energy-by-continent",
        title="Primary energy consumption by continent",
        description="Where in the world the energy is consumed, stacked to the world total.",
        group="throughput",
        sources=[OWID_ENERGY],
        fetch=owid.primary_energy_by_continent,
        y=Axis(title="Primary energy (TWh/year)", tickformat=".2s", rangemode="tozero"),
        chart="area",
        notes=SUBSTITUTION_NOTE,
    ),
    SeriesSpec(
        id="energy-per-gdp",
        title="Energy consumed per unit of economic output",
        description=(
            "Kilowatt-hours per international dollar of GDP — how much energy it takes to "
            "produce a unit of economic activity."
        ),
        group="throughput",
        sources=[OWID_ENERGY],
        fetch=owid.energy_per_gdp,
        y=Axis(title="kWh per international-$", tickformat=".2f", rangemode="tozero"),
        notes=(
            "GDP is in constant international dollars, so this is not distorted by inflation "
            "or exchange rates, but it does move with what a country makes as much as with "
            "how efficiently it makes it — offshoring heavy industry improves the ratio "
            "without any physical change. The EU and Africa are absent because OWID carries "
            "no GDP figure for those aggregates, and the series ends in 2022 for the same "
            "reason. " + SUBSTITUTION_NOTE
        ),
    ),
    # ---- sources -------------------------------------------------------
    SeriesSpec(
        id="primary-energy-mix",
        title="Share of world primary energy by source",
        description="The same total as above, normalised, so only the composition shows.",
        group="sources",
        sources=[OWID_ENERGY],
        fetch=owid.primary_energy_mix,
        y=Axis(title="Share of primary energy", tickformat=".0%"),
        chart="area-percent",
        notes=SUBSTITUTION_NOTE,
    ),
    SeriesSpec(
        id="fossil-vs-low-carbon",
        title="Fossil and low-carbon energy, in absolute terms",
        description=(
            "Deliberately not a share chart. Low-carbon energy has so far been added on top "
            "of fossil consumption rather than subtracted from it, and plotting shares would "
            "hide that the fossil line has kept climbing."
        ),
        group="sources",
        sources=[OWID_ENERGY],
        fetch=owid.fossil_vs_low_carbon,
        y=Axis(title="Primary energy (TWh/year)", tickformat=".2s", rangemode="tozero"),
        notes=SUBSTITUTION_NOTE,
    ),
    SeriesSpec(
        id="annual-change-by-source",
        title="Year-on-year change in world consumption, by source",
        description=(
            "The increment rather than the stock. Against a 175,000 TWh total, solar's share "
            "moves slowly; measured as the amount added each year it is now among the "
            "largest contributors. Points below zero are sources in retreat."
        ),
        group="sources",
        sources=[OWID_ENERGY],
        fetch=owid.annual_change_by_source,
        y=Axis(title="Change on previous year (TWh)", tickformat=".2s"),
        notes=(
            "Annual differences are noisy: a mild winter or one large economy's recession "
            "moves a line more than any trend in the technology. " + SUBSTITUTION_NOTE
        ),
    ),
    SeriesSpec(
        id="solar-wind-nuclear",
        title="Solar, wind, nuclear and hydro",
        description=(
            "The four large non-fossil sources on a log axis, where a constant growth rate "
            "is a straight line and the difference between the two that are compounding and "
            "the two that are not is visible directly."
        ),
        group="sources",
        sources=[OWID_ENERGY],
        fetch=owid.solar_wind_nuclear,
        y=Axis(title="Primary energy (TWh/year)", log=True, tickformat=".2s"),
        notes=SUBSTITUTION_NOTE,
    ),
    SeriesSpec(
        id="accounting-comparison",
        title="How much of world energy is solar and wind? Two answers",
        description=(
            "The same two technologies, the same years, the same publisher — differing by a "
            "factor of about 2.4 depending only on whether renewable electricity is counted "
            "at face value or scaled up to the fossil fuel it displaces. Most figures quoted "
            "in public are one of these without saying which."
        ),
        group="sources",
        sources=[OWID_ENERGY, OWID_LONG_RUN],
        fetch=owid.accounting_comparison,
        y=Axis(title="Share of primary energy (%)", tickformat=".1f", rangemode="tozero"),
        notes=(
            "The substitution method asks what fossil fuel would have been burned to produce "
            "the same electricity, and so credits a solar panel with the waste heat of the "
            "power station it replaces. Total energy supply counts the electricity itself. "
            "The first flatters renewables against fossil fuels; the second understates how "
            "much useful energy they deliver, since two-thirds of a thermal plant's input is "
            "lost as heat. The honest reading is that both are conventions, and that the "
            "single-number claims built on either should be treated accordingly."
        ),
    ),
    # ---- electricity ---------------------------------------------------
    SeriesSpec(
        id="electrification",
        title="Electricity's share of final energy",
        description=(
            "How much of the energy that reaches an end user arrives as electricity. This is "
            "the number that decides how much of the whole system the rest of this section "
            "describes — currently about a fifth, and climbing slowly."
        ),
        group="electricity",
        sources=[OWID_ENERGY],
        fetch=owid.electrification,
        y=Axis(title="Share of final energy (%)", tickformat=".0f", rangemode="tozero"),
        notes=(
            "Final energy, not primary: it excludes the fuel burned in power stations to make "
            "the electricity. Transport and industrial heat are most of what the remaining "
            "four-fifths goes to."
        ),
    ),
    SeriesSpec(
        id="world-electricity-mix",
        title="World electricity generation by fuel, monthly",
        description=(
            "Generation stacked by fuel, at monthly resolution. The annual figures smooth "
            "away a seasonal swing that is a real feature of the system: hydro follows the "
            "melt, solar the northern summer."
        ),
        group="electricity",
        sources=[EMBER_MONTHLY],
        fetch=ember.world_electricity_mix,
        y=Axis(title="Generation (TWh/month)", tickformat=".2s", rangemode="tozero"),
        chart="area",
        notes=(
            "Measured generation, no substitution scaling — so solar here is the electricity "
            "it actually produced. Ember's monthly coverage begins in 2019 and the most "
            "recent months are revised as national statistics land."
        ),
    ),
    SeriesSpec(
        id="solar-wind-share",
        title="Wind and solar as a share of generation",
        description="The same quantity as a percentage, for the regions that drive the total.",
        group="electricity",
        sources=[EMBER_MONTHLY],
        fetch=ember.solar_wind_share,
        y=Axis(title="Share of generation (%)", tickformat=".0f", rangemode="tozero"),
        notes=(
            "Monthly, so the seasonal cycle dominates the short-run wiggle; compare the same "
            "month across years rather than adjacent months."
        ),
    ),
    SeriesSpec(
        id="world-electricity-demand",
        title="Electricity demand",
        description=(
            "Total demand by region — the denominator for everything else in this section "
            "and the next."
        ),
        group="electricity",
        sources=[EMBER_MONTHLY],
        fetch=ember.world_electricity_demand,
        y=Axis(title="Demand (TWh/month)", tickformat=".2s", rangemode="tozero"),
    ),
    SeriesSpec(
        id="installed-capacity",
        title="World installed generating capacity by fuel",
        description=(
            "Nameplate capacity, stacked. Note how differently this reads from the generation "
            "chart above: solar's installed gigawatts overtook every other source years "
            "before its output did."
        ),
        group="electricity",
        sources=[EMBER_YEARLY],
        fetch=ember.installed_capacity,
        y=Axis(title="Installed capacity (GW)", tickformat=".2s", rangemode="tozero"),
        chart="area",
        notes=(
            "Capacity is what a fleet could deliver running flat out, not what it does "
            "deliver. The next chart is the conversion between the two."
        ),
    ),
    SeriesSpec(
        id="capacity-factors",
        title="Capacity factor by fuel",
        description=(
            "Generation divided by capacity times the hours in a year: the fraction of its "
            "nameplate rating each fleet actually delivers. This single chart explains most "
            "of the gap between the capacity and generation charts above."
        ),
        group="electricity",
        sources=[EMBER_YEARLY],
        fetch=ember.capacity_factors,
        y=Axis(title="Capacity factor", tickformat=".0%", rangemode="tozero"),
        notes=(
            "Solar sits near 13% and nuclear near 78%, so a gigawatt of one is not a gigawatt "
            "of the other — a distinction that headlines about capacity records routinely "
            "drop. Low factors are not all the same thing: solar's is set by the sun, "
            "gas-fired plant runs part-time by choice, and a coal fleet's decline reflects "
            "being outbid. 'Other renewables' is omitted: it is a residual category whose "
            "capacity and generation series do not cover the same plant, and dividing one by "
            "the other yields factors above 100%."
        ),
    ),
    # ---- loads ---------------------------------------------------------
    SeriesSpec(
        id="bitcoin-electricity",
        title="Electricity consumed by the Bitcoin network",
        description=(
            "Cambridge's annualised estimate, with the range they publish around it. The "
            "band is wide because neither the mining hardware mix nor its efficiency is "
            "observable; the central line alone would imply a precision the authors "
            "explicitly disclaim."
        ),
        group="loads",
        sources=[CBECI],
        fetch=cbeci.bitcoin_electricity,
        y=Axis(title="Annualised consumption (TWh/year)", tickformat=".0f", rangemode="tozero"),
        # None of the energy shocks has any claim on a hash rate.
        annotations=False,
        notes=(
            "An estimate, not a measurement — the only such series on this site, which is why "
            "it is the only one drawn with a band. Cambridge infers power draw from the "
            "network hash rate and an assumed distribution of mining hardware. Sampled at "
            "month end from a daily index."
        ),
    ),
    SeriesSpec(
        id="bitcoin-vs-countries",
        title="Bitcoin against national electricity demand",
        description=(
            "The same estimate placed next to whole countries' measured electricity demand, "
            "which is the only way the number means anything."
        ),
        group="loads",
        sources=[CBECI, EMBER_YEARLY],
        fetch=loads.bitcoin_vs_countries,
        y=Axis(title="Electricity (TWh/year)", tickformat=".3s", rangemode="tozero"),
        notes=(
            "Bitcoin is the mean of its monthly annualised estimates within each year; the "
            "countries are Ember's measured annual demand. Countries chosen to bracket the "
            "current estimate from both sides, not for any other reason."
        ),
    ),
    SeriesSpec(
        id="bitcoin-share-of-world-electricity",
        title="Bitcoin as a share of world electricity",
        description=(
            "The comparison that settles the magnitude question: a load the size of a "
            "mid-sized country is still a fraction of a percent of world demand."
        ),
        group="loads",
        sources=[CBECI, EMBER_YEARLY],
        fetch=loads.bitcoin_share_of_world_electricity,
        y=Axis(title="Share of world electricity demand (%)", tickformat=".2f", rangemode="tozero"),
        annotations=False,
    ),
    SeriesSpec(
        id="irish-data-centre-share",
        title="Data centres as a share of Ireland's electricity",
        description=(
            "Ireland is the only country that meters data centre consumption as its own "
            "statistical category and publishes it quarterly. Everywhere else the figure is "
            "an estimate, which makes this the best actual observation available of what "
            "data centres draw from a grid."
        ),
        group="loads",
        sources=[CSO_IRELAND],
        fetch=cso.irish_data_centre_share,
        y=Axis(title="Share of metered electricity (%)", tickformat=".0f", rangemode="tozero"),
        notes=(
            "One small country hosting a disproportionate share of European capacity, so this "
            "is an early case rather than a representative one. Metered consumption only, "
            "which excludes any on-site generation."
        ),
    ),
    SeriesSpec(
        id="us-energy-by-sector",
        title="US energy consumption by end-use sector",
        description=(
            "Monthly since 1949 — by a wide margin the longest high-frequency record of a "
            "whole national energy system that is free to obtain. Included because no "
            "equivalent sectoral split exists globally."
        ),
        group="loads",
        sources=[EIA_MER],
        fetch=eia.us_energy_by_sector,
        y=Axis(title="Consumption (TWh/month)", tickformat=".3s", rangemode="tozero"),
        notes=(
            "Converted from trillion Btu at 0.293 TWh each. Sector totals include the "
            "electricity each sector uses, attributed to the sector rather than to power "
            "generation, so the four lines partition the national total. Month lengths are "
            "not normalised, so February always dips."
        ),
    ),
    # ---- exhaust -------------------------------------------------------
    SeriesSpec(
        id="co2-by-source",
        title="World CO₂ emissions by source",
        description="What comes out the far end, stacked by where it came from.",
        group="exhaust",
        sources=[OWID_CO2],
        fetch=owid.co2_by_source,
        y=Axis(title="CO₂ (billion tonnes/year)", tickformat=".1f", rangemode="tozero"),
        chart="area",
        notes=(
            "Cement and other industry are not energy emissions: they come from the chemistry "
            "of making the material, and no change to the energy system removes them."
        ),
    ),
    SeriesSpec(
        id="grid-carbon-intensity",
        title="Carbon intensity of electricity",
        description=(
            "Grams of CO₂ per kilowatt-hour generated. The cleanest single measure of how far "
            "the electricity transition has actually got, since it moves only when the mix does."
        ),
        group="exhaust",
        sources=[EMBER_MONTHLY],
        fetch=ember.grid_carbon_intensity,
        y=Axis(title="gCO₂ per kWh", tickformat=".0f", rangemode="tozero"),
        notes=(
            "Seasonal: intensity rises in winter when demand is met by whatever can be "
            "dispatched. Compare the same month across years."
        ),
    ),
    SeriesSpec(
        id="power-sector-emissions",
        title="Monthly CO₂ from electricity generation",
        description="Power-sector emissions by fuel, at the resolution where a peak would show.",
        group="exhaust",
        sources=[EMBER_MONTHLY],
        fetch=ember.power_sector_emissions,
        y=Axis(title="CO₂ (Mt/month)", tickformat=".3s", rangemode="tozero"),
        chart="area",
    ),
]
