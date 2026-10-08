import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {monitorModel, monitorDetail, monitorRows, monitorCSVRows} from '../research-ui/monitor-model.mjs';
import {csv} from '../research-ui/core.mjs';

const today='2026-10-08';
const authority={score_authority:false,training_eligible:false,can_authorize_credit:false,human_review_required:true};
const categories=['asset_quality','deposits','refinancing','liquidity','capital','governance','exposures'].map(id=>({id,label:id,status:'insufficient_visibility'}));
const row=()=>({slug:'example-bank',name:'Example Bank',institution_type:'bank',status:'insufficient_visibility',priority:'evidence_review',latest_period:'2026-03-31',categories:structuredClone(categories),warnings:[],gaps:[{field:'withdrawals',reason:'No reviewed withdrawal data',status:'unavailable'}],coverage_complete:false,content_sha256:'a'.repeat(64),current_metrics:0,overdue_metrics:2,review_url:'/api/experimental/v1/banking/monitoring/institutions/example-bank'});
const payload=()=>({schema:'liquilens.institution-monitoring.v1',policy_version:'liquilens.institution-monitoring-policy.v1',as_of:today,watchlist_basis:'All tracked Indian institution records',rows:[row()],not_covered:[],counts:{tracked:1,selected:1,with_current_reviewed_metrics:0,with_visibility_gaps:1,with_deterioration:0},coverage_complete:false,delivery:{status:'review_queue_only',customer_delivery_verified:false},...authority});
const detail=()=>({...payload(),...row(),metrics:[{label:'Gross NPA',unit:'percent',period_end:'2026-03-31',status:'current',value:0,sources:['https://example.org/filing.pdf']}],validation:{historical_prediction_validated:false}});

test('missing evidence stays visible even with no deterioration warning',()=>{
  const model=monitorModel(payload(),today);
  assert.equal(model.rows.length,1);assert.equal(model.counts.current,0);assert.equal(model.counts.gaps,1);
  assert.equal(model.coverageComplete,false);assert.equal(model.rows[0].status,'insufficient_visibility');
});
test('a truncated or caller-selected response cannot present whole-register totals',()=>{
  for(const mutate of [d=>d.rows=[],d=>d.counts.tracked=59,d=>d.not_covered=['missing-bank'],d=>d.watchlist_basis='Caller-selected exact institution slugs',d=>d.counts.with_visibility_gaps=0,d=>d.counts.with_current_reviewed_metrics=1,d=>d.counts.with_deterioration=1]){
    const d=payload();mutate(d);assert.throws(()=>monitorModel(d,today));
  }
});
test('authority changes, absent gates and unknown policies fail closed',()=>{
  for(const key of Object.keys(authority)){
    const changed=payload();changed[key]=!changed[key];assert.throws(()=>monitorModel(changed,today));
    const absent=payload();delete absent[key];assert.throws(()=>monitorModel(absent,today));
  }
  const d=payload();d.policy_version='new-policy';assert.throws(()=>monitorModel(d,today));
});
test('counts do not turn empty, boolean or duplicate records into coverage',()=>{
  const d=payload();d.rows[0].current_metrics=true;assert.throws(()=>monitorModel(d,today));
  const duplicated=payload();duplicated.rows.push(row());duplicated.counts.tracked=2;duplicated.counts.selected=2;assert.throws(()=>monitorModel(duplicated,today));
  const empty=payload();empty.rows=[];for(const key of Object.keys(empty.counts))empty.counts[key]=0;
  assert.equal(monitorModel(empty,today).coverageComplete,false);
  empty.coverage_complete=true;assert.throws(()=>monitorModel(empty,today));
});
test('unknown evidence states and contradictory complete coverage are rejected',()=>{
  for(const mutate of [d=>d.rows[0].status='safe',d=>d.rows[0].priority='approved',d=>d.rows[0].coverage_complete=true,d=>d.rows[0].categories[0].status='safe',d=>d.rows[0].gaps[0].status='restricted',d=>d.rows[0].warnings=[{kind:'credit_approval',title:'Approved'}]]){
    const d=payload();mutate(d);assert.throws(()=>monitorModel(d,today));
  }
});
test('review cutoff cannot be malformed or future dated',()=>{
  for(const cutoff of ['2026-02-30','2026-10-09',null,'today']){const d=payload();d.as_of=cutoff;assert.throws(()=>monitorModel(d,today));}
});
test('historic records remain historic under the review-priority filter',()=>{
  const d=payload();d.rows[0].status='historical';d.rows[0].priority='historical_archive';
  const m=monitorModel(d,today);assert.equal(monitorRows(m,{priority:'historical_archive'}).length,1);
  assert.equal(monitorRows(m,{priority:'urgent_review'}).length,0);
});
test('search, type and priority narrow records without changing aggregate coverage',()=>{
  const m=monitorModel(payload(),today);assert.equal(monitorRows(m,{query:'EXAMPLE bank',type:'bank'}).length,1);
  assert.equal(monitorRows(m,{query:'other'}).length,0);assert.equal(m.counts.tracked,1);
});
test('selected record binds its exact identity, cutoff and content to the loaded list',()=>{
  assert.equal(monitorDetail(detail(),row(),today,today).slug,'example-bank');
  for(const mutate of [d=>d.slug='other-bank',d=>d.as_of='2026-10-07',d=>d.content_sha256='b'.repeat(64),d=>d.can_authorize_credit=true,d=>d.validation.historical_prediction_validated=true]){
    const d=detail();mutate(d);assert.throws(()=>monitorDetail(d,row(),today,today));
  }
});
test('zero and source holds survive while invalid numbers and unsafe URLs fail closed',()=>{
  const d=detail();assert.equal(monitorDetail(d,row(),today,today).metrics[0].value,0);
  d.metrics[0].status='source_review_hold';assert.equal(monitorDetail(d,row(),today,today).metrics[0].status,'source_review_hold');
  for(const mutate of [d=>d.metrics[0].value='0',d=>d.metrics[0].value=Infinity,d=>d.metrics[0].sources=['javascript:alert(1)'],d=>d.metrics[0].sources=['https://user:secret@example.org/']]){
    const bad=detail();mutate(bad);assert.throws(()=>monitorDetail(bad,row(),today,today));
  }
});
test('exports retain cutoff, gaps and source links and neutralize spreadsheet formulas',()=>{
  const d=payload();d.rows[0].name='=malicious()';const m=monitorModel(d,today);
  const output=csv(monitorCSVRows(m));assert.ok(output.includes("'=malicious()"));assert.ok(output.includes('?as_of=2026-10-08'));assert.ok(output.includes('Visibility gaps'));
});
test('the retained public register is compatible when supplied for acceptance',()=>{
  if(!process.env.MONITOR_ACCEPTANCE_FIXTURE)return;
  const d=JSON.parse(readFileSync(process.env.MONITOR_ACCEPTANCE_FIXTURE,'utf8'));
  const m=monitorModel(d,d.as_of);assert.equal(m.rows.length,d.counts.tracked);
});
