# Company bank-payment confirmations

`payments.liquilens.in` receives payment **references**, never initiates a transfer.
The supplied IDFC QR and statement establish the published beneficiary details.
The bank statement itself and its balances/transactions must never enter a public artifact.

Customers receive a durable acknowledgement and a private status link. Only the
dedicated administrator API can mark a claim verified, after matching the bank
credit, UTR, amount, date, payer and agreed invoice. No subscription is activated
by this service. It sends no automatic email; support uses the submitted email
when further information or fulfilment confirmation is needed.

The status token is 256 random bits, stored only as a hash in the ledger. The
customer link carries it in the fragment; API requests use a bearer header.
Status responses omit name, email, invoice and full transaction reference.
There are no analytics, third-party scripts, receipt uploads or public searches.
Records and append-only reconciliation events use SQLite Durable Object storage.
Cloudflare's storage recovery is separate from bank reconciliation.

## Operate

Use a dedicated random administrator token, at least 32 characters. Keep it in
`~/.config/liquilens-payments/admin-token` (mode 0600) and the Worker's
`PAYMENT_ADMIN_TOKEN` secret. Never commit it or put it in a command argument.
Submissions fail closed until the secret and durable storage are configured.

```sh
python3 scripts/payment_admin.py pending
```

Review the actual company bank credit, payer and agreed invoice before running:

```sh
python3 scripts/payment_admin.py verify --id ACKNOWLEDGEMENT \
  --reviewer 'Reviewer name' --bank-reference BANK_UTR \
  --bank-amount EXACT_INR_AMOUNT --bank-paid-on YYYY-MM-DD \
  --bank-credit-checked --evidence 'Bank credit, payer and invoice matched in the bank account'
```

If the match is incomplete, use `needs-review` with `--id`, `--reviewer` and
`--evidence`, then contact the customer. A screenshot or submitted reference
alone cannot establish receipt. Verified rows cannot be overwritten. Refunds
and access fulfilment follow the separate invoice/support process.

## Verify and publish

```sh
node --test tests/test_payment_ledger.mjs
npx --no-install wrangler deploy --config wrangler.payments.jsonc --dry-run
```

Publish this independent Worker from reviewed source. Do not redeploy the catalog
Worker to publish payments. Configure the secret through stdin using
`wrangler secret put PAYMENT_ADMIN_TOKEN --config wrangler.payments.jsonc`.
Prove `/api/health`, rejection of invalid or unauthenticated API requests,
the asset hashes and private-page security headers after publication. Do not
create a synthetic production claim or mark a payment verified without a bank credit.
The durable namespace and migration name must remain stable on subsequent deploys.
