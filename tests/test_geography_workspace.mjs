import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {briefCSV, briefHTML, createBrief, frameSelection, selectionFromURL, workspaceQuery} from '../banking/geography/workspace-model.mjs';
import {evidenceModel, DEFAULT_PLACE} from '../banking/geography/evidence-model.mjs';
import {PRESETS, validBox} from '../banking/geography/imagery-model.mjs';
import {Element, installDOM, settle} from './fixtures/geography-dom.mjs';
import {initEvidence} from '../banking/geography/evidence.mjs';

const data = () => ({schema: 'liquilens.lending-geography.v1', id: DEFAULT_PLACE, kind: 'district', scope: 'research',
  score_authority: false, scoring_eligible: false, training_corpus_changed: false, as_of: '2026-11-04', status: 'observed',
  district: {id: DEFAULT_PLACE, name: 'Jaipur', state: 'Rajasthan',
    jjas: {year: 2026, mm: null, normal_mm: 600, departure_pct: null},
    recent_months: {from: '2026-08', mm: [0, null], normal_mm: [8, 12], departure_pct: [-100, null]},
    soil_moisture: {as_of: '2024-10-15', sm_m3_m3: .2}},
  sources: {rainfall: {product: 'CHIRPS', through: '2026-09', licence: 'Public source', url: 'https://example.org/rain'},
    soil_moisture: {product: 'ESA CCI', credit: 'ESA', as_of: '2024-10-15', url: 'https://example.org/soil'}},
  limits: ['Research only.']});
const imagery = {bbox: PRESETS.india.bbox, before: '2025-11-02', after: '2026-11-02'};

test('share URL round trip restores district identity and exact page without accepting arbitrary IDs', () => {
  const query = workspaceQuery(imagery, {id: 'in-state-rajasthan', offset: 5});
  assert.deepEqual(selectionFromURL(query), {id: 'in-state-rajasthan', offset: 5});
  assert.equal(new URLSearchParams(query).get('view'), '66,5,99,38');
  assert.deepEqual(selectionFromURL('?evidence=../../secret&offset=5'), {id: null, offset: 0});
  for (const offset of ['-5', 'Infinity', '3.5', '1e2', '1001']) assert.equal(selectionFromURL(`?evidence=${DEFAULT_PLACE}&offset=${offset}`).offset, 0);
});

test('district selection uses exact catalog IDs and outward padding; missing metadata does not invent a location', () => {
  const model = evidenceModel(data(), DEFAULT_PLACE);
  const place = {id: DEFAULT_PLACE, state: 'Rajasthan', gb_shape_id: 'verified-shape-id', boundary_vintage: '2021', bbox: [75.7, 26.8, 75.71, 26.81]};
  const frame = frameSelection(model, [place]);
  assert.ok(validBox(frame.bbox)); assert.ok(frame.bbox[0] < place.bbox[0] && frame.bbox[2] > place.bbox[2]);
  assert.equal(frame.district_count, 1);
  assert.equal(frameSelection(model, [{...place, boundary_vintage: 'current'}]), null);
  assert.equal(frameSelection(model, [{...place, bbox: [NaN, 1, 2, 3]}]), null);
  assert.equal(frameSelection(model, [{...place, id: 'in-dist-rajasthan-ajmer'}]), null);
});

test('state viewport covers the full known state even when evidence is paginated', () => {
  const places = JSON.parse(readFileSync(new URL('../banking/geography/places.json', import.meta.url)));
  const model = {...evidenceModel(data(), DEFAULT_PLACE), id: 'in-state-rajasthan', offset: 5, total: 33};
  const frame = frameSelection(model, places);
  assert.equal(frame.district_count, places.filter(p => p.state === 'Rajasthan').length);
  assert.equal(frame.scope, 'state districts');
  assert.ok(frame.district_count > model.districts.length);
});

test('brief preserves null versus zero, independent source clocks and evidence-page scope', () => {
  const model = {...evidenceModel(data(), DEFAULT_PLACE), id: 'in-state-rajasthan', offset: 5, total: 33, nextOffset: 6};
  const brief = createBrief(model, imagery, 'https://liquilens.in/banking/geography/?evidence=in-state-rajasthan&offset=5', '2026-11-05T13:00:00Z');
  assert.equal(brief.source_payload.district.recent_months.mm[0], 0);
  assert.equal(brief.source_payload.district.recent_months.mm[1], null);
  assert.equal(brief.imagery.later_date, '2026-11-02');
  assert.equal(brief.source_payload.district.soil_moisture.as_of, '2024-10-15');
  assert.equal(brief.selection.coverage, 'Current evidence page only');
  assert.equal(brief.selection.offset, 5); assert.equal(brief.selection.districts_included, 1); assert.equal(brief.selection.districts_total, 33);
  brief.sources.push({label: 'Boundary source'}); assert.equal(model.sources.length, 2);
  const csv = briefCSV(brief);
  assert.match(csv, /monthly_rainfall,2026-08,0,mm,8,-100/);
  assert.match(csv, /monthly_rainfall,2026-09,,mm,12,,/);
  assert.match(csv, /soil_moisture,2024-10-15,0.2,m3\/m3/);
  assert.match(csv, /2026-11-04,5,1,33,2025-11-02,2026-11-02/);
});

test('missing imagery stays unavailable and printable briefs escape untrusted labels', () => {
  const model = evidenceModel(data(), DEFAULT_PLACE); model.name = '<script>alert(1)</script>';
  const brief = createBrief(model, null, 'javascript:alert(1)');
  assert.equal(brief.imagery.status, 'unavailable');
  const html = briefHTML(brief);
  assert.ok(!html.includes('<script>')); assert.match(html, /&lt;script&gt;/);
  assert.ok(!html.includes('javascript:')); assert.match(html, /2024-10-15/);
  assert.match(html, /Includes 1 of 1 districts/); assert.match(html, /Not available/);
  assert.throws(() => createBrief({...model, districts: []}, imagery, 'https://liquilens.in'), /Load district/);
});

test('new and invalid evidence selections clear a previously exportable result', async t => {
  installDOM(t);
  let exportable = null;
  globalThis.fetch = async url => String(url).endsWith('places.json') ? new Response('[]') : new Response(JSON.stringify(data()));
  const ui = initEvidence(new Element('main'), {onLoading() {exportable = null;}, onModel(model) {exportable = model;}, onInvalid() {exportable = null;}});
  t.after(() => ui.destroy());
  await ui.load(DEFAULT_PLACE); assert.equal(exportable.id, DEFAULT_PLACE);
  const pending = ui.load(DEFAULT_PLACE); assert.equal(exportable, null); await pending;
  await ui.load('not-a-valid-place'); assert.equal(exportable, null);
});

test('a shared view restores evidence while retaining the explicit imagery viewport', async t => {
  const html = readFileSync(new URL('../banking/geography/index.html', import.meta.url), 'utf8');
  const nodes = installDOM(t, [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]));
  globalThis.location = new URL(`https://liquilens.in/banking/geography/?view=74.6,25.9,77.1,28.4&before=2025-11-02&after=2026-11-02&evidence=${DEFAULT_PLACE}&offset=0`);
  globalThis.history = {replaceState(_state, _title, url) {globalThis.location = new URL(url, globalThis.location);}};
  globalThis.fetch = async url => {
    if (String(url).endsWith('places.json')) return new Response(JSON.stringify([{id: DEFAULT_PLACE, name: 'Jaipur', state: 'Rajasthan', bbox: [75,26,76,27], gb_shape_id: 'x', boundary_vintage: '2021'}]));
    if (String(url).includes('places-source.json')) return new Response('{}');
    if (String(url).includes('api.liquilens.in')) return new Response(JSON.stringify(data()));
    return new Response('image fixture', {headers: {'content-type': 'image/jpeg'}});
  };
  await import('../banking/geography/app.mjs?shared-evidence-regression'); await settle();
  assert.equal(nodes.get('download-json').disabled, false);
  assert.equal(globalThis.location.searchParams.get('evidence'), DEFAULT_PLACE);
  assert.equal(globalThis.location.searchParams.get('view'), '74.6,25.9,77.1,28.4');
  assert.match(nodes.get('framing-label').textContent, /Shared image viewport/);
  nodes.get('flow-district').listeners.click(); await settle();
  assert.notEqual(globalThis.location.searchParams.get('view'), '74.6,25.9,77.1,28.4');
  assert.match(nodes.get('framing-label').textContent, /2021 district extents/);
});
