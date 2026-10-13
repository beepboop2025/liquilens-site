import test from 'node:test';
import assert from 'node:assert/strict';
import {parseRequest, assessment, post} from '../agents/correlation/model.mjs';

test('request parsing requires an assessment clock and rejects oversized input',()=>{
  assert.throws(()=>parseRequest('{'),/valid JSON/);
  assert.throws(()=>parseRequest('{"series":[]}'),/as_of/);
  assert.throws(()=>parseRequest('x'.repeat(750001)),/750 KB/);
});
test('a blocked panel retains reasons and cannot display usable latest metrics',()=>{
  const result=assessment({schema:'noisefloor.spectral-assessment.v1',execution_authority:false,
    series:[{id:'restricted',reasons:['source_rights_not_permitted']}],windows:[],
    reasons:['one_or_more_series_ineligible'],latest:null});
  assert.equal(result.latest,null);
  assert.deepEqual(result.reasons,['one_or_more_series_ineligible','restricted: source_rights_not_permitted']);
  assert.throws(()=>assessment({schema:'unknown'}),/contract/);
});
test('HTTP errors stay errors; public requests omit credentials',async()=>{
  await assert.rejects(post('/v1/spectral/assess',{},async(_url,options)=>{
    assert.equal(options.credentials,'omit');
    return {ok:false,status:400,json:async()=>({error:'ineligible request'})};
  }),/400: ineligible request/);
});

test('hosted requests use reviewed routes and explicit synthetic attribution',async()=>{
  const calls=[];
  const fetcher=async(url,options)=>{calls.push({url,options});return {ok:true,json:async()=>({status:'synthetic'})};};
  await post('/v1/spectral/assess',{},fetcher);
  await post('/v1/research/dyson',{},fetcher,{synthetic:true});
  assert.equal(calls[0].url,'https://agents.seiche.info/v1/noisefloor/v1/spectral/assess');
  assert.equal(calls[0].options.headers['X-Financial-Evidence-Traffic-Class'],undefined);
  assert.equal(calls[1].options.headers['X-Financial-Evidence-Traffic-Class'],'synthetic');
  for(const {options} of calls){assert.equal(options.redirect,'error');assert.equal(options.credentials,'omit');}
  await assert.rejects(post('/unknown',{},fetcher),/Unsupported/);
  await assert.rejects(post('/v1/spectral/assess',{text:'x'.repeat(750001)},fetcher),/750 KB/);
  assert.equal(calls.length,2);
});
