#!/usr/bin/env python3
"""Review submitted references and reconcile actual bank credits. Never moves money."""
import argparse
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['pending', 'verify', 'needs-review'])
    parser.add_argument('--id')
    parser.add_argument('--reviewer')
    parser.add_argument('--evidence', help='Brief record of the actual bank and invoice checks; do not include credentials')
    parser.add_argument('--bank-reference')
    parser.add_argument('--bank-amount', help='Exact INR bank credit, such as 299.50')
    parser.add_argument('--bank-paid-on', help='Payment date YYYY-MM-DD')
    parser.add_argument('--bank-credit-checked', action='store_true')
    parser.add_argument('--token-file', type=Path, default=Path.home()/'.config/liquilens-payments/admin-token')
    args = parser.parse_args()
    token = os.environ.get('LIQUILENS_PAYMENT_ADMIN_TOKEN') or args.token_file.read_text().strip()
    if len(token) < 32:
        parser.error('A dedicated payment administrator token is required.')
    url = 'https://payments.liquilens.in/api/admin/'
    payload = None
    if args.action == 'pending':
        url += 'pending'
    else:
        if not all([args.id, args.reviewer, args.evidence]):
            parser.error('--id, --reviewer and --evidence are required.')
        if args.action == 'verify' and not all([args.bank_reference, args.bank_amount, args.bank_paid_on, args.bank_credit_checked]):
            parser.error('Verify only after matching the real bank credit: supply --bank-reference, --bank-amount, --bank-paid-on and --bank-credit-checked.')
        url += 'reconcile'
        payload = json.dumps({'id': args.id, 'status': 'verified' if args.action == 'verify' else 'needs_review',
            'reviewer': args.reviewer, 'evidence': args.evidence, 'bank_reference': args.bank_reference,
            'bank_amount': args.bank_amount, 'bank_paid_on': args.bank_paid_on,
            'bank_credit_checked': args.bank_credit_checked}).encode()
    req = urllib.request.Request(url, data=payload, headers={'Authorization': 'Bearer '+token, 'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            print(json.dumps(json.load(response), indent=2))
    except urllib.error.HTTPError as error:
        print(error.read().decode())
        raise SystemExit(1)

if __name__ == '__main__':
    main()
