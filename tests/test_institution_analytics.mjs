import test from 'node:test';
import assert from 'node:assert/strict';
import {metric, institutionModel, bankHistory, movementRows, institutionSpecs} from '../research-ui/institution-analytics.js';
const m = value => ({value, unit: 'percent', status: 'observed'});
const data = () => ({schema:'liquilens.bank-specialisation.v1', slug:'example-bank', name:'Example Bank', sector:'bank', status:'observed', score_authority:false, can_authorize_credit:false, period_end:'2026-06-30', sources:['https://example.org/filing.pdf'], history:[], metrics:{gnpa_pct:m(0), crar_pct:m(15)}, changes:{}, npa_movement:{status:'unavailable'}});
test('disclosed zero survives while missing, text and mismatched units remain unavailable', () => {
  assert.equal(metric(data(),'gnpa_pct'),0); assert.equal(metric(data(),'nnpa_pct'),null);
  for(const value of [null, '0', Infinity]) assert.equal(metric({metrics:{gnpa_pct:m(value)}},'gnpa_pct'),null);
  assert.equal(metric({metrics:{gnpa_pct:{...m(2),unit:'basis_points'}}},'gnpa_pct'),null);
  assert.equal(metric({metrics:{gnpa_pct:{...m(2),status:'not_disclosed'}}},'gnpa_pct'),null);
});
test('filing identity, duplicate periods and unsafe source records are rejected', () => {
  assert.equal(institutionModel(data(),'example-bank').slug,'example-bank');
  assert.throws(()=>institutionModel(data(),'another-bank'));
  assert.throws(()=>institutionModel({...data(),sources:['javascript:alert(1)']},'example-bank'));
  assert.throws(()=>institutionModel({...data(),history:[{period_end:'2026-03-31'},{period_end:'2026-03-31'}]},'example-bank'));
});
test('history preserves missing quarters and the current record supersedes the same period', () => {
  const d=data();d.history=[{period_end:'2025-12-31',metrics:{gnpa_pct:m(1)}},{period_end:'2026-03-31',metrics:{}},{period_end:'2026-06-30',metrics:{gnpa_pct:m(9)}}];
  assert.deepEqual(bankHistory(d,'gnpa_pct').map(p=>p.y),[1,null,0]);
});
test('NPA waterfall requires complete nonnegative components and a closed reconciliation', () => {
  const d=data();d.npa_movement={status:'reconciled',amount_unit:'INR_crore',period_start:'2026-04-01',period_end:'2026-06-30',rounding_tolerance:.01,opening_gnpa:100,additions:30,closing_gnpa:80,reductions:{upgrades:10,cash_recoveries:20,write_offs:20,other_reductions:0}};
  assert.equal(movementRows(d).at(-1).end,80); assert.equal(movementRows(d).find(r=>r.label==='Cash recoveries').value,-20);
  d.npa_movement.reductions.write_offs=null; assert.deepEqual(movementRows(d),[]);
  d.npa_movement.reductions.write_offs=0; assert.deepEqual(movementRows(d),[]);
});
test('peer comparisons never pool different reporting periods or historical records', () => {
  const a=data(), b={...data(),slug:'old-bank',period_end:'2025-06-30'}, c={...data(),slug:'historic-bank',status:'historical'};
  const specs=institutionSpecs(new Map([[a.slug,a],[b.slug,b],[c.slug,c]]),{selected:a.slug,period:'2026-06-30'});
  assert.equal(specs.length,8);assert.equal(specs[0].series[0].points.length,1);assert.equal(specs[0].series[0].points[0].x,0);
  assert.equal(specs.at(-1).matrix[0].values[1],null);
});
