import {API, reviewModel} from '../banking/model.mjs';
import {bankCoverage, readJSON, visibleRefresh, sourceUrl} from './core.mjs';
import {chartCard, dashboard, stats, selectControl, el, number, finite, dateValue, COLORS} from './analytics-charts.js';

const METRICS = [['gnpa_pct', 'Gross NPA'], ['nnpa_pct', 'Net NPA'], ['crar_pct', 'Capital ratio'], ['casa_pct', 'CASA'], ['lcr_pct', 'LCR'], ['top20_depositors_pct', 'Top 20 deposits']];
const shortName = data => data.name.replace(/ Small Finance Bank/g, ' SFB').replace(/ Co-operative Bank/g, ' Co-op').replace(/ Ltd/g, '');
export function metric(record, key, unit = 'percent') {
  const value = record?.metrics?.[key];
  return value?.status === 'observed' && value.unit === unit && finite(value.value) ? value.value : null;
}
export function institutionModel(data, slug) {
  reviewModel(data);
  if (data.slug !== slug || dateValue(data.period_end) === null || !Array.isArray(data.history) || data.history.length > 300 || !data.sources?.some(sourceUrl)) throw new Error('The filing identity or reporting clock could not be verified.');
  const dates = new Set();
  for (const row of data.history) {
    if (dateValue(row.period_end) === null || row.period_end > data.period_end || dates.has(row.period_end)) throw new Error('Ambiguous reporting history.');
    dates.add(row.period_end);
  }
  return data;
}
export function bankHistory(data, key) {
  if (!data) return [];
  const rows = [...data.history.filter(row => row.period_end !== data.period_end), data].sort((a, b) => a.period_end.localeCompare(b.period_end));
  return rows.map(row => ({x: dateValue(row.period_end), y: metric(row, key), label: row.period_end, note: `${data.name} · ${row.metrics?.[key]?.basis || 'Reported ratio'} · available ${row.available_at || 'time not supplied'}`}));
}
export function movementRows(data) {
  const m = data?.npa_movement;
  if (m?.status !== 'reconciled' || m.amount_unit !== 'INR_crore' || dateValue(m.period_start) === null || dateValue(m.period_end) === null || m.period_start >= m.period_end || m.period_end !== data.period_end) return [];
  const values = [m.opening_gnpa, m.additions, ...['upgrades', 'cash_recoveries', 'write_offs', 'other_reductions'].map(key => m.reductions?.[key]), m.closing_gnpa];
  if (!values.every(v => finite(v) && v >= 0) || !finite(m.rounding_tolerance) || m.rounding_tolerance < 0 || m.rounding_tolerance > 1) return [];
  const [opening, additions, upgrades, recoveries, writeoffs, other, closing] = values;
  if (Math.abs(opening + additions - upgrades - recoveries - writeoffs - other - closing) > m.rounding_tolerance + 1e-8) return [];
  let level = opening;
  const rows = [{label: 'Opening GNPA', value: opening, start: 0, end: opening, color: COLORS[0]}];
  for (const [label, delta] of [['New additions', additions], ['Upgrades', -upgrades], ['Cash recoveries', -recoveries], ['Write-offs', -writeoffs], ['Other reductions', -other]]) {
    rows.push({label, value: delta, start: level, end: level + delta, color: delta > 0 ? COLORS[4] : COLORS[2]}); level += delta;
  }
  rows.push({label: 'Closing GNPA', value: closing, start: 0, end: closing, color: COLORS[0]});
  return rows.map(row => ({...row, note: `${data.name} · ${m.period_start} to ${m.period_end}`}));
}
export function institutionSpecs(records, {selected, period, sector = 'all', change = 'year', movement}, onSelect) {
  const data = records.get(selected), peers = [...records.values()].filter(row => ['observed', 'stale'].includes(row.status) && row.period_end === period && (sector === 'all' || row.sector === sector));
  const source = record => ({label: `${record.name} · reporting ${record.period_end} · ${record.status}`, url: `${API}/institutions/${encodeURIComponent(record.slug)}?include_history=true`});
  const historySources = data ? [source(data), ...data.sources.filter(sourceUrl).map(url => ({label: 'Original filing · ' + new URL(url).hostname, url}))] : [];
  const peerSources = peers.map(source);
  const base = (id, index, title, description, unit, sources, note) => ({id, number: String(index).padStart(2, '0'), title, description, unit, sources, note});
  const title = data ? shortName(data) : 'Selected institution';
  const m = records.get(movement);
  const peerPoints = peers.flatMap(row => {
    const x = metric(row, 'gnpa_pct'), y = metric(row, 'crar_pct');
    return x === null || y === null ? [] : [{x, y, label: shortName(row), id: row.slug, note: `${row.name} · ${row.period_end} · ${row.status}`}];
  });
  return [
    {...base('institution-risk-map', 1, 'Asset quality against capital', `Compare disclosed ratios from the same reporting date: ${period || 'unavailable'}. Select a point to inspect that institution.`, 'Capital adequacy · %', peerSources, 'Each dot is a disclosed institution, not an estimated default probability. Same-date comparisons still have sector and accounting differences. The public corpus is a selected sample, not the banking system.'), kind: 'scatter', xType: 'linear', xLabel: 'Gross NPA / gross advances · %', series: [{name: 'Disclosed institutions', points: peerPoints}], zero: true, onSelect},
    {...base('institution-asset-quality', 2, `${title}: asset quality`, 'Gross and net non-performing asset ratios across reported periods.', '%', historySources, 'GNPA and NNPA have different denominators. Their difference is not provision coverage. Missing observations break the line; reporting dates are not filing-availability dates.'), xType: 'date', maxGapDays: 400, series: [{name: 'Gross NPA', points: bankHistory(data, 'gnpa_pct')}, {name: 'Net NPA', points: bankHistory(data, 'nnpa_pct')}], zero: true},
    {...base('institution-capital', 3, `${title}: capital structure`, 'Total capital adequacy, Tier 1 and CET1 where explicitly disclosed.', '%', historySources, 'These capital ratios overlap and must not be added together. No common regulatory threshold is imposed across different institution classes. Gaps remain visible.'), xType: 'date', maxGapDays: 400, series: [['crar_pct', 'Total capital'], ['tier1_pct', 'Tier 1'], ['cet1_pct', 'CET1']].map(([key, name]) => ({name, points: bankHistory(data, key)}))},
    {...base('institution-npa-change', 4, `${change === 'year' ? 'Annual' : 'Quarterly'} change in reported GNPA`, `Source-qualified changes for the selected ${period || 'unavailable'} cohort.`, 'percentage points', peerSources, 'Only changes explicitly admitted by the source API are shown. Negative means a lower reported ratio; recoveries, write-offs and denominator growth are separate explanations. Exact comparison periods appear in the data table.'), kind: 'bar', rows: peers.map(row => {
      const delta = row.changes?.[change]; const value = delta?.status === 'observed' && delta.unit === 'percentage_points' && delta.to_period === row.period_end && dateValue(delta.from_period) !== null && delta.from_period < delta.to_period && finite(delta.changes?.gnpa_pct) ? delta.changes.gnpa_pct : null;
      return {label: shortName(row), value, note: `${delta?.from_period || 'Unavailable'} → ${row.period_end}`};
    }).sort((a, b) => (b.value ?? -Infinity) - (a.value ?? -Infinity))},
    {...base('institution-npa-bridge', 5, `${m ? shortName(m) : 'Filing'}: the NPA movement bridge`, m ? `Reconciled filing components · ${m.npa_movement.period_start} to ${m.npa_movement.period_end}.` : 'A complete opening-to-closing movement statement is required.', 'INR crore', m ? [source(m), ...m.sources.filter(sourceUrl).map(url => ({label: 'Original movement statement', url}))] : [], 'Opening GNPA + additions − upgrades − cash recoveries − write-offs − other reductions = closing GNPA, within reported rounding tolerance. Reconciliation is arithmetic, not an audit. This independently selected filing is separate from the peer-period filter.'), kind: 'waterfall', rows: movementRows(m), empty: 'No fully reconciled NPA movement statement is available. Partial components are not turned into a balancing figure.'},
    {...base('institution-funding-profile', 6, `${title}: funding disclosures`, 'Liquidity coverage, low-cost deposits and depositor concentration.', '%', historySources, 'CASA, LCR and top-20 depositor concentration have different denominators and meanings. They are not additive. Hover or open the table for the reported basis, including period-average LCR when applicable.'), kind: 'bar', rows: [['casa_pct', 'CASA ratio'], ['lcr_pct', 'Liquidity coverage'], ['top20_depositors_pct', 'Top 20 depositors']].map(([key, label]) => ({label, value: metric(data, key), note: `${data?.period_end || 'Date unavailable'} · ${data?.metrics?.[key]?.basis || 'See original disclosure'}`}))},
    {...base('institution-deposit-base', 7, 'The disclosed deposit base', `Balance-sheet scale across the ${period || 'unavailable'} cohort.`, 'INR crore', peerSources, 'Amounts are compared only in the same currency and unit, at the selected reporting date. Deposit size alone does not measure deposit stability, liquidity coverage or institution safety.'), kind: 'bar', rows: peers.map(row => ({label: shortName(row), value: metric(row, 'deposits', 'INR_crore'), note: `${row.period_end} · ${row.status}`})).sort((a, b) => (b.value ?? -Infinity) - (a.value ?? -Infinity))},
    {...base('institution-disclosure-map', 8, 'Which disclosures support the comparison?', 'A coverage matrix makes missing inputs visible before drawing conclusions.', '1 = disclosed; — = missing', peerSources, 'A filled cell means the metric is explicitly observed in the accepted record; it is not a positive risk assessment. A dash means unavailable, not zero. Annual and quarterly records are never silently pooled.'), kind: 'matrix', columns: METRICS.map(([, label]) => label), domain: [0, 1], matrix: peers.map(row => ({label: shortName(row), values: METRICS.map(([key]) => metric(row, key) === null ? null : 1), notes: METRICS.map(([key]) => `${row.period_end} · ${row.metrics?.[key]?.basis || row.metrics?.[key]?.status || 'Not disclosed'}`)}))},
  ];
}

export function mountInstitutionAnalytics(target) {
  const view = dashboard(target, {eyebrow: 'LIQUILENS / INSTITUTION OBSERVATORY', title: 'Read the balance sheet. See the pressure.', description: 'Eight views connect asset quality, capital, funding and the disclosures behind them. Compare like reporting dates, inspect an institution’s history, and reconcile a complete NPA movement statement.'});
  let records = new Map(), coverage = null, selected = 'au-sfb', period = '', sector = 'all', change = 'year', movement = 'cosmos-ucb', request = null, disposed = false;
  const render = () => {
    view.grid.replaceChildren(...institutionSpecs(records, {selected, period, sector, change, movement}, id => {selected = id; controls(); render();}).map(chartCard));
    const data = records.get(selected), value = key => metric(data, key);
    stats(view.stats, [['Institution', data ? shortName(data) : 'Loading', data?.period_end || 'Awaiting source'], ['Gross NPA', value('gnpa_pct') === null ? 'Not disclosed' : number(value('gnpa_pct')) + '%', 'Gross NPAs / gross advances'], ['Capital adequacy', value('crar_pct') === null ? 'Not disclosed' : number(value('crar_pct')) + '%', 'Reported CRAR'], ['Evidence loaded', String(records.size), `${coverage?.rows.length || 0} dossiers in the coverage register`]]);
  };
  const controls = () => {
    const periods = [...new Set([...records.values()].filter(r => ['observed', 'stale'].includes(r.status)).map(r => r.period_end))].sort().reverse();
    if (!periods.includes(period)) period = periods[0] || '';
    const movements = [...records.values()].filter(r => movementRows(r).length);
    if (!movements.some(r => r.slug === movement)) movement = movements[0]?.slug || '';
    const choices = [...records.values()].sort((a, b) => a.name.localeCompare(b.name)).map(r => [r.slug, r.name]);
    view.controls.replaceChildren(
      selectControl('Institution history', choices.length ? choices : [['au-sfb', 'Loading institutions…']], selected, id => {selected = id; render();}),
      selectControl('Peer reporting date', periods.map(date => [date, date]), period, value => {period = value; render();}),
      selectControl('Peer group', [['all', 'All reporting classes'], ['sfb', 'Small finance banks'], ['bank', 'Commercial banks'], ['ucb', 'Co-operative banks']], sector, value => {sector = value; render();}),
      selectControl('GNPA change', [['year', 'Year over year'], ['quarter', 'Quarter over quarter']], change, value => {change = value; render();}),
      selectControl('Movement filing', movements.map(r => [r.slug, shortName(r)]), movement, value => {movement = value; render();}));
    const refresh = el('button', 'Refresh filings'); refresh.type = 'button'; refresh.disabled = Boolean(request); refresh.addEventListener('click', () => void load()); view.controls.append(refresh);
  };
  async function load() {
    if (request) return; const controller = new AbortController(); request = controller;
    const timer = setTimeout(() => controller.abort(), 45000); view.status.textContent = 'Reading current filing evidence and histories…';
    try {
      const nextCoverage = bankCoverage(await readJSON(`${API}/coverage`, {signal: controller.signal}));
      const rows = nextCoverage.rows.filter(r => ['observed', 'stale'].includes(r.status)), next = new Map();
      for (let i = 0; i < rows.length; i += 2) await Promise.all(rows.slice(i, i + 2).map(async row => {
        try {next.set(row.slug, institutionModel(await readJSON(`${API}/institutions/${encodeURIComponent(row.slug)}?include_history=true`, {signal: controller.signal}), row.slug));} catch { /* Failed records do not enter cross-institution comparisons. */ }
      }));
      if (disposed) return; records = next; coverage = nextCoverage;
      if (!records.has(selected)) selected = records.keys().next().value || '';
      view.status.textContent = `${records.size} / ${rows.length} current or stale dossiers loaded. Coverage ${nextCoverage.asOf}. Historical cases remain in the institution explorer below.`;
    } catch {
      if (!disposed) {records.clear(); view.status.textContent = 'Filing data could not be verified. Retry to load the institution charts.';}
    } finally {clearTimeout(timer); request = null; if (!disposed) {controls(); render();}}
  }
  controls(); render(); const stop = visibleRefresh(load);
  return () => {disposed = true; stop(); request?.abort();};
}
if (typeof customElements !== 'undefined' && !customElements.get('institution-analytics')) customElements.define('institution-analytics', class extends HTMLElement {
  connectedCallback() {this.stop = mountInstitutionAnalytics(this);}
  disconnectedCallback() {this.stop?.();}
});
