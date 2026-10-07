import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {PaymentLedger, amountPaise, validateClaim} from '../edge/payments/ledger.mjs';
import worker from '../edge/payments/worker.mjs';

function fixture(database = new DatabaseSync(':memory:')) {
  const ctx = {storage: {
    sql: {exec(query,...args) { if (!args.length && query.includes('CREATE TABLE')) { database.exec(query); return {toArray:()=>[]}; } const rows=database.prepare(query).all(...args); return {toArray:()=>rows}; }},
    transactionSync(fn) { database.exec('BEGIN'); try {const result=fn();database.exec('COMMIT');return result;} catch(error){database.exec('ROLLBACK');throw error;} }
  }};
  return {ledger:new PaymentLedger(ctx),database};
}
function claim(overrides={}) {return {product:'undertow',name:'Example Buyer',email:'buyer@example.test',invoice:'TEST-INVOICE-1',amount:'299.50',reference:'TEST123456789',paid_on:new Date().toISOString().slice(0,10),token:'a'.repeat(64),consent:true,...overrides};}
const secret='operator-test-secret-that-is-never-used-in-production';
function env(ledger) {return {PAYMENT_ADMIN_TOKEN:secret,PAYMENT_LEDGER:{idFromName:n=>n,get:()=>ledger},ASSETS:{fetch:async()=>new Response('<h1>Payments</h1>')}};}
function request(path,{method='GET',body,token,origin}={}) {return new Request('https://payments.liquilens.in'+path,{method,headers:{...(body?{'Content-Type':'application/json'}:{}),...(token?{Authorization:'Bearer '+token}:{}),...(origin?{Origin:origin}:{})},body:body?JSON.stringify(body):undefined});}
function verification(body) {return {status:'verified',reviewer:'Test operator',evidence:'Matched the test bank credit and invoice.',bank_credit_checked:true,bank_reference:body.reference,bank_amount:body.amount,bank_paid_on:body.paid_on};}

test('INR amounts use exact paise and reject rounding, zero, negatives and exponent syntax',()=>{
  assert.equal(amountPaise('299.50'),29950);assert.equal(amountPaise('1.1'),110);
  for(const value of ['0','-1','1.001','1e3','01',29,Infinity,'10000001']) assert.throws(()=>amountPaise(value));
});
test('invoices are required for purchases, not for voluntary support',()=>{
  assert.throws(()=>validateClaim(claim({invoice:''})));
  assert.equal(validateClaim(claim({product:'seiche',invoice:''})).invoice,'');
});
test('the customer cannot submit verification or an alternate currency',()=>{
  for(const extra of [{status:'verified'},{currency:'USD'},{verified_at:'today'}]) assert.throws(()=>validateClaim(claim(extra)));
  assert.throws(()=>validateClaim(claim({consent:false})));
  assert.throws(()=>validateClaim(claim({paid_on:'2026-02-30'})));
});
test('submission creates a pending record with a private status key and no customer PII in the response',async()=>{
  const {ledger,database}=fixture();const body=claim();const result=await ledger.submit(body,'ip');
  assert.equal(result.status,'pending');assert.equal(result.verified_at,null);
  assert.match(result.id,/^LLP-\d{8}-[A-F0-9]{16}$/);
  for(const key of ['email','name','reference','token','token_hash','body_hash','invoice'])assert.equal(result[key],undefined);
  assert.deepEqual(await ledger.status(body.token),result);
  assert.equal(database.prepare('SELECT token_hash FROM claims').get().token_hash.includes(body.token),false);
  await assert.rejects(()=>ledger.status('b'.repeat(64)),{status:404});
});
test('retries and concurrent requests do not create duplicate financial records',async()=>{
  const {ledger,database}=fixture();const body=claim();
  const [a,b]=await Promise.all([ledger.submit(body,'ip'),ledger.submit(body,'ip')]);assert.equal(a.id,b.id);
  assert.equal(database.prepare('SELECT count(*) AS n FROM claims').get().n,1);
  await assert.rejects(()=>ledger.submit(claim({amount:'500'}),'ip'),{status:409});
  await assert.rejects(()=>ledger.submit(claim({token:'b'.repeat(64),reference:'test123456789'}),'ip'),{status:409});
  assert.equal(database.prepare('SELECT count(*) AS n FROM audit').get().n,1);
});
test('bank reconciliation requires the matching reference, date, amount and explicit credit check',async()=>{
  const {ledger}=fixture();const body=claim();const created=await ledger.submit(body,'ip');
  for(const changes of [{bank_credit_checked:false},{bank_reference:'OTHER123456'},{bank_amount:'1.00'},{bank_paid_on:'2026-01-01'}]) assert.throws(()=>ledger.reconcile(created.id,{...verification(body),...changes}),{status:409});
  assert.equal((await ledger.status(body.token)).status,'pending');
  assert.equal(ledger.reconcile(created.id,verification(body)).status,'verified');
  assert.throws(()=>ledger.reconcile(created.id,{...verification(body),status:'needs_review'}),{status:409});
});
test('a needs-review request remains unverified and audit records are append-only',async()=>{
  const {ledger,database}=fixture();const body=claim();const created=await ledger.submit(body,'ip');
  ledger.reconcile(created.id,{status:'needs_review',reviewer:'Operator',evidence:'Invoice details need further confirmation.'});
  assert.equal((await ledger.status(body.token)).verified_at,null);
  ledger.reconcile(created.id,verification(body));
  assert.deepEqual(database.prepare('SELECT action FROM audit ORDER BY id').all().map(r=>r.action),['submitted','needs_review','verified']);
});
test('records survive recreation of the service instance',async()=>{
  const first=fixture();const result=await first.ledger.submit(claim(),'ip');
  const second=fixture(first.database);assert.equal((await second.ledger.status(claim().token)).id,result.id);
});
test('the eleventh new submission from the same client is limited, while its saved record can still be read',async()=>{
  const {ledger}=fixture();for(let i=0;i<10;i++)await ledger.submit(claim({token:i.toString(16).padStart(64,'0'),reference:'TEST000000'+i}),'ip');
  await assert.rejects(()=>ledger.submit(claim(),'ip'),{status:429});
  assert.equal((await ledger.status('0'.repeat(64))).status,'pending');
});
test('HTTP API requires same-origin submissions, bounds payloads and fails closed without administration',async()=>{
  const {ledger}=fixture();
  assert.equal((await worker.fetch(request('/api/claims',{method:'POST',body:claim(),origin:'https://evil.example'}),env(ledger))).status,403);
  assert.equal((await worker.fetch(request('/api/claims',{method:'POST',body:claim(),origin:'https://payments.liquilens.in'}),env(ledger))).status,200);
  assert.equal((await worker.fetch(request('/api/claims',{method:'POST',body:claim({name:'x'.repeat(9000)}),origin:'https://payments.liquilens.in'}),env(ledger))).status,413);
  assert.equal((await worker.fetch(request('/api/health'),{...env(ledger),PAYMENT_ADMIN_TOKEN:undefined})).status,503);
});
test('administrator routes reject unauthenticated and browser-origin requests',async()=>{
  const {ledger}=fixture();const e=env(ledger);
  assert.equal((await worker.fetch(request('/api/admin/pending'),e)).status,401);
  assert.equal((await worker.fetch(request('/api/admin/pending',{token:secret,origin:'https://payments.liquilens.in'}),e)).status,403);
  assert.equal((await worker.fetch(request('/api/admin/pending',{token:secret}),e)).status,200);
  const body=claim();const record=await ledger.submit(body,'ip');
  assert.equal((await worker.fetch(request('/api/admin/reconcile',{method:'POST',body:{id:record.id,...verification(body)},token:'wrong'}),e)).status,401);
  assert.equal((await ledger.status(body.token)).status,'pending');
});
test('private status uses a bearer key, rejects tokens in query strings and never permits browser embedding',async()=>{
  const {ledger}=fixture();await ledger.submit(claim(),'ip');const e=env(ledger);
  const response=await worker.fetch(request('/api/status',{token:claim().token}),e);
  assert.equal(response.status,200);assert.equal(response.headers.get('Cache-Control'),'no-store');
  assert.equal(response.headers.get('Referrer-Policy'),'no-referrer');assert.equal(response.headers.get('Access-Control-Allow-Origin'),null);
  assert.match(response.headers.get('Content-Security-Policy'),/frame-ancestors 'none'/);
  assert.equal((await worker.fetch(request('/api/status?token='+claim().token),e)).status,400);
  assert.equal((await worker.fetch(request('/api/status'),e)).status,404);
});
