export class PaymentError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}
const fail = (status, message) => { throw new PaymentError(status, message); };
const PRODUCTS = new Set(['liquilens', 'undertow', 'seiche']);
const TOKEN = /^[a-f0-9]{64}$/;
export async function digest(text) {
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text)))].map(b => b.toString(16).padStart(2, '0')).join('');
}
function text(value, min, max, label) {
  if (typeof value !== 'string' || /[\x00-\x1f\x7f]/.test(value) || value.trim().length < min || value.trim().length > max) fail(400, `Enter a valid ${label}.`);
  return value.trim();
}
export function amountPaise(value) {
  if (typeof value !== 'string' || !/^(0|[1-9]\d{0,7})(\.\d{1,2})?$/.test(value)) fail(400, 'Enter the INR amount using at most two decimal places.');
  const [rupees, paise = ''] = value.split('.');
  const result = Number(rupees) * 100 + Number(paise.padEnd(2, '0'));
  if (!Number.isSafeInteger(result) || result < 100 || result > 1000000000) fail(400, 'The amount must be between INR 1 and INR 10,000,000. Contact support for other amounts.');
  return result;
}
export function reference(value) {
  const ref = text(value, 6, 40, 'UPI transaction ID or bank UTR').replace(/[ -]/g, '').toUpperCase();
  if (!/^[A-Z0-9]{6,35}$/.test(ref)) fail(400, 'Use the transaction ID or UTR from your payment receipt.');
  return ref;
}
export function validateClaim(body, now = new Date()) {
  const allowed = new Set(['product', 'name', 'email', 'invoice', 'amount', 'reference', 'paid_on', 'token', 'consent']);
  if (!body || Array.isArray(body) || typeof body !== 'object' || Object.keys(body).some(k => !allowed.has(k))) fail(400, 'Invalid payment submission.');
  if (!PRODUCTS.has(body.product) || typeof body.token !== 'string' || !TOKEN.test(body.token) || body.consent !== true) fail(400, 'Choose a product and agree to payment verification.');
  const email = text(body.email, 3, 254, 'email address').toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) fail(400, 'Enter a valid email address.');
  const day = text(body.paid_on, 10, 10, 'payment date');
  const parsed = new Date(day + 'T00:00:00Z');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day) || !Number.isFinite(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== day || parsed > new Date(now.getTime() + 86400000) || now - parsed > 366 * 86400000) fail(400, 'Enter a payment date within the last year.');
  return {product: body.product, name: text(body.name, 2, 100, 'payer name'), email,
    invoice: text(body.invoice || '', body.product === 'seiche' ? 0 : 1, 80, 'invoice reference'),
    amount_paise: amountPaise(body.amount), reference: reference(body.reference), paid_on: day};
}
export function customerRecord(row) {
  return {id: row.id, product: row.product, amount_paise: row.amount_paise, currency: 'INR',
    reference_ending: row.reference.slice(-4), paid_on: row.paid_on, status: row.status,
    submitted_at: row.submitted_at, verified_at: row.verified_at || null,
    message: row.status === 'verified' ? 'Payment verified against the company bank account. Contact us with this reference for invoice or delivery help.' : row.status === 'needs_review' ? 'We need more information to match this transfer. Contact mrinal@liquilens.in with your acknowledgement number.' : 'Payment details received. Bank verification is pending. No paid access has been activated by this submission.'};
}
export class PaymentLedger {
  constructor(ctx) {
    this.ctx = ctx;
    this.sql = ctx.storage.sql;
    this.sql.exec(`CREATE TABLE IF NOT EXISTS claims (
      id TEXT PRIMARY KEY, token_hash TEXT NOT NULL UNIQUE, body_hash TEXT NOT NULL,
      product TEXT NOT NULL, name TEXT NOT NULL, email TEXT NOT NULL, invoice TEXT NOT NULL,
      amount_paise INTEGER NOT NULL CHECK(amount_paise > 0), reference TEXT NOT NULL UNIQUE,
      paid_on TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('pending','needs_review','verified')),
      submitted_at TEXT NOT NULL, verified_at TEXT);
      CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, claim_id TEXT NOT NULL, action TEXT NOT NULL, actor TEXT NOT NULL, evidence TEXT NOT NULL, at TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS limits (key TEXT PRIMARY KEY, count INTEGER NOT NULL, expires INTEGER NOT NULL);`);
  }
  one(query, ...args) { return this.sql.exec(query, ...args).toArray()[0]; }
  async submit(body, ipHash) {
    const claim = validateClaim(body);
    const tokenHash = await digest(body.token);
    const bodyHash = await digest(JSON.stringify(claim));
    // All reads and writes below are synchronous in one transaction: concurrent retries cannot duplicate a claim.
    return this.ctx.storage.transactionSync(() => {
      const existing = this.one('SELECT * FROM claims WHERE token_hash = ?', tokenHash);
      if (existing) {
        if (existing.body_hash !== bodyHash) fail(409, 'This submission key already belongs to different details. Use your existing status link or start a new submission.');
        return customerRecord(existing);
      }
      const now = Date.now();
      this.sql.exec('DELETE FROM limits WHERE expires < ?', now);
      const key = ipHash + ':' + Math.floor(now / 3600000);
      if ((this.one('SELECT count FROM limits WHERE key = ?', key)?.count || 0) >= 10) fail(429, 'Too many submissions. Try again later or email support.');
      if (this.one('SELECT id FROM claims WHERE reference = ?', claim.reference)) fail(409, 'This transaction reference has already been submitted. Use your saved status link or contact support.');
      const id = 'LLP-' + new Date(now).toISOString().slice(0, 10).replaceAll('-', '') + '-' + crypto.randomUUID().replaceAll('-', '').slice(0, 16).toUpperCase();
      const row = {...claim, id, status: 'pending', submitted_at: new Date(now).toISOString(), verified_at: null};
      this.sql.exec('INSERT INTO claims VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', id, tokenHash, bodyHash, claim.product, claim.name, claim.email, claim.invoice, claim.amount_paise, claim.reference, claim.paid_on, 'pending', row.submitted_at, null);
      this.sql.exec('INSERT INTO audit (claim_id,action,actor,evidence,at) VALUES (?,?,?,?,?)', id, 'submitted', 'customer', 'Reference submitted; bank credit not verified', row.submitted_at);
      this.sql.exec('INSERT INTO limits VALUES (?,1,?) ON CONFLICT(key) DO UPDATE SET count = count + 1', key, now + 3600000);
      return customerRecord(row);
    });
  }
  async status(token) {
    if (!TOKEN.test(token || '')) fail(404, 'Payment reference not found. Use your complete private status link.');
    const row = this.one('SELECT * FROM claims WHERE token_hash = ?', await digest(token));
    if (!row) fail(404, 'Payment reference not found. Use your complete private status link.');
    return customerRecord(row);
  }
  reconcile(id, body) {
    if (!body || !['verified','needs_review'].includes(body.status)) fail(400, 'Choose verified or needs_review.');
    const actor = text(body.reviewer, 2, 100, 'reviewer');
    const evidence = text(body.evidence, 12, 500, 'bank reconciliation evidence');
    return this.ctx.storage.transactionSync(() => {
      const row = this.one('SELECT * FROM claims WHERE id = ?', id);
      if (!row) fail(404, 'Unknown acknowledgement number.');
      if (row.status === 'verified') fail(409, 'This payment is already verified; the audit record cannot be overwritten.');
      if (body.status === 'verified' && (body.bank_credit_checked !== true || reference(body.bank_reference) !== row.reference || amountPaise(body.bank_amount) !== row.amount_paise || body.bank_paid_on !== row.paid_on)) fail(409, 'The bank credit, reference, amount and payment date must match before verification.');
      const at = new Date().toISOString();
      this.sql.exec('UPDATE claims SET status = ?, verified_at = ? WHERE id = ?', body.status, body.status === 'verified' ? at : null, id);
      this.sql.exec('INSERT INTO audit (claim_id,action,actor,evidence,at) VALUES (?,?,?,?,?)', id, body.status, actor, evidence, at);
      return customerRecord({...row, status: body.status, verified_at: body.status === 'verified' ? at : null});
    });
  }
  async fetch(request) {
    try {
      const url = new URL(request.url);
      let result;
      if (url.pathname === '/submit') result = await this.submit(await request.json(), request.headers.get('X-Client-Hash') || 'unknown');
      else if (url.pathname === '/status') result = await this.status(request.headers.get('Authorization')?.replace(/^Bearer /, ''));
      else if (url.pathname === '/pending') result = {claims: this.sql.exec("SELECT id,product,name,email,invoice,amount_paise,reference,paid_on,status,submitted_at FROM claims WHERE status != 'verified' ORDER BY submitted_at LIMIT 100").toArray()};
      else if (url.pathname === '/reconcile') { const body = await request.json(); result = this.reconcile(body.id, body); }
      else if (url.pathname === '/health') result = {storage: this.one('SELECT 1 AS ok').ok === 1 ? 'ready' : 'unavailable'};
      else fail(404, 'Not found.');
      return Response.json(result);
    } catch (error) {
      return Response.json({error: error instanceof PaymentError ? error.message : 'Unable to save or read payment details. Please try again or contact support.'}, {status: error instanceof PaymentError ? error.status : 503});
    }
  }
}
