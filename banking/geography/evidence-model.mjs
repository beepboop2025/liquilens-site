import {readBounded} from '../model.mjs';

export const GEO_API = 'https://api.liquilens.in/api/experimental/v1/banking/lending-geography/';
export const DEFAULT_PLACE = 'in-dist-rajasthan-jaipur';
const ID = /^in-(?:dist|state|dccb|stcb)-[a-z0-9]+(?:-[a-z0-9]+)*$/;
const unavailable = 'Not available';
const number = value => typeof value === 'number' && Number.isFinite(value);
const record = value => value && typeof value === 'object' && !Array.isArray(value);
const text = value => typeof value === 'string' && value.length <= 2000 ? value : '';
const contractError = () => new Error('The geography evidence contract could not be verified. Please retry later.');
export const formatNumber = value => number(value) ? new Intl.NumberFormat('en-IN', {maximumFractionDigits: 3}).format(value) : unavailable;
export function validPlace(id) { return typeof id === 'string' && id.length <= 120 && ID.test(id); }
export function safeSource(value) {
  try { const url = new URL(value); return url.protocol === 'https:' && !url.username && !url.password ? url.href : null; } catch { return null; }
}
function month(value) {return typeof value === 'string' && /^\d{4}-(?:0[1-9]|1[0-2])$/.test(value);}
function day(value) {return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;}
function observationDate(value) {return day(value) || (typeof value === 'string' && /^\d{4}-W(?:0[1-9]|[1-4]\d|5[0-3])$/.test(value));}
function nullableNumber(value) {if (value != null && !number(value)) throw contractError(); return value ?? null;}
function rainfallNumber(value) {const result = nullableNumber(value); if (result !== null && result < 0) throw contractError(); return result;}
function valueWithUnit(value, unit) {return number(value) ? `${formatNumber(value)}${unit}` : unavailable;}

export function recentMonths(recent) {
  if (recent == null) return [];
  if (!record(recent) || !month(recent.from) || !Array.isArray(recent.mm) || recent.mm.length > 120 ||
      !Array.isArray(recent.normal_mm) || recent.mm.length !== recent.normal_mm.length ||
      !Array.isArray(recent.departure_pct) || recent.mm.length !== recent.departure_pct.length) throw contractError();
  const low = new Set(Array.isArray(recent.low_normal_months) ? recent.low_normal_months : []);
  return recent.mm.map((value, i) => {
    const date = new Date(`${recent.from}-01T00:00:00Z`);
    date.setUTCMonth(date.getUTCMonth() + i);
    const label = date.toISOString().slice(0, 7);
    return {month: label, mm: rainfallNumber(value), normal: rainfallNumber(recent.normal_mm[i]),
      departure: nullableNumber(recent.departure_pct[i]), lowNormal: low.has(label)};
  });
}

function districtModel(district, sources) {
  if (!record(district) || !validPlace(district.id) || !district.id.startsWith('in-dist-') || !text(district.name) || !text(district.state)) throw contractError();
  const seasonal = [['jjas', 'Monsoon rainfall', 'June–September'], ['ond', 'Post-monsoon rainfall', 'October–December'],
    ['fiscal_year', 'Full fiscal-year rainfall', 'April–March'], ['fiscal_year_to_date', 'Fiscal year to date', 'April onward']];
  const rainfall = seasonal.map(([key, label, period]) => {
    const row = district[key];
    if (row == null) return {label, value: unavailable, detail: 'Observation not supplied', date: 'Date unavailable'};
    if (!record(row) || !(Number.isInteger(row.year) && row.year >= 1900 && row.year <= 2200 || typeof row.year === 'string' && /^\d{4}-\d{2}$/.test(row.year))) throw contractError();
    const mm = rainfallNumber(row.mm), normal = rainfallNumber(row.normal_mm), departure = nullableNumber(row.departure_pct);
    if (row.through != null && !month(row.through)) throw contractError();
    return {label, value: valueWithUnit(mm, ' mm'), date: `${row.year} · ${period}${row.through ? ` · through ${row.through}` : ''}`,
      detail: `Normal ${valueWithUnit(normal, ' mm')} · departure ${valueWithUnit(departure, '%')}${number(departure) && text(row.category) ? ` · ${row.category}` : ''}`};
  });
  const signals = [['vegetation_health', 'Vegetation health', 'vhi', ' / 100'], ['soil_moisture', 'Soil moisture', 'sm_m3_m3', ' m³/m³']].map(([key, label, field, unit]) => {
    const signal = district[key], source = sources[key];
    if (signal == null) return {label, value: unavailable, date: 'Date unavailable', detail: 'No observation supplied for this district.'};
    if (!record(signal) || !observationDate(signal.as_of) || !record(source) || source.as_of !== signal.as_of || !text(source.product) || !text(source.credit)) throw contractError();
    const value = nullableNumber(signal[field]);
    if (value !== null && (value < 0 || value > (key === 'vegetation_health' ? 100 : 1))) throw contractError();
    return {label, value: valueWithUnit(value, unit), date: `${signal.as_of} · historical observation`, detail: `${source.product} · ${source.credit}`};
  });
  const drought = district.declared_drought;
  if (drought != null && (!record(drought) || !Array.isArray(drought.years) || drought.years.some(year => typeof year !== 'string' || !/^\d{4}-\d{2}$/.test(year)))) throw contractError();
  return {id: district.id, name: district.name, state: district.state, rainfall, signals,
    months: recentMonths(district.recent_months), droughtYears: drought?.years ?? null,
    droughtSource: text(drought?.source), basis: text(district.link?.basis).replaceAll('_', ' ')};
}

export function evidenceModel(data, expectedId, expectedOffset = 0) {
  if (!record(data) || data.schema !== 'liquilens.lending-geography.v1' || data.scope !== 'research' ||
      data.score_authority !== false || data.scoring_eligible !== false || data.training_corpus_changed !== false ||
      !validPlace(data.id) || data.id !== expectedId || !day(data.as_of) ||
      !['observed', 'mapped', 'unmapped', 'not_covered', 'unavailable'].includes(data.status)) throw contractError();
  const base = {id: data.id, name: text(data.name) || text(data.state) || data.id, generated: data.as_of, status: data.status,
    reason: text(data.reason), districts: [], sources: [], institutions: [], limits: [], offset: 0, nextOffset: null, total: 0};
  if (['unmapped', 'not_covered', 'unavailable'].includes(data.status)) return base;
  if (!['district', 'institution', 'state'].includes(data.kind) || !record(data.sources)) throw contractError();
  const districts = data.kind === 'district' ? [data.district] : data.districts;
  if (!Array.isArray(districts) || districts.length > 5) throw contractError();
  if (data.kind !== 'district') {
    if (!Number.isInteger(data.offset) || data.offset !== expectedOffset || !Number.isInteger(data.districts_total) || data.districts_total < 0 ||
      data.districts_total > 1000 || data.offset > data.districts_total || data.offset + districts.length > data.districts_total ||
      data.next_offset != null && (!Number.isInteger(data.next_offset) || data.next_offset <= data.offset || data.next_offset !== data.offset + districts.length || data.next_offset >= data.districts_total)) throw contractError();
    if (data.next_offset == null && data.offset + districts.length < data.districts_total) throw contractError();
    base.offset = data.offset; base.nextOffset = data.next_offset ?? null; base.total = data.districts_total;
  }
  base.districts = districts.map(d => districtModel(d, data.sources));
  if (data.kind === 'district') {
    if (base.districts[0].id !== data.id) throw contractError();
    base.name = `${base.districts[0].name}, ${base.districts[0].state}`; base.total = 1;
  }
  base.institutions = (Array.isArray(data.institutions) ? data.institutions : []).flatMap(item => {
    const id = typeof item === 'string' ? item : item?.id;
    return validPlace(id) && /^in-(dccb|stcb)-/.test(id) ? [{id, basis: text(item?.basis).replaceAll('_', ' ')}] : [];
  }).slice(0, 500);
  base.sources = Object.entries(data.sources).filter(([, source]) => record(source)).map(([key, source]) => ({
    label: text(source.product) || text(source.title) || key.replaceAll('_', ' '),
    detail: [source.credit, source.author, source.licence, source.through && `Through ${source.through}`, source.as_of, source.vintage && `Boundary vintage ${source.vintage}`].filter(v => typeof v === 'string').join(' · '),
    url: safeSource(source.url),
  }));
  base.limits = (Array.isArray(data.limits) ? data.limits : []).filter(v => typeof v === 'string').slice(0, 20);
  return base;
}

/** Each view has one active request; old responses cannot replace a newer selection. */
export function createEvidenceLoader(fetcher = globalThis.fetch, timeoutMs = 15000) {
  let sequence = 0, controller;
  return {
    cancel() {sequence += 1; controller?.abort();},
    async load(id, offset = 0) {
      if (!validPlace(id) || !Number.isInteger(offset) || offset < 0 || offset > 1000) throw new Error('Enter a valid district, state, or cooperative-bank ID.');
      const current = ++sequence;
      controller?.abort();
      const requestController = new AbortController(); controller = requestController;
      let timedOut = false;
      const timer = setTimeout(() => {timedOut = true; requestController.abort();}, timeoutMs);
      try {
        const response = await fetcher(`${GEO_API}${encodeURIComponent(id)}?offset=${offset}`, {signal: requestController.signal, headers: {Accept: 'application/json'}, credentials: 'omit'});
        if (response.status === 404) throw new Error('This district, state, or bank ID is not covered. Check the exact ID or choose a district from the list.');
        const data = await readBounded(response, 256 * 1024);
        if (current !== sequence) return null;
        return evidenceModel(data, id, offset);
      } catch (error) {
        if (current !== sequence) return null;
        if (timedOut) throw new Error('The evidence request timed out. Retry to load this place.');
        throw error;
      } finally {clearTimeout(timer);}
    },
  };
}
