from hashlib import sha256
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from scripts.build_upgrade_surfaces import outputs, manifest, block

ROOT = Path(__file__).resolve().parents[1]


def test_homepage_manifest_and_public_pages_cannot_drift():
    for path, generated in outputs().items():
        assert path.read_text() == generated, str(path)
    data, revision = manifest()
    assert revision == sha256((ROOT / 'updates/capabilities.json').read_bytes()).hexdigest()
    assert block(data, revision) in (ROOT / 'index.html').read_text()


def test_capabilities_preserve_authority_and_reviewed_provenance():
    data, _ = manifest()
    assert len({c['id'] for c in data['capabilities']}) == len(data['capabilities'])
    assert {p['name'] for p in data['products']} == {'LiquiLens', 'Seiche', 'Undertow'}
    for capability in data['capabilities']:
        assert capability['boundary']
        assert re.fullmatch(r'https://github.com/beepboop2025/[a-zA-Z0-9-]+/commit/[a-f0-9]{40}',capability['source'])
        assert urlsplit(capability['url']).scheme == 'https'
    execution = next(c for c in data['capabilities'] if c['id'] == 'execution-workbench')
    assert 'disabled' in execution['state']
    assert 'simulation' in execution['boundary']


def test_monitor_is_discoverable_and_loads_without_a_private_app():
    for path in ['index.html','banking/index.html','agents/index.html','developers/index.html','llms.txt','sitemap.xml']:
        assert '/banking/monitoring/' in (ROOT / path).read_text()
    page = (ROOT / 'banking/monitoring/index.html').read_text()
    assert 'institution-monitor.mjs' in page
    assert 'monitoring/watchlist' in page
    assert 'demo.liquilens.in' not in page
    assert 'type="module"' in page

