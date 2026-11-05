import test from 'node:test';
import assert from 'node:assert/strict';
import {validateBundle,emptyBundle,normalisePrice,seriesSummary,scenario,validatePlanning,safeURL,csv,casePack,validateCase} from '../banking/real-assets/model.mjs';
const source={id:'s1',title:'Test record',url:'https://example.org/record',published_at:'2025-01-01',retrieved_at:'2025-01-02T00:00:00Z',rights:'unknown',locator:'Page 1'};
const row={id:'o1',source_id:'s1',city_id:'jaipur',locality:'Test locality',asset_type:'land',price_basis:'asking_price',series_id:'test',comparison_basis:'same_asset',unit:'INR/sqft',value:1000,as_of:'2025-01-01',evidence_type:'declared',sample_size:1,methodology:'Same asset asking price'};
const bundle=()=>({...emptyBundle(),sources:[{...source}],observations:[{...row}]});
test('price conversion preserves index and unknown units',()=>{assert.ok(Math.abs(normalisePrice(row)-10763.9104167)<0.001);assert.equal(normalisePrice({...row,unit:'index',price_basis:'housing_index'}),null);assert.equal(normalisePrice({...row,unit:'INR/bigha'}),null);});
test('single observation cannot claim appreciation',()=>{const s=seriesSummary(bundle())[0];assert.equal(s.change_pct,null);assert.equal(s.annualised_pct,null);});
test('comparison rejects mixed price bases and duplicate dates',()=>{const b=bundle();b.observations.push({...row,id:'o2',price_basis:'registered_sale'});assert.throws(()=>validateBundle(b),/cannot mix/);b.observations[1]={...row,id:'o2'};assert.throws(()=>validateBundle(b),/Duplicate series date/);});
test('future observations and credential URLs are rejected',()=>{const b=bundle();b.observations[0].as_of='2099-01-01';assert.throws(()=>validateBundle(b),/date/);assert.equal(safeURL('https://a:secret@example.org/'),null);assert.equal(safeURL('javascript:alert(1)'),null);});
test('housing index requires housing and explicit base year',()=>{const b=bundle();Object.assign(b.observations[0],{price_basis:'housing_index',unit:'index',comparison_basis:'published_index'});assert.throws(()=>validateBundle(b),/base year/);Object.assign(b.observations[0],{asset_type:'housing',methodology:'Index base 2022-23 = 100'});assert.equal(validateBundle(b).observations[0].unit,'index');});
test('scenario accounts for exit shortfall and monthly equity costs',()=>{const s=scenario({price_inr:100,debt_inr:80,annual_appreciation_pct:-50,annual_interest_pct:12,annual_carry_pct:1,entry_cost_pct:5,exit_cost_pct:2,exit_haircut_pct:10,months:12});assert.equal(s.net_sale_inr,44.1);assert.ok(Math.abs(s.terminal_funding_shortfall_inr-35.9)<1e-8);assert.ok(Math.abs(s.equity_profit_inr+71.5)<1e-8);assert.ok(Math.abs(s.equity_returned_inr-s.equity_contributed_inr-s.equity_profit_inr)<1e-8);});
test('scenario refuses blank coerced inputs and debt above purchase',()=>{assert.throws(()=>scenario({}),/missing/);const s={price_inr:100,debt_inr:101,annual_appreciation_pct:8,annual_interest_pct:12,annual_carry_pct:1,entry_cost_pct:5,exit_cost_pct:2,exit_haircut_pct:10,months:12};assert.throws(()=>scenario(s),/Debt/);});
test('planning records cannot assert government verification',()=>{const row={district_id:'in-dist-rajasthan-jaipur',area_reference:'Test reference',document_title:'Plan',land_use:'Research note',as_of:'2025-01-01',source_url:'https://example.org/plan',notes:'',status:'approved'};assert.throws(()=>validatePlanning([row]),/researcher-recorded/);row.status='researcher_recorded';assert.equal(validatePlanning([row])[0].status,'researcher_recorded');});
test('CSV protects spreadsheet formulas and preserves source identity',()=>{const b=bundle();b.observations[0].locality='=HYPERLINK("bad")';const output=csv(b);assert.ok(output.includes("'=HYPERLINK"));assert.ok(output.includes('"source_id"'));});
test('case import uses canonical district and recalculates scenario results',()=>{
  const places=[{id:'in-dist-rajasthan-jaipur',name:'Jaipur',state:'Rajasthan',bbox:[75,26,77,28],boundary_vintage:'2021'}];
  const inputs={price_inr:100,debt_inr:0,annual_appreciation_pct:0,annual_interest_pct:0,annual_carry_pct:0,entry_cost_pct:0,exit_cost_pct:0,exit_haircut_pct:0,months:12};
  const pack=casePack({district:places[0],bundle:bundle(),places,scenarioResult:{inputs}});
  pack.district.name='Fake district';pack.district.bbox=[1,2,3,4];pack.scenario.equity_profit_inr=1e12;
  const restored=validateCase(pack,{places});assert.equal(restored.district.name,'Jaipur');assert.deepEqual(restored.district.bbox,[75,26,77,28]);assert.equal(restored.scenario.equity_profit_inr,0);
  pack.district.id='unknown';assert.throws(()=>validateCase(pack,{places}),/Unknown district/);
});
test('case cannot misattribute NASA imagery as an Indian scene',()=>{
  assert.throws(()=>casePack({district:null,bundle:emptyBundle(),imagery:{provider:'ISRO',layer:'MODIS_Terra_CorrectedReflectance_TrueColor',before:'2025-01-01',after:'2025-02-01',bbox:[75,26,77,28]}}),/NASA/);
});
