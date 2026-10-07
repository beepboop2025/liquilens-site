(function () {
  'use strict';
  const form = document.getElementById('payment-form');
  const product = document.getElementById('product');
  const invoice = document.getElementById('invoice');
  const button = document.getElementById('submit-payment');
  const status = document.getElementById('form-status');
  const selected = new URLSearchParams(location.search).get('product');
  if (['liquilens','undertow','seiche'].includes(selected)) product.value = selected;
  function updateInvoice() {
    invoice.required = product.value !== 'seiche';
    document.getElementById('invoice-hint').textContent = invoice.required ? '(required)' : '(optional for support)';
  }
  updateInvoice(); product.addEventListener('change', updateInvoice);
  const today = new Date();
  document.getElementById('paid-on').value = new Date(today.getTime() - today.getTimezoneOffset() * 60000).toISOString().slice(0,10);
  let attempt = null;
  button.disabled = false;
  form.addEventListener('submit', async function (event) {
    event.preventDefault(); if (!form.reportValidity()) return;
    const data = Object.fromEntries(new FormData(form)); data.consent = data.consent === 'on';
    const fingerprint = JSON.stringify(data);
    if (!attempt || attempt.fingerprint !== fingerprint) attempt = {fingerprint, token: [...crypto.getRandomValues(new Uint8Array(32))].map(b => b.toString(16).padStart(2,'0')).join('')};
    button.disabled = true; status.classList.remove('error'); status.textContent = 'Saving your payment details…';
    try {
      const response = await fetch('/api/claims', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...data,token:attempt.token}),signal:AbortSignal.timeout(20000)});
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Unable to confirm submission. Try again with the same details or contact support.');
      document.getElementById('ack-id').textContent = result.id;
      document.getElementById('status-link').href = '/status.html#' + attempt.token;
      const receipt = document.getElementById('acknowledgement'); receipt.hidden = false; receipt.focus();
      form.hidden = true;
      // The private link becomes the address immediately, so a reload cannot lose a saved acknowledgement.
      location.assign('/status.html#' + attempt.token);
    } catch (error) {
      status.classList.add('error');
      status.textContent = error.name === 'TimeoutError' || error instanceof TypeError ? 'We could not confirm whether your details were saved. Retry with the same details; the submission key is preserved to prevent duplicates. You can also contact mrinal@liquilens.in.' : error.message;
    } finally { button.disabled = false; }
  });
}());
