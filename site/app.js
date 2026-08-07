/* Renders one Plotly chart per series listed in data/manifest.json.
 *
 * Everything on the page is driven by the manifest, so adding a chart is a
 * change to the Python registry alone -- no edits here.
 *
 * Three chart kinds: plain lines, stacked areas (`area`, `area-percent`), and
 * lines carrying an uncertainty band. */

const PALETTE = [
  '#2f6fdd', '#e2622a', '#189f6d', '#a259d9',
  '#d4a017', '#c94f7c', '#4aa3c7', '#7a8794',
];

/* A fuel keeps its colour wherever it appears, so the generation, capacity and
 * emissions charts can be read against each other. Conventional where a
 * convention exists: coal grey, gas orange, solar yellow, hydro blue.
 *
 * Every value here clears a 3:1 contrast ratio against both the light and the
 * dark panel background, which rules out the darker greys and browns the
 * fossil fuels would otherwise get: a 2px line at 1.9:1 is invisible on a dark
 * page, whatever it looks like on a white one. */
const NAMED_COLOURS = {
  /* fuels */
  'Coal': '#7f7f89',
  'Oil': '#9c7348',
  'Gas': '#d98b3a',
  'Other Fossil': '#6b7280',
  'Nuclear': '#8e5fd9',
  'Hydro': '#2f7fd0',
  'Hydropower': '#2f7fd0',
  'Wind': '#3fae9e',
  'Solar': '#e8b81e',
  'Bioenergy': '#6f9e4c',
  'Biofuels': '#6f9e4c',
  'Other Renewables': '#9aa66b',
  'Other renewables': '#9aa66b',
  'Traditional biomass': '#8a7b5c',
  /* aggregates */
  'Fossil fuels': '#8a8a92',
  'Low-carbon': '#2f9e6d',
  /* regions -- World is deliberately absent; see THEME_COLOURS */
  'China': '#e2622a',
  'United States': '#2f6fdd',
  'European Union': '#189f6d',
  'India': '#a259d9',
  'Africa': '#d4a017',
  /* CO2 sources */
  'Cement': '#a0a0a8',
  'Flaring': '#c94f7c',
  'Other industry': '#7a8794',
};

/* Series whose colour has to follow the theme rather than sit at a fixed hex.
 * World is the line these regional charts exist to show, so it takes the
 * page's own ink colour -- near-black on light, near-white on dark -- which no
 * fixed value can do. */
const THEME_COLOURS = { 'World': '--ink' };

/* ...and it is drawn heavier, and last, so it stays readable where the regions
 * cross it. */
const EMPHASISED = new Set(['World']);

/* Charts with few points get visible markers; dense ones would be a smear. */
const MARKER_THRESHOLD = 60;

const state = { charts: [], showEvents: true, events: [] };

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

function theme() {
  return {
    ink: css('--ink'),
    soft: css('--ink-soft'),
    faint: css('--ink-faint'),
    rule: css('--rule'),
  };
}

function colourFor(name, index) {
  if (THEME_COLOURS[name]) return css(THEME_COLOURS[name]);
  return NAMED_COLOURS[name] || PALETTE[index % PALETTE.length];
}

/* Bands are drawn in the line's own colour at low opacity, so a chart with two
 * banded series stays readable. */
function translucent(hex, alpha) {
  const value = parseInt(hex.slice(1), 16);
  return `rgba(${value >> 16 & 255}, ${value >> 8 & 255}, ${value & 255}, ${alpha})`;
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

const isStacked = (series) => series.chart === 'area' || series.chart === 'area-percent';

/* ---- chart construction ------------------------------------------------ */

function areaTraces(series) {
  const format = (series.y || {}).tickformat;
  return series.lines.map((line, i) => {
    const colour = colourFor(line.name, i);
    return {
      type: 'scatter',
      mode: 'lines',
      name: line.name,
      x: line.points.map((p) => p[0]),
      y: line.points.map((p) => p[1]),
      stackgroup: 'one',
      /* 'fraction' rather than 'percent' so a ".0%" tickformat is honest about
       * the units instead of rendering 20 as 2000%. */
      groupnorm: series.chart === 'area-percent' ? 'fraction' : undefined,
      line: { width: 0.5, color: colour },
      fillcolor: translucent(colour, 0.85),
      yhoverformat: format,
      hovertemplate: '%{y}<extra>%{fullData.name}</extra>',
    };
  });
}

/* Two invisible traces per band: the lower bound, then the upper filling down
 * to it. They must precede the line traces so the central estimate draws on
 * top of its own shading. */
function bandTraces(series) {
  const out = [];
  series.lines.forEach((line, i) => {
    if (!line.band || !line.band.length) return;
    const colour = colourFor(line.name, i);
    const x = line.band.map((p) => p[0]);
    const common = {
      type: 'scatter',
      mode: 'lines',
      line: { width: 0 },
      hoverinfo: 'skip',
      showlegend: false,
      legendgroup: line.name,
    };
    out.push({ ...common, x, y: line.band.map((p) => p[1]) });
    out.push({
      ...common,
      x,
      y: line.band.map((p) => p[2]),
      fill: 'tonexty',
      fillcolor: translucent(colour, 0.16),
    });
  });
  return out;
}

function lineTraces(series) {
  const dense = series.lines.some((line) => line.points.length > MARKER_THRESHOLD);
  const format = (series.y || {}).tickformat;
  const built = series.lines.map((line, i) => ({
    type: 'scatter',
    mode: dense ? 'lines' : 'lines+markers',
    name: line.name,
    x: line.points.map((p) => p[0]),
    y: line.points.map((p) => p[1]),
    line: {
      color: colourFor(line.name, i),
      width: EMPHASISED.has(line.name) ? 3 : 2,
      shape: series.line_shape || 'linear',
    },
    marker: { size: 5 },
    connectgaps: false,
    /* Plotly draws in data order, so the emphasised series has to move to the
     * end of the array to sit on top. legendrank holds the legend to the order
     * the registry declared. */
    legendrank: i,
    /* Match the axis formatting, or the tooltip shows raw 35802000000. */
    yhoverformat: format,
    hovertemplate: '%{y}<extra>%{fullData.name}</extra>',
  }));

  const [emphasised, rest] = [
    built.filter((t) => EMPHASISED.has(t.name)),
    built.filter((t) => !EMPHASISED.has(t.name)),
  ];
  return [...rest, ...emphasised];
}

function traces(series) {
  if (isStacked(series)) return areaTraces(series);
  return [...bandTraces(series), ...lineTraces(series)];
}

const DAY_MS = 86400000;

/* An append-mode series starts life with a single observation. Left to
 * autorange, Plotly fits the axis to that one instant and labels it down to
 * fractions of a second; this keeps a minimum window either side. */
const MIN_SPAN_DAYS = 14;

function dateExtent(series) {
  const dates = series.lines.flatMap((line) => line.points.map((p) => p[0]));
  if (!dates.length) return null;
  return {
    first: dates.reduce((a, b) => (a < b ? a : b)),
    last: dates.reduce((a, b) => (a > b ? a : b)),
  };
}

function paddedRange(extent) {
  const first = Date.parse(extent.first);
  const last = Date.parse(extent.last);
  const spanDays = (last - first) / DAY_MS;
  if (spanDays >= MIN_SPAN_DAYS) return undefined; // autorange is fine

  const pad = ((MIN_SPAN_DAYS - spanDays) / 2) * DAY_MS;
  const iso = (ms) => new Date(ms).toISOString().slice(0, 10);
  return [iso(first - pad), iso(last + pad)];
}

/* Vertical labels occupy a narrow strip of x and a tall strip of y, so two
 * events a year apart collide no matter how they are anchored. Cycling the
 * label down the plot in thirds gives three neighbours somewhere to sit --
 * enough for the 2020-2023 cluster on a sixty-year axis. */
const LABEL_HEIGHTS = [0.98, 0.66, 0.34];

/* Event markers are clipped to the data's own date range -- a shock that
 * predates the series would otherwise stretch the axis to fit it. */
function eventDecorations(series, palette, extent) {
  if (!state.showEvents || !series.annotations || !extent) {
    return { shapes: [], annotations: [] };
  }
  const { first, last } = extent;

  const shapes = [];
  const annotations = [];
  state.events
    .filter((e) => e.date >= first && e.date <= last)
    .forEach((e, i) => {
      shapes.push({
        type: 'line',
        x0: e.date, x1: e.date,
        y0: 0, y1: 1, yref: 'paper',
        line: { color: palette.faint, width: 1, dash: 'dot' },
        /* Above a stacked area, or the fills bury it. */
        layer: isStacked(series) ? 'above' : 'below',
      });
      /* Vertical labels inside the plot. Horizontal ones collide as soon as
       * two events land in the same year, which is most of them. */
      annotations.push({
        x: e.date,
        y: LABEL_HEIGHTS[i % LABEL_HEIGHTS.length],
        yref: 'paper',
        yanchor: 'top',
        xanchor: 'center',
        xshift: -7,
        textangle: -90,
        text: e.label,
        showarrow: false,
        font: { size: 10, color: palette.faint },
      });
    });
  return { shapes, annotations };
}

function layoutFor(series, logScale) {
  const palette = theme();
  const y = series.y || {};
  const extent = dateExtent(series);
  const decorations = eventDecorations(series, palette, extent);

  return {
    margin: { l: 68, r: 18, t: 26, b: 40 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: palette.soft, size: 12 },
    hovermode: 'x unified',
    hoverlabel: { align: 'left' },
    showlegend: series.lines.length > 1,
    legend: { orientation: 'h', y: -0.14, x: 0, font: { size: 12 } },
    xaxis: {
      type: 'date',
      range: extent ? paddedRange(extent) : undefined,
      gridcolor: palette.rule,
      zeroline: false,
      linecolor: palette.rule,
    },
    yaxis: {
      type: logScale ? 'log' : 'linear',
      title: { text: y.title || '', font: { size: 12 } },
      tickformat: y.tickformat,
      /* One label per decade; Plotly's default log ticks label every minor
       * gridline and the axis turns into a wall of numbers. */
      dtick: logScale ? 1 : undefined,
      /* rangemode is meaningless on a log axis and Plotly warns about it. */
      rangemode: !logScale && y.rangemode ? y.rangemode : 'normal',
      gridcolor: palette.rule,
      zeroline: false,
      linecolor: palette.rule,
    },
    ...decorations,
  };
}

const PLOT_CONFIG = { displayModeBar: false, responsive: true };

function renderChart(chart) {
  Plotly.react(chart.node, traces(chart.series), layoutFor(chart.series, chart.log), PLOT_CONFIG);
}

/* ---- card assembly ----------------------------------------------------- */

function provenance(meta, series) {
  const row = el('div', 'provenance');

  const sources = meta.sources || [];
  sources.forEach((source, i) => {
    const span = el('span');
    if (i === 0) span.append(sources.length > 1 ? 'Sources: ' : 'Source: ');
    const link = el('a', null, source.name);
    link.href = source.url;
    link.rel = 'noopener';
    span.append(link);
    if (source.license) span.append(` (${source.license})`);
    row.append(span);
  });

  const updated = (series && series.updated) || meta.updated;
  if (updated) row.append(el('span', null, `Updated ${updated.slice(0, 10)}`));
  if (!meta.ok) {
    row.append(el('span', 'badge', series ? 'Last refresh failed — showing previous data' : 'Refresh failed'));
  }
  return row;
}

function buildCard(meta, series) {
  const card = el('section', 'card');
  card.id = meta.id;

  const head = el('div', 'card-head');
  head.append(el('h3', null, meta.title));

  const chart = { node: null, series, log: !!(meta.y && meta.y.log) };

  /* No log toggle on a stacked area: the stack's arithmetic only works on a
   * linear axis, and the picture it would produce is meaningless. */
  if (series && !isStacked(meta)) {
    /* Labelled with what the click does, not with the current state -- a button
     * reading "Log scale" on an already-logarithmic chart is a coin flip. */
    const label = () => (chart.log ? 'Switch to linear' : 'Switch to log');
    const button = el('button', 'scale-btn', label());
    button.addEventListener('click', () => {
      chart.log = !chart.log;
      button.textContent = label();
      renderChart(chart);
    });
    head.append(button);
  }
  card.append(head);

  if (meta.description) card.append(el('p', 'desc', meta.description));

  if (series && series.lines.length) {
    chart.node = el('div', 'plot');
    card.append(chart.node);
    chart.series = { ...meta, ...series };
    state.charts.push(chart);
  } else {
    card.append(el('p', 'empty', 'No data recorded yet.'));
  }

  if (meta.notes) card.append(el('p', 'notes', meta.notes));
  card.append(provenance(meta, series));
  return card;
}

/* ---- page -------------------------------------------------------------- */

async function fetchSeries(id, version) {
  try {
    const response = await fetch(`data/${id}.json?v=${encodeURIComponent(version)}`);
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  }
}

async function main() {
  const manifest = await (await fetch(`data/manifest.json?t=${Date.now()}`)).json();
  state.events = manifest.events || [];

  const charts = document.getElementById('charts');
  charts.innerHTML = '';
  const nav = document.getElementById('nav');

  for (const group of manifest.groups) {
    const link = el('a', null, group.title);
    link.href = `#group-${group.id}`;
    nav.append(link);

    const section = el('section', 'group');
    section.id = `group-${group.id}`;
    section.append(el('h2', null, group.title));
    if (group.blurb) section.append(el('p', 'blurb', group.blurb));

    const cards = await Promise.all(
      group.series.map(async (meta) => buildCard(meta, await fetchSeries(meta.id, manifest.generated)))
    );
    cards.forEach((card) => section.append(card));
    charts.append(section);
  }

  state.charts.forEach(renderChart);

  document.getElementById('generated').textContent =
    `Page rebuilt ${manifest.generated.replace('T', ' ').replace('Z', ' UTC')}.`;

  const toggle = document.getElementById('events-toggle');
  toggle.addEventListener('change', () => {
    state.showEvents = toggle.checked;
    state.charts.forEach(renderChart);
  });

  /* Re-render on theme flips so axis and grid colours follow the OS. */
  window.matchMedia('(prefers-color-scheme: dark)')
    .addEventListener('change', () => state.charts.forEach(renderChart));
}

main().catch((error) => {
  document.getElementById('charts').innerHTML =
    `<p class="empty">Could not load chart data: ${error}</p>`;
});
