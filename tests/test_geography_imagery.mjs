import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {imageURL, moveBox, PRESETS, stateFromURL, validBox, validDate} from '../banking/geography/imagery-model.mjs';
import {installDOM, settle} from './fixtures/geography-dom.mjs';
test('WMS uses explicit date, longitude-first 1.1.1 axis order and the same viewport for comparison', () => {
  const a = new URL(imageURL('2025-11-02', PRESETS.india.bbox));
  const b = new URL(imageURL('2026-11-02', PRESETS.india.bbox));
  assert.equal(a.origin, 'https://gibs.earthdata.nasa.gov');
  assert.equal(a.searchParams.get('BBOX'), '66,5,99,38');
  assert.equal(a.searchParams.get('VERSION'), '1.1.1');
  assert.equal(a.searchParams.get('TIME'), '2025-11-02');
  b.searchParams.set('TIME', '2025-11-02'); assert.equal(a.href, b.href);
});
test('reject impossible and future dates rather than silently normalizing them', () => {
  for (const date of ['2025-02-30','2025-13-01','2025-2-01','not-a-date','2099-01-01']) assert.equal(validDate(date, '2026-11-05'), false);
  assert.equal(validDate('2024-02-29', '2026-11-05'), true);
  assert.equal(validDate('2014-01-01', '2026-11-05'), false);
});
test('untrusted share URLs cannot inject hosts or invalid geographic extents', () => {
  for (const view of ['0,0,0,0', 'NaN,2,3,4', '-181,0,20,30', '0,-90,30,30', '10,10,5,5']) {
    assert.deepEqual(stateFromURL(`?view=${view}&before=bad`).bbox, PRESETS.india.bbox);
  }
  assert.throws(() => imageURL('2025-11-02', [0, 0, Infinity, 30]));
});
test('zoom and repeated pan remain bounded and preserve usable scale', () => {
  let box = PRESETS.india.bbox;
  for (let i = 0; i < 40; i++) box = moveBox(box, .6, 30, 30);
  assert.equal(validBox(box), true); assert.ok(box[2] <= 180 && box[3] <= 85);
  for (let i = 0; i < 40; i++) box = moveBox(box, 2, -30, -30);
  assert.equal(validBox(box), true); assert.ok(box[0] >= -180 && box[1] >= -85);
});
test('shared views identify their preset and pan or zoom changes the selector to Custom', async t => {
  const html = readFileSync(new URL('../banking/geography/index.html', import.meta.url), 'utf8');
  assert.match(html, /<option value="custom" disabled>Custom view<\/option>/);
  const nodes = installDOM(t, [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]));
  globalThis.location = new URL('https://liquilens.in/banking/geography/?before=2025-11-02&after=2026-11-02&view=74.6,25.9,77.1,28.4');
  globalThis.history = {replaceState(_state, _title, url) { globalThis.location = new URL(url, globalThis.location); }};
  globalThis.fetch = async url => String(url).endsWith('places.json') ? new Response('[]') : new Response('image fixture', {headers: {'content-type': 'image/jpeg'}});
  await import('../banking/geography/app.mjs?control-regression'); await settle();
  assert.equal(nodes.get('region').value, 'jaipur');
  assert.equal(nodes.get('viewer').attributes['aria-busy'], 'false');
  nodes.get('zoom-in').listeners.click(); await settle();
  assert.equal(nodes.get('region').value, 'custom');
  assert.notEqual(globalThis.location.searchParams.get('view'), PRESETS.jaipur.bbox.join(','));
  nodes.get('reset').listeners.click(); await settle();
  assert.equal(nodes.get('region').value, 'india');
  assert.equal(globalThis.location.searchParams.get('view'), PRESETS.india.bbox.join(','));
  nodes.get('viewer').listeners.keydown({key: 'ArrowRight', preventDefault() {}}); await settle();
  assert.equal(nodes.get('region').value, 'custom');
  assert.notEqual(globalThis.location.searchParams.get('view'), PRESETS.india.bbox.join(','));
});
