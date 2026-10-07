import {digest, PaymentError} from './ledger.mjs';
export {PaymentLedger} from './ledger.mjs';

const HEADERS = {
  'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; base-uri 'none'; object-src 'none'; form-action 'self'; frame-ancestors 'none'",
  'Referrer-Policy': 'no-referrer', 'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY',
  'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=()',
  'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex, nofollow',
};
function secure(response) {
  const headers = new Headers(response.headers);
  for (const [key, value] of Object.entries(HEADERS)) headers.set(key, value);
  return new Response(response.body, {status: response.status, headers});
}
async function boundedJson(request) {
  if (!request.headers.get('Content-Type')?.startsWith('application/json')) throw new PaymentError(415, 'Send JSON payment details.');
  const reader = request.body?.getReader();
  if (!reader) throw new PaymentError(400, 'Payment details are missing.');
  let size = 0; const parts = [];
  while (true) {
    const {done, value} = await reader.read(); if (done) break;
    size += value.byteLength;
    if (size > 8192) { await reader.cancel(); throw new PaymentError(413, 'Payment details are too large.'); }
    parts.push(value);
  }
  const bytes = new Uint8Array(size); let at = 0;
  for (const part of parts) { bytes.set(part, at); at += part.length; }
  try { return JSON.parse(new TextDecoder().decode(bytes)); } catch { throw new PaymentError(400, 'Invalid payment details.'); }
}
async function isAdmin(request, secret) {
  if (typeof secret !== 'string' || secret.length < 32) return false;
  const supplied = request.headers.get('Authorization')?.replace(/^Bearer /, '') || '';
  if (supplied.length > 256) return false;
  const a = await digest(supplied); const b = await digest(secret);
  let different = 0; for (let i = 0; i < a.length; i++) different |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return different === 0;
}
export default {
  async fetch(request, env) {
    try {
      const url = new URL(request.url);
      if (!url.pathname.startsWith('/api/')) return secure(await env.ASSETS.fetch(request));
      if (url.search) throw new PaymentError(400, 'Use the payment portal without API query parameters.');
      if (!env.PAYMENT_LEDGER || !env.PAYMENT_ADMIN_TOKEN || env.PAYMENT_ADMIN_TOKEN.length < 32) throw new PaymentError(503, 'Payment-reference submissions are temporarily unavailable. Email mrinal@liquilens.in for help.');
      const ledger = env.PAYMENT_LEDGER.get(env.PAYMENT_LEDGER.idFromName('idfc-inr-v1'));
      let target; let body; const headers = new Headers();
      if (url.pathname === '/api/health' && request.method === 'GET') target = '/health';
      else if (url.pathname.startsWith('/api/admin/')) {
        if (!await isAdmin(request, env.PAYMENT_ADMIN_TOKEN)) throw new PaymentError(401, 'Administrator authentication required.');
        if (request.headers.has('Origin')) throw new PaymentError(403, 'Use the authenticated operator command for reconciliation.');
        if (url.pathname === '/api/admin/pending' && request.method === 'GET') target = '/pending';
        else if (url.pathname === '/api/admin/reconcile' && request.method === 'POST') { target = '/reconcile'; body = await boundedJson(request); }
      } else if (url.pathname === '/api/claims' && request.method === 'POST') {
        if (request.headers.get('Origin') !== url.origin) throw new PaymentError(403, 'Submit payment details from the company payment portal.');
        body = await boundedJson(request); target = '/submit';
        headers.set('X-Client-Hash', await digest(env.PAYMENT_ADMIN_TOKEN + ':' + (request.headers.get('CF-Connecting-IP') || 'local')));
      } else if (url.pathname === '/api/status' && request.method === 'GET') {
        if (request.headers.has('Origin') && request.headers.get('Origin') !== url.origin) throw new PaymentError(403, 'Open your private company status link.');
        target = '/status'; headers.set('Authorization', request.headers.get('Authorization') || '');
      }
      if (!target) throw new PaymentError(404, 'Not found.');
      if (body) headers.set('Content-Type', 'application/json');
      return secure(await ledger.fetch(new Request('https://ledger.internal' + target, {method: body ? 'POST' : 'GET', headers, body: body ? JSON.stringify(body) : undefined})));
    } catch (error) {
      return secure(Response.json({error: error instanceof PaymentError ? error.message : 'The payment service is temporarily unavailable. Contact mrinal@liquilens.in.'}, {status: error instanceof PaymentError ? error.status : 503}));
    }
  }
};
