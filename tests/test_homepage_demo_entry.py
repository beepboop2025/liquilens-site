from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_investor_demo_remains_discoverable_with_its_access_boundary():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    footer = html.split('<footer class="family-footer">', 1)[1].split('</footer>', 1)[0]
    assert 'https://demo.liquilens.in/?demo=1' in footer
    assert 'sign in required' in footer.lower()
    assert footer.count('data-funnel="investor_demo_clicked"') == 1
