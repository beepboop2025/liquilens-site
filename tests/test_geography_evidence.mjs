import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createEvidenceLoader, DEFAULT_PLACE, evidenceModel, formatNumber, recentMonths, safeSource, validPlace} from '../banking/geography/evidence-model.mjs';
import {initEvidence} from '../banking/geography/evidence.mjs';
import {Element, installDOM, settle} from './fixtures/geography-dom.mjs';

const district = () => ({id: DEFAULT_PLACE, name: 'Jaipur', state: 'Rajasthan',
  jjas: {year: 2026, mm: 482, normal_mm: 602, departure_pct: -20, category: 'Deficient'},
  soil_moisture: {as_of: '2024-10-15', sm_m3_m3: 0.201},
  vegetation_health: {as_of: '2026-W43', vhi: 50.4},
  recent_months: {from: '2025-12', mm: [0, null, 10], normal_mm: [5, 6, 7], departure_pct: [-100, null, 43], low_normal_months: ['2025-12']},
  declared_drought: {years: ['2023-24'], source: 'CMP 2026 Appendix 4'}});
const response = () => ({schema: 'liquilens.lending-geography.v1', id: DEFAULT_PLACE, kind: 'district', as_of: '2026-11-04',
  scope: 'research', score_authority: false, training_corpus_changed: false, scoring_eligible: false, status: 'observed', district: district(),
  institutions: [{id: 'in-dccb-rajasthan-jaipur', basis: 'nafscob_area_of_operation_note_2025'}],
  sources: {soil_moisture: {as_of: '2024-10-15', product: 'ESA CCI Soil Moisture', credit: 'ESA CCI'},
    vegetation_health: {as_of: '2026-W43', product: 'NOAA VHP', credit: 'NOAA'},
    declared_drought: {title: 'Drought declarations', url: 'https://example.org/drought.pdf'}}, limits: ['Research only.']});

test('separate signal observation dates survive the model; response date does not refresh soil moisture', () => {
  const model = evidenceModel(response(), DEFAULT_PLACE);
  assert.equal(model.generated, '2026-11-04');
  assert.match(model.districts[0].signals[1].date, /2024-10-15.*historical/);
  assert.match(model.districts[0].signals[0].date, /2026-W43/);
  assert.equal(model.districts[0].rainfall[0].value, '482 mm');
  assert.match(model.districts[0].rainfall[0].date, /2026.*June/);
});
test('zero rainfall and missing rainfall stay distinct across year boundaries', () => {
  const rows = recentMonths(district().recent_months);
  assert.deepEqual(rows.map(row => row.month), ['2025-12', '2026-01', '2026-02']);
  assert.equal(rows[0].mm, 0); assert.equal(rows[1].mm, null);
  assert.equal(formatNumber(null), 'Not available'); assert.equal(formatNumber(NaN), 'Not available'); assert.equal(formatNumber(0), '0');
  assert.equal(rows[0].lowNormal, true);
});
test('malformed history lengths and non-finite readings are rejected', () => {
  assert.throws(() => recentMonths({...district().recent_months, normal_mm: [2]}));
  assert.throws(() => recentMonths({...district().recent_months, from: '2025-13'}));
  assert.throws(() => recentMonths({...district().recent_months, mm: [0, NaN, 10]}));
  assert.throws(() => recentMonths({...district().recent_months, mm: [0, -2, 10]}));
});
test('research boundary, selected identity, date, shape and source clocks fail closed', () => {
  for (const [key, value] of [['schema', 'other'], ['score_authority', true], ['scoring_eligible', true], ['scope', 'supported'], ['training_corpus_changed', true], ['as_of', '2026-02-30']]) {
    assert.throws(() => evidenceModel({...response(), [key]: value}, DEFAULT_PLACE));
  }
  assert.throws(() => evidenceModel(response(), 'in-dist-rajasthan-ajmer'));
  const mismatch = response(); mismatch.sources.soil_moisture.as_of = '2026-10-15';
  assert.throws(() => evidenceModel(mismatch, DEFAULT_PLACE));
  const impossible = response(); impossible.district.vegetation_health.vhi = 101;
  assert.throws(() => evidenceModel(impossible, DEFAULT_PLACE));
});
test('absent signals and drought history remain explicitly unavailable', () => {
  const data = response(); delete data.district.soil_moisture; delete data.district.declared_drought;
  const d = evidenceModel(data, DEFAULT_PLACE).districts[0];
  assert.equal(d.signals[1].value, 'Not available'); assert.equal(d.droughtYears, null);
});
test('only safe HTTPS source links and structured IDs are accepted', () => {
  assert.equal(safeSource('javascript:alert(1)'), null); assert.equal(safeSource('https://user:pass@example.org'), null);
  assert.equal(safeSource('https://example.org/source.pdf'), 'https://example.org/source.pdf');
  assert.equal(validPlace('../../secret'), false); assert.equal(validPlace('in-dist-rajasthan-jaipur?x=1'), false);
  assert.equal(validPlace(DEFAULT_PLACE), true);
});
test('pagination is bound to requested offset and cannot loop or silently truncate', () => {
  const id = 'in-state-rajasthan';
  const page = {...response(), id, kind: 'state', state: 'Rajasthan', district: undefined, districts: [district()], districts_total: 2, offset: 0, next_offset: 1};
  assert.equal(evidenceModel(page, id).nextOffset, 1);
  assert.throws(() => evidenceModel({...page, next_offset: 0}, id));
  assert.throws(() => evidenceModel({...page, next_offset: null}, id));
  assert.throws(() => evidenceModel(page, id, 5));
  const last = {...page, offset: 1, next_offset: null};
  assert.equal(evidenceModel(last, id, 1).offset, 1);
});
test('unmapped and unavailable places are honest empty states', () => {
  const data = {...response(), status: 'unmapped', reason: 'No verified district link'};
  const model = evidenceModel(data, DEFAULT_PLACE); assert.deepEqual(model.districts, []); assert.equal(model.reason, data.reason);
});
test('a slow earlier request cannot replace newer evidence, even when fetch ignores abort', async () => {
  const waiting = [];
  const loader = createEvidenceLoader(() => new Promise(resolve => waiting.push(resolve)));
  const first = loader.load(DEFAULT_PLACE); const second = loader.load(DEFAULT_PLACE);
  waiting[1](new Response(JSON.stringify(response())));
  assert.equal((await second).id, DEFAULT_PLACE);
  waiting[0](new Response(JSON.stringify(response())));
  assert.equal(await first, null);
});
test('timeouts, rate limits, and oversized transport bodies produce actionable failures', async () => {
  const timeout = createEvidenceLoader((_, {signal}) => new Promise((_, reject) => signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))), 5);
  await assert.rejects(timeout.load(DEFAULT_PLACE), /timed out/);
  await assert.rejects(createEvidenceLoader(async () => new Response('{}', {status: 429})).load(DEFAULT_PLACE), /rate limit/);
  await assert.rejects(createEvidenceLoader(async () => new Response('{}', {status: 404})).load(DEFAULT_PLACE), /not covered/);
  await assert.rejects(createEvidenceLoader(async () => new Response('x'.repeat(256 * 1024 + 1))).load(DEFAULT_PLACE), /display limit/);
});
test('all-India discovery contains only unique district labels and IDs, never geometry', () => {
  const places = JSON.parse(readFileSync(new URL('../banking/geography/places.json', import.meta.url)));
  assert.equal(places.length, 735); assert.equal(new Set(places.map(place => place.id)).size, places.length);
  assert.ok(places.some(place => place.id === DEFAULT_PLACE));
  assert.ok(places.every(place => validPlace(place.id) && Object.keys(place).sort().join() === 'id,name,state'));
});
test('rejected district searches cancel pending evidence and clear previously displayed evidence', async t => {
  installDOM(t);
  const directory = [{id: DEFAULT_PLACE, name: 'Jaipur', state: 'Rajasthan'},
    {id: 'in-dist-first-duplicate', name: 'Duplicate', state: 'First'},
    {id: 'in-dist-second-duplicate', name: 'Duplicate', state: 'Second'}];
  let complete, requestSignal, delay = true;
  globalThis.fetch = async (url, options) => {
    if (String(url).endsWith('places.json')) return new Response(JSON.stringify(directory));
    requestSignal = options.signal;
    return delay ? new Promise(resolve => { complete = resolve; }) : new Response(JSON.stringify(response()));
  };
  const root = new Element('main'), ui = initEvidence(root); t.after(() => ui.destroy());
  await settle();
  const form = root.children[0].children[2], input = form.children[0].children[0];
  const status = root.children[4], results = root.children[5];
  const pending = ui.load(DEFAULT_PLACE);
  input.value = 'Unknown district'; form.listeners.submit({preventDefault() {}});
  const rejectedStatus = status.textContent;
  assert.equal(requestSignal.aborted, true); assert.equal(results.attributes['aria-busy'], 'false');
  complete(new Response(JSON.stringify(response()))); await pending;
  assert.equal(status.textContent, rejectedStatus); assert.equal(results.children.length, 0);
  delay = false; await ui.load(DEFAULT_PLACE); assert.ok(results.children.length > 0);
  input.value = 'Duplicate'; form.listeners.submit({preventDefault() {}});
  assert.match(status.textContent, /more than one state/); assert.equal(results.children.length, 0);
});
