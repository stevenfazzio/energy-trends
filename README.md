# Energy Trends

Time-series charts on how much energy humanity moves in a year, where it comes
from, and what it is spent on — rebuilt weekly from public sources and published
to GitHub Pages.

Nothing here is an original estimate. Every chart plots someone else's published
numbers and links back to them.

The organising question is closer to biology than to industry: how does a
species of eight billion acquire energy, and what does it do with it? So the
groups follow the flow — how much moves, where it comes from, what carries it,
what spends it, what comes out — and solar, wind and nuclear appear as
components of that flow rather than as the subject.

## How it works

A GitHub Actions job runs each Monday, fetches every series in the registry,
commits the result to `data/`, and deploys the static site.

```
src/energy_trends/
  registry.py     the list of charts -- the only file you edit to add one
  model.py        SeriesSpec / Line / Axis
  build.py        fetch -> data/*.json -> _site/
  http.py         shared session, retries, local response cache
  sources/        one module per upstream provider
data/             committed output, one JSON per series
manual/           hand-entered observations, one CSV per series, with citations
site/             index.html, app.js, style.css -- rendered with Plotly
events.toml       shock markers drawn across the charts
```

Weekly rather than daily: Ember publishes monthly, OWID a few times a year, and
the one daily upstream hands over its whole history on each request, so a weekly
run loses no data points — only freshness on the last one.

## The accounting problem

More than half the charts here depend on a convention, and the conventions move
the numbers by more than a factor of two. This is not a footnote; on a site
about magnitudes it is most of the difficulty.

**Substitution versus direct.** Ask what share of world energy is solar and
wind and there are two defensible answers, currently **6.4%** and **3.1%**. The
substitution method asks what fossil fuel would have been burned to generate the
same electricity, and so credits a solar panel with the waste heat of the power
station it displaces. Total energy supply — the IEA convention — counts the
electricity itself. Both of OWID's energy products are used here and *they use
different conventions*: `owid-energy-data.csv` is substitution, while the
long-run series behind `global-energy-substitution.csv` is total energy supply
despite its slug. No chart mixes them, every affected chart says which one it
uses, and `accounting-comparison` plots the gap directly.

**Capacity versus generation.** Solar's installed gigawatts exceed nuclear's
several times over while producing less electricity. The whole of that gap is
capacity factor — about 13% against about 79% — which is why the capacity chart,
the generation chart and the capacity-factor chart sit next to each other.

**Primary versus final.** Electricity is about a fifth of final energy. Charts
in the Electricity group describe that fifth, not the system.

**Estimates versus measurements.** Everything here is measured except the
Bitcoin series, which Cambridge infers from hash rate and an assumed hardware
mix. It is the only chart drawn with an uncertainty band, because it is the only
one whose publisher provides bounds — and those bounds span a factor of three.

## Running it locally

```sh
uv sync
uv run python -m energy_trends.build              # everything
uv run python -m energy_trends.build --only capacity-factors
uv run python -m energy_trends.build --fail-fast  # stop on the first fetch error

python3 -m http.server 8000 --directory _site
```

A failing upstream does not blank a chart: the previously committed JSON stays
in place and the page shows a "last refresh failed" badge.

A cold build downloads about 130 MB, most of it Ember's two full releases.
Responses are cached under `.cache/` for six hours, so iterating on one chart
does not refetch them.

## Adding a chart

1. Write a function in `src/energy_trends/sources/` returning `list[Line]`.
2. Add a `SeriesSpec` to `SERIES` in `registry.py`.
3. `uv run python -m energy_trends.build --only your-new-id --fail-fast`

The page is driven entirely by `data/manifest.json`; no front-end changes are
needed. Set `chart="area"` for a stack, `chart="area-percent"` for shares, and
give a `Line` a `band` if — and only if — the upstream publishes bounds.

## Sources

| Series | Source | Licence |
|---|---|---|
| Primary energy, per-capita, intensity, mix, electrification | [OWID — Energy dataset](https://github.com/owid/energy-data) | CC BY 4.0 |
| Primary energy since 1800 | [OWID — Global primary energy](https://ourworldindata.org/grapher/global-energy-substitution) | CC BY 4.0 |
| Dietary energy per person | [OWID — Daily calorie supply](https://ourworldindata.org/grapher/daily-per-capita-caloric-supply) | CC BY 4.0 |
| CO₂ by source | [OWID — CO₂ by source](https://ourworldindata.org/grapher/co2-by-source) | CC BY 4.0 |
| Electricity mix, demand, carbon intensity | [Ember — Monthly Electricity Data](https://ember-energy.org/data/monthly-electricity-data/) | CC BY 4.0 |
| Capacity, capacity factors, national demand | [Ember — Yearly Electricity Data](https://ember-energy.org/data/yearly-electricity-data/) | CC BY 4.0 |
| Bitcoin electricity consumption | [Cambridge CBECI](https://ccaf.io/cbnsi/cbeci) | — |
| Irish data centre electricity | [CSO Ireland MEC02](https://data.cso.ie/table/MEC02) | CC BY 4.0 |
| US consumption by sector | [EIA Monthly Energy Review](https://www.eia.gov/totalenergy/data/monthly/) | public domain |

Ember's data lives on a public GCS bucket rather than the documented
`ember-climate.org` paths, which are dead — and which answer with a decorated
200 HTML page rather than a 404, so `http.get_text` rejects an HTML content type
outright to keep that failure from looking like an empty dataset.

## Not here yet

**Global end use by sector.** Conceptually half the question — what the energy
is actually spent on — and the half with the worst data. IEA's World Energy
Balances are the canonical source and are paywalled; the Sankey endpoint I tried
404s. Eurostat's `nrg_bal_s` API returns full EU balances with no key and is the
obvious next step, and the US is already covered by the MER. Global is the gap.

**Primary aluminium smelting.** One of the loads most worth setting against
Bitcoin and data centres, and the reason the `manual/` mechanism exists here
with nothing in it yet. The International Aluminium Institute serves its
statistics from a JavaScript app whose API endpoint 404s; USGS is the fallback
but is annual and coarser.

**Global data centre consumption.** Ireland is the only country that meters it
as a category. Everywhere else — including the widely quoted IEA and LBNL
figures — is estimation published as PDF, which means `manual/` with a citation
per row rather than a feed.

**Nuclear construction.** Nuclear appears here only as generation and capacity,
which makes it look like nothing is happening — global capacity has been roughly
flat for thirty years while the narrative around it inverted. The story is in
construction starts, build durations and cost, which live in IAEA PRIS. Its
pages return HTML but the tables did not parse on a first attempt; it needs real
work rather than a quick scrape.

**Costs.** No LCOE, module prices or battery prices. Lazard and BloombergNEF
publish annually as PDF. OWID's `solar-pv-prices` grapher does expose the
1975–2024 module price series as a 1.5 KB CSV with no key, which would be the
cheapest thing on this list to add.

## Elsewhere

[Our World in Data — Energy](https://ourworldindata.org/energy) and
[Ember](https://ember-energy.org/data/) are fuller treatments of the same
territory. This site's only claims to a reason for existing are that it is
composed around one question, that it prefers monthly series where they exist,
and that it says out loud which accounting convention each number uses.
