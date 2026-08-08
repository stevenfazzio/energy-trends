/* Renders one Plotly chart per series listed in data/manifest.json.
 *
 * Everything on the page is driven by the manifest, so adding a chart is a
 * change to the Python registry alone -- no edits here.
 *
 * Each card carries its own controls: scale for every chart, view (stacked /
 * 100% / lines) for any series the registry declares a decomposition of a
 * whole, and a moving average for the monthly ones. Chart state -- including
 * which series the reader has clicked off in the legend -- survives every one
 * of those, which is the whole reason rendering goes through one function. */

const PALETTE = [
  '#2f6fdd', '#e2622a', '#189f6d', '#a259d9',
  '#d4a017', '#c94f7c', '#4aa3c7', '#7a8794',
];

/* A fuel or a region keeps its colour wherever it appears, so the generation,
 * capacity and emissions charts can be read against each other. Conventional
 * where a convention exists: coal grey, gas orange, solar yellow, hydro blue.
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
  /* regions and blocs */
  'China': '#e2622a',
  'United States': '#2f6fdd',
  'European Union': '#189f6d',
  'India': '#a259d9',
  /* continents -- all six need to be distinct from each other, which the
   * generic palette did not manage: Africa and South America both landed on
   * the same gold. */
  'Asia': '#2f6fdd',
  'North America': '#e2622a',
  'Europe': '#189f6d',
  'Africa': '#d4a017',
  'South America': '#c94f7c',
  'Oceania': '#4aa3c7',
  /* CO2 sources */
  'Cement': '#a0a0a8',
  'Flaring': '#c94f7c',
  'Other industry': '#7a8794',
};

/* Series whose colour has to follow the theme rather than sit at a fixed hex.
 * These are the lines a chart exists to show, so they take the page's own ink
 * colour -- near-black on light, near-white on dark -- which no fixed value
 * can do, and they are drawn heavier and last so they stay readable where the
 * others cross them. */
const THEME_COLOURS = { 'World': '--ink', 'Total': '--ink' };
const EMPHASISED = new Set(['World', 'Total']);

/* Charts with few points get visible markers; dense ones would be a smear. */
const MARKER_THRESHOLD = 60;

const VIEW_LABELS = [['stacked', 'Stacked'], ['percent', '100%'], ['lines', 'Lines']];

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

/* Bands are drawn in the line's own colour at low opacity. */
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

const isStacked = (chart) => chart.view === 'stacked' || chart.view === 'percent';

/* ---- data shaping ------------------------------------------------------ */

/* Trailing moving average. A window containing a gap produces no point rather
 * than an average over fewer months, and the first months of a series produce
 * nothing at all -- an average needs its whole window to be the thing it
 * claims to be. */
function movingAverage(points, window) {
  const out = [];
  for (let i = window - 1; i < points.length; i++) {
    let sum = 0;
    let complete = true;
    for (let j = i - window + 1; j <= i; j++) {
      const value = points[j][1];
      if (value == null) { complete = false; break; }
      sum += value;
    }
    if (complete) out.push([points[i][0], sum / window]);
  }
  return out;
}

function bandMovingAverage(band, window) {
  const low = movingAverage(band.map((p) => [p[0], p[1]]), window);
  const high = movingAverage(band.map((p) => [p[0], p[2]]), window);
  return low.map((p, i) => [p[0], p[1], high[i] ? high[i][1] : null]);
}

/* The sum across every series, for the lines view of a decomposition. Only
 * dates carried by all of them contribute: summing a subset would draw a total
 * that dips wherever one series happens to start late. */
function totalLine(lines) {
  if (!lines.length) return null;
  const maps = lines.map((line) => new Map(line.points.map((p) => [p[0], p[1]])));
  const points = [];
  for (const date of maps[0].keys()) {
    let sum = 0;
    let complete = true;
    for (const map of maps) {
      const value = map.get(date);
      if (value == null) { complete = false; break; }
      sum += value;
    }
    if (complete) points.push([date, sum]);
  }
  return points.length ? { name: 'Total', points } : null;
}

function linesFor(chart) {
  const window = chart.meta.smooth_months || 0;
  let lines = chart.series.lines.map((line) => {
    if (!chart.smooth || !window) return line;
    return {
      name: line.name,
      points: movingAverage(line.points, window),
      band: line.band ? bandMovingAverage(line.band, window) : undefined,
    };
  });

  if (chart.meta.chart === 'area' && chart.view === 'lines') {
    const total = totalLine(lines);
    if (total) lines = [total, ...lines];
  }
  return lines;
}

/* ---- chart construction ------------------------------------------------ */

function visibilityOf(chart, name) {
  const recorded = chart.visibility[name];
  return recorded === undefined ? true : recorded;
}

function areaTraces(chart, lines) {
  return lines.map((line, i) => {
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
      groupnorm: chart.view === 'percent' ? 'fraction' : undefined,
      line: { width: 0.5, color: colour },
      fillcolor: translucent(colour, 0.85),
      visible: visibilityOf(chart, line.name),
      yhoverformat: axisFor(chart).tickformat,
      hovertemplate: '%{y}<extra>%{fullData.name}</extra>',
    };
  });
}

/* Two invisible traces per band: the lower bound, then the upper filling down
 * to it. They must precede the line traces so the central estimate draws on
 * top of its own shading. */
function bandTraces(chart, lines) {
  const out = [];
  lines.forEach((line, i) => {
    if (!line.band || !line.band.length) return;
    if (visibilityOf(chart, line.name) !== true) return;
    const colour = colourFor(line.name, i);
    const x = line.band.map((p) => p[0]);
    const common = {
      type: 'scatter',
      mode: 'lines',
      line: { width: 0 },
      hoverinfo: 'skip',
      showlegend: false,
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

function lineTraces(chart, lines) {
  const dense = lines.some((line) => line.points.length > MARKER_THRESHOLD);
  const format = axisFor(chart).tickformat;
  const built = lines.map((line, i) => ({
    type: 'scatter',
    mode: dense ? 'lines' : 'lines+markers',
    name: line.name,
    x: line.points.map((p) => p[0]),
    y: line.points.map((p) => p[1]),
    line: {
      color: colourFor(line.name, i),
      width: EMPHASISED.has(line.name) ? 3 : 2,
      shape: chart.meta.line_shape || 'linear',
    },
    marker: { size: 5 },
    connectgaps: false,
    visible: visibilityOf(chart, line.name),
    /* Plotly draws in data order, so the emphasised series has to move to the
     * end of the array to sit on top. legendrank holds the legend to the order
     * the registry declared. */
    legendrank: i,
    /* Match the axis formatting, or the tooltip shows raw 35802000000. */
    yhoverformat: format,
    hovertemplate: '%{y}<extra>%{fullData.name}</extra>',
  }));

  const emphasised = built.filter((t) => EMPHASISED.has(t.name));
  const rest = built.filter((t) => !EMPHASISED.has(t.name));
  return [...rest, ...emphasised];
}

function traces(chart) {
  const lines = linesFor(chart);
  if (isStacked(chart)) return areaTraces(chart, lines);
  return [...bandTraces(chart, lines), ...lineTraces(chart, lines)];
}

/* A 100% stack is a share of a total whatever the underlying series measures,
 * so it overrides the registry's axis. Everything else keeps it. */
function axisFor(chart) {
  const y = chart.meta.y || {};
  if (chart.view === 'percent') {
    return { title: 'Share of total', tickformat: '.0%', rangemode: 'tozero' };
  }
  return y;
}

const DAY_MS = 86400000;
const MIN_SPAN_DAYS = 14;

function dateExtent(chart) {
  const dates = linesFor(chart).flatMap((line) => line.points.map((p) => p[0]));
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
 * label down the plot in thirds gives neighbours somewhere to sit. */
const LABEL_HEIGHTS = [0.98, 0.66, 0.34];

/* Event markers are clipped to the data's own date range -- a shock that
 * predates the series would otherwise stretch the axis to fit it. */
function eventDecorations(chart, palette, extent) {
  if (!state.showEvents || !chart.meta.annotations || !extent) {
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
        layer: isStacked(chart) ? 'above' : 'below',
      });
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

function layoutFor(chart) {
  const palette = theme();
  const y = axisFor(chart);
  const extent = dateExtent(chart);
  const decorations = eventDecorations(chart, palette, extent);
  const logScale = chart.log && !isStacked(chart);

  return {
    margin: { l: 68, r: 18, t: 26, b: 40 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: palette.soft, size: 12 },
    hovermode: 'x unified',
    hoverlabel: { align: 'left' },
    showlegend: chart.series.lines.length > 1,
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

/* Legend clicks live in Plotly's copy of the data, so they have to be read
 * back out before anything re-renders or they are lost -- which is what used
 * to happen on every scale toggle. */
function captureVisibility(chart) {
  if (!chart.node || !chart.node.data) return;
  chart.node.data.forEach((trace) => {
    if (trace.name && trace.showlegend !== false) {
      chart.visibility[trace.name] = trace.visible === undefined ? true : trace.visible;
    }
  });
}

function renderChart(chart) {
  if (!chart.node) return;
  captureVisibility(chart);
  Plotly.react(chart.node, traces(chart), layoutFor(chart), PLOT_CONFIG);
  if (!chart.listening) {
    chart.node.on('plotly_restyle', () => captureVisibility(chart));
    chart.listening = true;
  }
}

/* ---- controls ---------------------------------------------------------- */

function segmented(options, current, onChange) {
  const group = el('div', 'seg');
  options.forEach(([value, label]) => {
    const button = el('button', value === current ? 'on' : null, label);
    button.addEventListener('click', () => { if (value !== current) onChange(value); });
    group.append(button);
  });
  return group;
}

function renderControls(chart) {
  const bar = chart.controls;
  bar.innerHTML = '';
  if (!chart.node) return;

  if (chart.meta.chart === 'area') {
    bar.append(segmented(VIEW_LABELS, chart.view, (view) => {
      chart.view = view;
      /* A decomposition read as lines is nearly always a set of quantities
       * spanning orders of magnitude -- that is why it was a stack. Log is the
       * useful default there, until the reader says otherwise. */
      if (view === 'lines' && !chart.scaleTouched) chart.log = true;
      renderControls(chart);
      renderChart(chart);
    }));
  }

  if (!isStacked(chart)) {
    bar.append(segmented([['linear', 'Linear'], ['log', 'Log']], chart.log ? 'log' : 'linear', (scale) => {
      chart.log = scale === 'log';
      chart.scaleTouched = true;
      renderControls(chart);
      renderChart(chart);
    }));
  }

  const months = chart.meta.smooth_months || 0;
  if (months) {
    bar.append(segmented(
      [['raw', 'Monthly'], ['smooth', `${months}-mo avg`]],
      chart.smooth ? 'smooth' : 'raw',
      (mode) => {
        chart.smooth = mode === 'smooth';
        renderControls(chart);
        renderChart(chart);
      },
    ));
  }
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

  const chart = {
    node: null,
    meta,
    series,
    view: meta.chart === 'area' ? 'stacked' : 'lines',
    log: !!(meta.y && meta.y.log),
    scaleTouched: false,
    smooth: !!(meta.smooth_months && meta.smooth_default),
    visibility: {},
    listening: false,
  };

  card.append(el('h3', null, meta.title));
  if (meta.description) card.append(el('p', 'desc', meta.description));

  chart.controls = el('div', 'chart-controls');
  card.append(chart.controls);

  if (series && series.lines.length) {
    chart.node = el('div', 'plot');
    card.append(chart.node);
    state.charts.push(chart);
  } else {
    card.append(el('p', 'empty', 'No data recorded yet.'));
  }
  renderControls(chart);

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

  /* Re-render on theme flips so axis, grid and ink-coloured lines follow. */
  window.matchMedia('(prefers-color-scheme: dark)')
    .addEventListener('change', () => state.charts.forEach(renderChart));
}

main().catch((error) => {
  document.getElementById('charts').innerHTML =
    `<p class="empty">Could not load chart data: ${error}</p>`;
});
