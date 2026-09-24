import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('research_shell', ROOT / 'scripts/research_shell.py')
shell = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shell)


def test_generator_chrome_is_shared_without_modifying_article_or_policy():
    source = '<html class="family-design"><head><meta name="policy" content="keep"></head><body><header class="family-header"><nav>old</nav></header><main><h1>Source-dated evidence</h1><script>const period = "2026-06-30";</script></main></body></html>'
    result = shell.unify_html(source, 'https://liquilens.in/articles/example/')
    assert 'class="family-design research-interface"' in result
    assert '<a href="/articles/" aria-current="page">' in result
    assert '<a href="/" aria-current="page">LiquiLens</a>' in result
    assert '<meta name="policy" content="keep">' in result
    assert '<main id="main"><h1>Source-dated evidence</h1><script>const period = "2026-06-30";</script>' in result
    assert shell.unify_html(result, '/articles/example/') == result


def test_existing_content_anchor_is_preserved():
    result = shell.unify_html('<html><head></head><body><main id="review">content</main></body></html>', '/banking/')
    assert 'class="research-skip" href="#review"' in result
    assert 'href="/banking/" aria-current="page"' in result


def test_redirect_bridge_remains_unchanged():
    source = '<html><head><meta http-equiv="refresh" content="0;url=/banking/"></head><body>Continue</body></html>'
    assert shell.unify_html(source, '/old/') == source
