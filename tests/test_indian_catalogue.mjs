import test from 'node:test';
import assert from 'node:assert/strict';
import {FEATURED, PUBLISHED_COLLECTION_IDS, entriesFor, searchDraft} from '../banking/real-assets/indian-catalogue.mjs';

const today = '2026-11-05';
const jaipur = [75.6, 26.6, 76.4, 27.4];

test('featured collection identifiers are published, unique, and not loaded', () => {
  assert.equal(new Set(PUBLISHED_COLLECTION_IDS).size, PUBLISHED_COLLECTION_IDS.length);
  const collections = FEATURED.filter(item => item.kind === 'collection');
  assert.ok(collections.length >= 10);
  for (const item of FEATURED) {
    assert.equal(item.scenesLoaded, false);
    assert.ok(item.href.startsWith('https://'));
    assert.equal(JSON.stringify(item).includes('downloaded scene'), false);
  }
  for (const item of collections) assert.ok(PUBLISHED_COLLECTION_IDS.includes(item.id), item.id);
  assert.ok(PUBLISHED_COLLECTION_IDS.includes('EOS-06_SCAT_3WW'));
  assert.equal(FEATURED.some(item => item.id.startsWith('EOS-06_SCAT')), false);
});

test('questions keep crop, water, radar and planning apart', () => {
  const crop = entriesFor('crop').map(item => item.id);
  const water = entriesFor('water').map(item => item.id);
  assert.ok(crop.includes('EOS-06_OCM-LAC_NDVI_8day_360m'));
  assert.equal(crop.includes('EOS-06_OCM-LAC_L2C-CHL'), false);
  assert.ok(water.includes('EOS-06_OCM-LAC_L2C-CHL'));
  assert.ok(entriesFor('radar').some(item => item.id === 'NISAR_SSAR_GCOV'));
  assert.ok(entriesFor('planning').some(item => item.id === 'vedas-builtup'));
  assert.ok(entriesFor('access').some(item => item.id === 'inspace-rules'));
  assert.equal(entriesFor('all').length, FEATURED.length);
  assert.throws(() => entriesFor('credit'), /Unknown catalogue question/);
});

test('a search draft is local and matches the private connector body', () => {
  const draft = searchDraft({collectionId: 'EOS-04_SAR-MRS_L2B', bbox: jaipur, start: '2025-11-02', end: '2026-11-02'}, today);
  assert.deepEqual(Object.keys(draft).sort(), ['bbox', 'collections', 'end_date', 'limit', 'start_date']);
  assert.deepEqual(draft.collections, ['EOS-04_SAR-MRS_L2B']);
  assert.equal(draft.limit, 10);
  assert.equal(JSON.stringify(draft).includes('Bearer'), false);
  assert.throws(() => searchDraft({collectionId: 'Landsat-8_fake', bbox: jaipur, start: '2025-11-02', end: '2026-11-02'}, today), /not on the reviewed/);
  assert.throws(() => searchDraft({collectionId: 'EOS-04_SAR-MRS_L2B', bbox: jaipur, start: '2026-11-02', end: '2025-11-02'}, today), /earlier image date/);
  assert.throws(() => searchDraft({collectionId: 'EOS-04_SAR-MRS_L2B', bbox: jaipur, start: '2026-11-06', end: '2026-11-06'}, today), /future/);
  assert.throws(() => searchDraft({collectionId: 'EOS-04_SAR-MRS_L2B', bbox: jaipur, start: '2026-02-31', end: '2026-03-01'}, today), /YYYY-MM-DD/);
});
