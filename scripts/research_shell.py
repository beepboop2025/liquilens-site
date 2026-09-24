"""Keep generated and hand-maintained public pages on one research shell."""
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
STYLE = '<link rel="stylesheet" href="/research-ui/research.css">'
CONTEXT = '<script type="module" src="/research-ui/context.js"></script>'


def attach_context(source: str) -> str:
    return source if CONTEXT in source else source.replace('</body>', CONTEXT + '</body>', 1)


def research_header(path: str) -> str:
    header = (ROOT / 'research-ui/header.html').read_text().strip()
    prefix, tabs = header.split('<nav class="research-tabs"', 1)
    tabs = tabs.replace(' aria-current="page"', '')
    destinations = re.findall(r'href="(/[^"#?]*)"', tabs)
    section = next((item for item in sorted(set(destinations), key=len, reverse=True)
                    if path == item or (item != '/' and item.endswith('/') and path.startswith(item))), None)
    if section:
        tabs = tabs.replace(f'href="{section}"', f'href="{section}" aria-current="page"', 1)
    return prefix + '<nav class="research-tabs"' + tabs


def unify_html(source: str, path: str) -> str:
    """Replace only product chrome; retain content, routing, metadata and controls."""
    if re.search(r'http-equiv=[\"\x27]refresh', source, re.I):
        return source
    if '<header class="research-header"' in source:
        return attach_context(source)
    path = urlsplit(path).path or '/'
    header = research_header(path)
    old = re.compile(r'<header class="family-header">.*?</header>', re.S)
    if old.search(source):
        source = old.sub(lambda _: header, source, count=1)
    elif '<body' in source:
        source = re.sub(r'(<body\b[^>]*>)', lambda m: m[0] + header, source, count=1)
    else:
        return source
    def html_class(match):
        opening = match[0]
        if 'research-interface' in opening:
            return opening
        if re.search(r'\bclass="', opening):
            return re.sub(r'class="([^"]*)"', lambda m: f'class="{m[1]} research-interface"', opening, count=1)
        return opening[:-1] + ' class="research-interface">'
    source = re.sub(r'<html\b[^>]*>', html_class, source, count=1)
    source = source.replace('</head>', STYLE + '</head>', 1)
    main = re.search(r'<main\b[^>]*>', source)
    if main:
        identity = re.search(r'\bid="([^"]+)"', main[0])
        if identity:
            source = source.replace('class="research-skip" href="#main"', f'class="research-skip" href="#{identity[1]}"', 1)
        else:
            source = source[:main.start()] + main[0].replace('<main', '<main id="main"', 1) + source[main.end():]
    return attach_context(source)


def sync() -> list[str]:
    changed = []
    names = subprocess.check_output(['git', 'ls-files', '*.html'], cwd=ROOT, text=True).splitlines()
    for name in names:
        if name.startswith(('tests/', 'brand/')):
            continue
        file = ROOT / name
        source = file.read_text()
        if not re.search(r'<html\b', source, re.I):
            continue
        path = '/' + name.removesuffix('index.html') if name.endswith('index.html') else '/' + name
        rendered = unify_html(source, path)
        if rendered != source:
            file.write_text(rendered)
            changed.append(name)
    return changed


if __name__ == '__main__':
    changed = sync()
    print(f'Unified {len(changed)} public page shells')
