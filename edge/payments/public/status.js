(function () {
  'use strict';
  const token = location.hash.slice(1);
  const message = document.getElementById('status-message');
  const refresh = document.getElementById('refresh-status');
  const formatDate = value => new Date(value).toLocaleString(undefined, {dateStyle:'medium',timeStyle:'short'});
  async function load() {
    if (!/^[a-f0-9]{64}$/.test(token)) { message.textContent = 'Open the complete private status link from your acknowledgement. For help, email mrinal@liquilens.in.'; refresh.hidden = true; return; }
    refresh.disabled = true; message.classList.remove('error');
    try {
      const response = await fetch('/api/status', {headers:{Authorization:'Bearer '+token},cache:'no-store',signal:AbortSignal.timeout(15000)});
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Status is unavailable. Try again or contact support.');
      const verified = result.status === 'verified';
      const labels = {pending:'Awaiting bank verification',needs_review:'Additional information needed',verified:'Payment verified'};
      document.getElementById('receipt-status').textContent = labels[result.status] || 'Status unavailable';
      document.getElementById('receipt-status').classList.toggle('verified',verified);
      document.getElementById('receipt-title').textContent = verified ? 'Payment receipt' : 'Payment acknowledgement';
      for (const [id,value] of Object.entries({'receipt-id':result.id,'receipt-product':{liquilens:'LiquiLens',undertow:'Undertow',seiche:'Seiche voluntary support'}[result.product],'receipt-amount':new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR'}).format(result.amount_paise/100),'receipt-reference':'Ending '+result.reference_ending,'receipt-date':result.paid_on,'receipt-submitted':formatDate(result.submitted_at),'receipt-verified':result.verified_at?formatDate(result.verified_at):''})) document.getElementById(id).textContent = value;
      document.getElementById('verified-row').hidden = !verified;
      document.getElementById('receipt-boundary').textContent = verified ? 'This confirms receipt of the matched bank credit. It is not a tax invoice. Product access and delivery follow your agreed invoice; voluntary support does not purchase access.' : 'This acknowledges submitted payment details only. Bank receipt is not yet confirmed and no paid access has been activated by this submission.';
      message.textContent = result.message;
      document.getElementById('receipt').hidden = false;
      document.getElementById('print-receipt').hidden = false;
      document.getElementById('copy-status').hidden = false;
    } catch (error) { message.classList.add('error'); message.textContent = 'Could not refresh payment status. '+(error.name==='TimeoutError'?'Please try again.':error.message); }
    finally { refresh.disabled = false; }
  }
  refresh.addEventListener('click',load);
  document.getElementById('print-receipt').addEventListener('click',()=>window.print());
  document.getElementById('copy-status').addEventListener('click',async()=>{
    const input=document.getElementById('private-link'); input.value=location.origin+'/status.html#'+token;
    try { await navigator.clipboard.writeText(input.value); document.getElementById('copy-message').textContent='Private status link copied. Keep it confidential.'; }
    catch { input.hidden=false; input.focus(); input.select(); document.getElementById('copy-message').textContent='Select and copy the private link below.'; }
  });
  load();
}());
