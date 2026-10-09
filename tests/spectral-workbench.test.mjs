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
