import test from 'node:test';
import assert from 'node:assert/strict';
import {gnpaHistory, gnpaChart, provisionalSection} from '../research-ui/institution-detail.mjs';
import {reviewModel} from '../banking/model.mjs';

const metric = value => ({value, unit: 'percent', status: 'observed'});
const period = (date, value) => ({period_end: date, metrics: {gnpa_pct: metric(value)}});
class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.attributes = {}; this.textContent = ''; }
  append(...children) { this.children.push(...children); }
  setAttribute(key, value) { this.attributes[key] = value; }
}
const descendants = node => [node, ...node.children.flatMap(descendants)];
const content = node => descendants(node).map(item => item.textContent).join(' ');
function dom(run) {
  const previous = globalThis.document;
  globalThis.document = {createElement: tag => new Element(tag), createElementNS: (_, tag) => new Element(tag)};
  try { run(); } finally { globalThis.document = previous; }
}

test('GNPA history sorts dates while retaining zero, missing and ambiguous periods', () => {
  const input = [period('2026-09-30', 3), period('2026-03-31', 0), period('2026-06-30', null), period('2025-12-31', 2), period('2025-12-31', 7)];
  const before = structuredClone(input);
  assert.deepEqual(gnpaHistory(input), [
    {date: '2025-12-31', value: null, duplicate: true}, {date: '2026-03-31', value: 0},
    {date: '2026-06-30', value: null}, {date: '2026-09-30', value: 3},
  ]);
  assert.deepEqual(input, before);
});

test('malformed records never become valid GNPA readings or corrupt SVG coordinates', () => {
  const invalid = [null, {}, period('2026-02-30', 5), period('today', 1)];
  assert.deepEqual(gnpaHistory(invalid), []);
  for (const value of [undefined, null, '0', NaN, Infinity, -1, 101]) {
    assert.equal(gnpaHistory([period('2026-03-31', value)])[0].value, null);
  }
  for (const patch of [{unit: 'basis_points'}, {status: 'not_disclosed'}]) {
    assert.equal(gnpaHistory([{period_end: '2026-03-31', metrics: {gnpa_pct: {...metric(2), ...patch}}}])[0].value, null);
  }
  dom(() => assert.match(content(gnpaChart({history: invalid})), /No comparable GNPA/));
});

test('a gap breaks the rendered line and isolated observations remain visible', () => dom(() => {
  const chart = gnpaChart({history: [period('2026-03-31', 0), period('2026-06-30', null), period('2026-09-30', 4), period('2026-12-31', 5)]});
  const nodes = descendants(chart), path = nodes.find(node => node.tag === 'path').attributes.d;
  assert.equal((path.match(/M/g) || []).length, 2);
  assert.equal((path.match(/L/g) || []).length, 1);
  assert.equal(nodes.filter(node => node.tag === 'circle').length, 3);
  assert.match(content(chart), /2026-06-30: not disclosed/);
  assert.doesNotMatch(path, /NaN|Infinity/);
}));

test('one observation is drawn as a dot and duplicate periods break the line', () => dom(() => {
  const single = descendants(gnpaChart({history: [period('2026-03-31', 0)]}));
  assert.equal(single.filter(node => node.tag === 'circle').length, 1);
  assert.equal(single.find(node => node.tag === 'circle').attributes.cx, '242.5');
  const duplicate = gnpaChart({history: [period('2026-03-31', 1), period('2026-06-30', 2), period('2026-06-30', 9), period('2026-09-30', 3)]});
  assert.doesNotMatch(descendants(duplicate).find(node => node.tag === 'path').attributes.d, /L/);
  assert.match(content(duplicate), /duplicate reporting period, withheld/);
}));

test('rendered provisional figures keep their own clock and accepted asset quality date', () => dom(() => {
  const record = {schema: 'liquilens.bank-specialisation.v1', status: 'observed', name: 'Example Bank',
    score_authority: false, can_authorize_credit: false, period_end: '2026-06-30', metrics: {gnpa_pct: metric(0)},
    provisional_update: {status: 'provisional', period_end: '2026-09-30', publication_date: '2026-10-03',
      retrieved_at: '2026-10-14T08:38:45Z', full_financial_results: false, asset_quality_period_refreshed: false,
      score_authority: false, training_eligible: false, metrics: {casa_pct: metric(0), gnpa_pct: metric(99)},
      sources: ['https://example.org/provisional.pdf', 'javascript:alert(1)']}};
  const model = reviewModel(record), rendered = provisionalSection(model.provisional);
  assert.match(content(rendered), /Reporting period: 2026-09-30.*Published: 2026-10-03.*Captured: 2026-10-14/);
  assert.match(content(rendered), /NPA and capital figures above remain dated 2026-06-30/);
  assert.match(content(rendered), /0%/);
  assert.doesNotMatch(content(rendered), /99%/);
  assert.equal(model.metrics[0].value, '0%');
  const links = descendants(rendered).filter(node => node.tag === 'a');
  assert.deepEqual(links.map(node => node.href), ['https://example.org/provisional.pdf']);
  assert.equal(links[0].rel, 'noopener noreferrer');
  assert.equal(provisionalSection(null), null);
}));
