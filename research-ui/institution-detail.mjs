import {dateOnly, dateText, finite, element as el, link} from './core.mjs';

/** Preserve explicit gaps and withhold ambiguous duplicate reporting periods. */
export function gnpaHistory(history) {
  const periods = new Map();
  for (const row of Array.isArray(history) ? history : []) {
    const date = dateOnly(row?.period_end);
    if (!date) continue;
    const metric = row?.metrics?.gnpa_pct;
    const value = metric?.status === 'observed' && metric.unit === 'percent' ? finite(metric.value) : null;
    const valid = value !== null && value >= 0 && value <= 100 ? value : null;
    periods.set(date, periods.has(date) ? {date, value: null, duplicate: true} : {date, value: valid});
  }
  return [...periods.values()].sort((a, b) => a.date.localeCompare(b.date));
}

function svgElement(tag, attributes = {}, text) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, String(value));
  if (text !== undefined) node.textContent = text;
  return node;
}

export function gnpaChart(data) {
  const points = gnpaHistory(data.history), observed = points.filter(point => point.value !== null);
  if (!observed.length) return el('p', 'No comparable GNPA observations are available for a chart. The disclosure table below retains the supplied record.');
  const figure = el('figure', undefined, 'rw-chart');
  const svg = svgElement('svg', {viewBox: '0 0 460 150', role: 'img'});
  svg.append(svgElement('title', {}, 'Disclosed gross non-performing assets as a percentage. ' + points.map(point => `${point.date}: ${point.duplicate ? 'duplicate reporting period, withheld' : point.value === null ? 'not disclosed' : point.value + '%'}`).join('; ')));
  const maximum = Math.max(...observed.map(point => point.value), .1) * 1.15;
  const start = Date.parse(points[0].date), end = Date.parse(points.at(-1).date);
  const x = point => start === end ? 242.5 : 38 + (Date.parse(point.date) - start) / (end - start) * 409;
  const y = point => 124 - point.value / maximum * 102;
  for (const level of [0, maximum / 2, maximum]) {
    const py = 124 - level / maximum * 102;
    svg.append(svgElement('line', {x1: 38, x2: 450, y1: py, y2: py, stroke: 'var(--research-line)'}));
    svg.append(svgElement('text', {x: 30, y: py + 4, 'text-anchor': 'end', fill: 'var(--research-muted)', 'font-size': 10}, level.toFixed(1) + '%'));
  }
  let path = '', connected = false;
  for (const point of points) {
    if (point.value === null) { connected = false; continue; }
    path += `${connected ? 'L' : 'M'}${x(point).toFixed(2)},${y(point).toFixed(2)} `;
    connected = true;
  }
  svg.append(svgElement('path', {d: path.trim(), fill: 'none', stroke: 'var(--research-accent)', 'stroke-width': 2}));
  for (const point of observed) {
    const dot = svgElement('circle', {cx: x(point), cy: y(point), r: 3, fill: 'var(--research-accent)'});
    dot.append(svgElement('title', {}, `${point.date}: ${point.value}%`));
    svg.append(dot);
  }
  const caption = el('figcaption');
  caption.append(el('span', dateText(points[0].date)), el('span', 'Gross NPAs / advances (%)'), el('span', dateText(points.at(-1).date)));
  figure.append(svg, caption, el('p', 'Dots show disclosed observations. Lines stop at missing or duplicate reporting periods; gaps are not filled.', 'rw-caption'));
  return figure;
}

export function provisionalSection(update) {
  if (!update) return null;
  const section = el('section', undefined, 'rw-provisional');
  section.append(el('h3', update.title), el('p', update.clock, 'rw-clock'), el('p', update.note, 'rw-caption'));
  const metrics = el('dl', undefined, 'rw-metrics');
  for (const metric of update.metrics) {
    const item = el('div');
    item.append(el('dt', metric.label), el('dd', metric.value, metric.value === 'Not disclosed' ? 'rw-missing' : undefined));
    if (metric.basis) item.append(el('dd', metric.basis, 'rw-caption'));
    metrics.append(item);
  }
  section.append(metrics);
  for (const url of update.sources) {
    const paragraph = el('p'), anchor = link(`Read the provisional disclosure: ${new URL(url).hostname}`, url);
    anchor.target = '_blank'; anchor.rel = 'noopener noreferrer'; paragraph.append(anchor); section.append(paragraph);
  }
  return section;
}
