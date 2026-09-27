import copy
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from scripts import build_bank_evidence as bank

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def snapshot():
    return json.loads((ROOT/'banking/institutions/au-sfb/evidence.json').read_text())


def reseal(snapshot):
    snapshot['source_payload_sha256'] = bank.digest(snapshot['evidence'])
    return snapshot


def test_committed_cut_reproduces_and_every_snapshot_is_discoverable():
    bank.build(ROOT, check=True)
    manifest = json.loads((ROOT/'banking/institutions/manifest.json').read_text())
    sitemap = ET.fromstring((ROOT/'sitemap.xml').read_text())
    urls = [n.text for n in sitemap.iter() if n.tag.endswith('}loc')]
    for row in manifest['records']:
        assert urls.count(bank.SITE + bank.PREFIX + row['slug'] + '/') == 1


def test_snapshot_preserves_clocks_and_source_identity(snapshot):
    page = bank.render_record(snapshot)
    for value in [snapshot['captured_at'], snapshot['source_payload_sha256'], snapshot['evidence']['period_end'], snapshot['evidence']['available_at'], snapshot['evidence']['publication_date']]:
        assert value in page
    assert 'Source document SHA-256' in page
    assert 'dated snapshot, not a live bank-health assessment' in page


def test_missing_is_not_zero_and_values_keep_precision():
    assert bank.metric_value({'value':None, 'status':'not_disclosed'}) == 'Not disclosed / unavailable'
    assert bank.metric_value({'value':0, 'status':'observed', 'unit':'percent'}) == '0%'
    assert bank.metric_value({'value':123456789.123, 'status':'observed', 'unit':'INR_crore'}) == '123,456,789.123 INR crore'


def test_digest_mismatch_is_refused(snapshot):
    snapshot['evidence']['metrics']['gnpa_pct']['value'] = 0
    with pytest.raises(ValueError, match='digest'):
        bank.render_record(snapshot)


def test_institution_identity_and_authority_are_not_promoted(snapshot):
    with pytest.raises(ValueError, match='identity'):
        bank.validate(snapshot['evidence'], 'different-bank')
    snapshot['evidence']['score_authority'] = True
    with pytest.raises(ValueError, match='authority'):
        bank.render_record(reseal(snapshot))


def test_markup_and_source_links_are_safe(snapshot):
    snapshot['evidence']['name'] = '</script><img src=x onerror=alert(1)>'
    page = bank.render_record(reseal(snapshot))
    assert '<img src=x' not in page
    assert '\\u003c/script\\u003e' in page
    snapshot['evidence']['sources'] = ['javascript:alert(1)']
    with pytest.raises(ValueError, match='HTTPS'):
        bank.render_record(reseal(snapshot))


@pytest.mark.parametrize('value', [float('nan'), float('inf'), True])
def test_invalid_numeric_values_are_refused(snapshot, value):
    snapshot['evidence']['metrics']['gnpa_pct']['value'] = value
    with pytest.raises(ValueError, match='finite'):
        bank.validate(snapshot['evidence'], 'au-sfb')


def test_stale_record_cannot_be_rendered_as_current(snapshot):
    snapshot['evidence']['status'] = 'stale'
    page = bank.render_record(reseal(snapshot))
    assert 'Evidence state at capture: <strong>stale</strong>' in page
    assert 'not a live bank-health assessment' in page


def test_wrong_api_or_ambiguous_capture_clock_is_refused(snapshot):
    altered = copy.deepcopy(snapshot)
    altered['api_url'] = 'https://other.example/record'
    with pytest.raises(ValueError, match='API route'):
        bank.render_record(altered)
    snapshot['captured_at'] = '2026-09-27T00:00:00'
    with pytest.raises(ValueError, match='timezone'):
        bank.render_record(snapshot)


def test_active_mcp_counts_agree_with_the_published_inventory():
    catalog = json.loads((ROOT/'.well-known/ai-catalog.json').read_text())
    entry = next(e for e in catalog['entries'] if e['identifier'] == 'urn:air:liquilens.in:mcp:failure-radar')
    count = len(entry['capabilities'])
    assert count == entry['metadata']['publicToolCount']
    assert f'{count} read-only tools and 5 prompts' in (ROOT/'banking/index.html').read_text()
    assert f'{count} public tools + 5 prompts' in (ROOT/'developers/index.html').read_text()
    assert f'review the {count} public tools' in (ROOT/'developers/index.html').read_text()
