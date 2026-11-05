import {safeSource, validPlace} from './evidence-model.mjs';
import {LAYER, validBox, validDate} from './imagery-model.mjs';

/** Shared by the public explorer and the native product workspaces. */
export function selectionFromURL(search) {
  const query = new URLSearchParams(search);
  const id = query.get('evidence');
  const rawOffset = query.get('offset') ?? '0';
  const offset = /^\d{1,4}$/.test(rawOffset) ? Number(rawOffset) : 0;
  return {id: validPlace(id) ? id : null, offset: validPlace(id) && offset <= 1000 ? offset : 0};
}

export function workspaceQuery(imagery, selection = {}) {
  const query = new URLSearchParams();
  if (validBox(imagery?.bbox)) query.set('view', imagery.bbox.join(','));
  if (validDate(imagery?.before)) query.set('before', imagery.before);
  if (validDate(imagery?.after)) query.set('after', imagery.after);
  if (validPlace(selection.id)) {
    query.set('evidence', selection.id);
    query.set('offset', String(Number.isInteger(selection.offset) && selection.offset >= 0 && selection.offset <= 1000 ? selection.offset : 0));
  }
  return query.toString();
}

const validExtent = box => Array.isArray(box) && box.length === 4 && box.every(Number.isFinite)
  && box[0] >= -180 && box[2] <= 180 && box[1] >= -85 && box[3] <= 85 && box[2] > box[0] && box[3] > box[1];
const stateId = name => `in-state-${name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')}`;

/** A boundary-derived extent frames context; it is not a rendered parcel or district outline. */
export function frameSelection(model, places) {
  if (!model?.districts?.length || !Array.isArray(places)) return null;
  const wanted = new Set(model.districts.map(district => district.id));
  const rows = places.filter(place => model.id.startsWith('in-state-') ? stateId(place.state) === model.id : wanted.has(place.id));
  if (!rows.length || (!model.id.startsWith('in-state-') && rows.length !== wanted.size)
      || rows.some(place => !validExtent(place.bbox) || place.boundary_vintage !== '2021' || typeof place.gb_shape_id !== 'string')) return null;
  const extent = [Math.min(...rows.map(row => row.bbox[0])), Math.min(...rows.map(row => row.bbox[1])),
    Math.max(...rows.map(row => row.bbox[2])), Math.max(...rows.map(row => row.bbox[3]))];
  const width = Math.max(.25, (extent[2] - extent[0]) * 1.12), height = Math.max(.25, (extent[3] - extent[1]) * 1.12);
  const x = (extent[0] + extent[2]) / 2, y = (extent[1] + extent[3]) / 2;
  const bbox = [x - width / 2, y - height / 2, x + width / 2, y + height / 2].map(value => Number(value.toFixed(6)));
  if (!validBox(bbox)) return null;
  return {bbox, extent, district_count: rows.length, boundary_vintage: '2021',
    scope: model.id.startsWith('in-state-') ? 'state districts' : model.id.startsWith('in-dist-') ? 'selected district' : 'districts on this evidence page',
    interpretation: 'Viewport derived from geoBoundaries 2021 district extents. It is not a parcel outline or a measure of lender exposure.'};
}

export function createBrief(model, imagery, viewURL, exportedAt = new Date().toISOString()) {
  if (!model?.districts?.length || !validPlace(model.id)) throw new Error('Load district observations before downloading a brief.');
  const image = imagery && validBox(imagery.bbox) && validDate(imagery.before) && validDate(imagery.after) && imagery.before < imagery.after
    ? {status: 'displayed', source: 'NASA GIBS', product: 'Terra MODIS true colour', layer: LAYER,
      source_resolution: '250 m; displayed resolution varies', earlier_date: imagery.before, later_date: imagery.after,
      bbox: [...imagery.bbox], crs: 'EPSG:4326', source_url: 'https://nasa-gibs.github.io/gibs-api-docs/'}
    : {status: 'unavailable', reason: 'No successfully loaded image comparison was available when this brief was created.'};
  return {schema: 'liquilens.geography-brief.v1', scope: 'research', exported_at: exportedAt, view_url: safeSource(viewURL) ?? 'https://liquilens.in/banking/geography/',
    selection: {id: model.id, name: model.name, status: model.status, response_date: model.generated,
      offset: model.offset, districts_included: model.districts.length, districts_total: model.total,
      next_offset: model.nextOffset, coverage: model.total > model.districts.length ? 'Current evidence page only' : 'Selected evidence'},
    imagery: image, districts: model.districts, sources: model.sources.map(source => ({...source})), source_payload: model.payload ?? null,
    limits: [...new Set(['Image dates and observation dates are independent. Image comparison does not measure change.',
      'District aggregates and lender area links do not establish parcel condition, property value, lending share or credit risk.',
      'A missing observation remains unknown; no valuation or automated credit decision is produced.', ...model.limits])]};
}

const csvCell = value => {
  if (value == null) return '';
  let text = typeof value === 'object' ? JSON.stringify(value) : String(value);
  if (typeof value === 'string' && /^[=+@\-\t\r]/.test(text)) text = `'${text}`;
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};

export function briefCSV(brief) {
  const header = ['selection_id', 'district_id', 'district_name', 'state', 'observation', 'observed_at', 'value', 'unit', 'normal', 'departure_pct',
    'context', 'response_date', 'page_offset', 'districts_included', 'districts_total', 'image_earlier_date', 'image_later_date', 'image_bbox',
    'sources', 'limits', 'view_url'];
  const rows = [header];
  const raw = brief.source_payload;
  const rawDistricts = raw?.kind === 'district' ? [raw.district] : raw?.districts ?? [];
  for (const district of brief.districts) {
    const append = (observation, date, value, unit, normal = null, departure = null, context = '') => rows.push([
      brief.selection.id, district.id, district.name, district.state, observation, date, value, unit, normal, departure, context,
      brief.selection.response_date, brief.selection.offset, brief.selection.districts_included, brief.selection.districts_total,
      brief.imagery.earlier_date, brief.imagery.later_date, brief.imagery.bbox, brief.sources, brief.limits, brief.view_url]);
    for (const row of district.months) append('monthly_rainfall', row.month, row.mm, 'mm', row.normal, row.departure,
      row.lowNormal ? 'Normal below 10 mm; percentage departure may be unstable' : '');
    const source = rawDistricts.find(row => row?.id === district.id);
    for (const key of ['jjas', 'ond', 'fiscal_year', 'fiscal_year_to_date']) {
      const value = source?.[key];
      if (value) append(key, [value.year, value.through].filter(Boolean).join(' through '), value.mm, 'mm', value.normal_mm, value.departure_pct, value.category ?? '');
    }
    for (const [key, field, unit] of [['vegetation_health', 'vhi', 'index / 100'], ['soil_moisture', 'sm_m3_m3', 'm3/m3']]) {
      const value = source?.[key];
      append(key, value?.as_of ?? '', value?.[field] ?? null, unit, null, null, value ? 'Historical source observation' : 'Not supplied');
    }
  }
  return rows.map(row => row.map(csvCell).join(',')).join('\r\n');
}

const escape = value => String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
const display = value => value == null ? 'Not available' : escape(value);

export function briefHTML(brief) {
  const image = brief.imagery;
  const districts = brief.districts.map(d => `<section><h2>${escape(d.name)}, ${escape(d.state)}</h2>
    <table><thead><tr><th>Observation</th><th>Value</th><th>Observation date</th><th>Context</th></tr></thead><tbody>${[...d.rainfall, ...d.signals].map(m => `<tr><th>${escape(m.label)}</th><td>${escape(m.value)}</td><td>${escape(m.date)}</td><td>${escape(m.detail)}</td></tr>`).join('')}</tbody></table>
    <h3>Monthly rainfall</h3><table><thead><tr><th>Month</th><th>Rainfall (mm)</th><th>Normal (mm)</th><th>Departure (%)</th></tr></thead><tbody>${d.months.map(m => `<tr><th>${escape(m.month)}</th><td>${display(m.mm)}</td><td>${display(m.normal)}</td><td>${display(m.departure)}</td></tr>`).join('')}</tbody></table>
    <p>Drought declarations: ${d.droughtYears === null ? 'Not supplied' : d.droughtYears.length ? escape(d.droughtYears.join(', ')) : 'None listed in this source; this does not establish absence of drought.'} ${escape(d.droughtSource)}</p></section>`).join('');
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>${escape(brief.selection.name)} | LiquiLens geography brief</title><style>body{font:15px/1.55 Arial,sans-serif;color:#142c3f;max-width:1100px;margin:auto;padding:36px}h1{font-size:30px;line-height:1.2}h2{margin-top:30px}table{width:100%;border-collapse:collapse;font-size:12px}th,td{text-align:left;vertical-align:top;padding:8px;border-bottom:1px solid #cbd8e0}thead{display:table-header-group}a{color:#17617a}small{color:#4e6574}section{break-before:auto}tr{break-inside:avoid}@media print{body{padding:0;font-size:11px}table{font-size:9px}a{color:inherit}h2,h3{break-after:avoid}}@page{size:A4;margin:15mm}</style></head><body>
    <small>LiquiLens • Geography research brief</small><h1>${escape(brief.selection.name)}</h1>
    <p>${escape(brief.selection.coverage)}. Includes ${brief.selection.districts_included} of ${brief.selection.districts_total} districts; offset ${brief.selection.offset}. Response date ${escape(brief.selection.response_date)}. Exported ${escape(brief.exported_at)}.</p>
    <p><a href="${escape(brief.view_url)}">Reopen this research view</a>. Use your browser’s Print command to save this brief as a PDF.</p>
    <h2>Satellite context</h2><p>${image.status === 'displayed' ? `${escape(image.source)} / ${escape(image.product)}. Earlier image ${escape(image.earlier_date)}; later image ${escape(image.later_date)}. View [west, south, east, north]: ${escape(image.bbox.join(', '))}. ${escape(image.source_resolution)}. <a href="${escape(image.source_url)}">Imagery documentation</a>.` : escape(image.reason)}</p>
    ${districts}<section><h2>Sources and interpretation</h2><ul>${brief.sources.map(s => `<li>${s.url ? `<a href="${escape(s.url)}">${escape(s.label)}</a>` : escape(s.label)} — ${escape(s.detail)}</li>`).join('')}</ul><ul>${brief.limits.map(limit => `<li>${escape(limit)}</li>`).join('')}</ul></section></body></html>`;
}
