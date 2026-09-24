import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeView, restoreView, rememberView} from '../research-ui/view-state.mjs';

test('shared institution link wins over unrelated saved filters', () => {
  const storage = {getItem: () => JSON.stringify({query: 'another bank', sector: 'ucb', status: 'stale'})};
  assert.deepEqual(restoreView('https://liquilens.in/?institution=au-sfb', storage), {
    institution: 'au-sfb', query: '', sector: 'all', status: 'all', comparison: [],
  });
});

test('only bounded institution identifiers and choices survive persisted input', () => {
  assert.deepEqual(normalizeView({institution: '../bank', query: 'a'.repeat(500), status: 'safe', sector: 'approved',
    comparison: ['au-sfb', 'au-sfb', '<script>', 'rbl-bank', 'federal-bank', 'svc-ucb'], metrics: {gnpa: 0}}), {
    institution: null, query: 'a'.repeat(100), status: 'observed', sector: 'all', comparison: ['au-sfb', 'rbl-bank', 'federal-bank'],
  });
});

test('URL and saved preferences round-trip without storing evidence values', () => {
  let raw;
  const storage = {setItem: (_, value) => { raw = value; }, getItem: () => raw};
  const view = {institution: 'au-sfb', query: 'finance', sector: 'sfb', status: 'observed', comparison: ['au-sfb', 'jana-sfb']};
  const url = rememberView('https://liquilens.in/?verification=1#main', {...view, evidence: {value: 2.1}}, storage);
  assert.equal(url.searchParams.get('verification'), '1');
  assert.equal(url.hash, '#main');
  assert.deepEqual(JSON.parse(raw), view);
  assert.deepEqual(restoreView(url, storage), view);
});

test('corrupt or denied storage preserves working URL navigation', () => {
  assert.deepEqual(restoreView('https://liquilens.in/', {getItem: () => '{broken'}), normalizeView());
  const storage = {getItem: () => { throw Error('denied'); }, setItem: () => { throw Error('denied'); }};
  const url = rememberView('https://liquilens.in/', {institution: 'rbl-bank'}, storage);
  assert.equal(restoreView(url, storage).institution, 'rbl-bank');
});
