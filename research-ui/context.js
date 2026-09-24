export function readInstitutionContext(href) {
  try {
    const values = new URL(href).searchParams.getAll('institution');
    return values.length === 1 && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(values[0])
      && values[0].length <= 96 ? values[0] : null;
  } catch { return null; }
}

export function syncInstitutionContext() {
  if (typeof document === 'undefined') return;
  const institution = readInstitutionContext(location.href);
  const header = document.querySelector('.research-header');
  if (header) {
    header.querySelector('[data-institution-context]')?.remove();
    const product = header.querySelector('.research-network [aria-current="page"]')?.textContent.trim();
    const links = [...header.querySelectorAll('.research-network a, .research-tabs a, .research-identity')];
    for (const link of links) {
      const url = new URL(link.href, location.href);
      if (institution && !(product === 'Undertow' && url.pathname === '/app/')) url.searchParams.set('institution', institution);
      else url.searchParams.delete('institution');
      link.href = url.href;
    }
    if (institution && product !== 'LiquiLens') {
      const context = document.createElement('div');
      context.className = 'research-context';
      context.dataset.institutionContext = '';
      const label = document.createElement('span');
      label.textContent = 'Institution review';
      const back = document.createElement('a');
      back.href = 'https://liquilens.in/?institution=' + encodeURIComponent(institution);
      back.textContent = 'Return to institution evidence →';
      const clear = document.createElement('button');
      clear.type = 'button'; clear.textContent = 'Clear';
      clear.setAttribute('aria-label', 'Clear institution review context');
      clear.addEventListener('click', () => {
        const url = new URL(location.href); url.searchParams.delete('institution');
        history.replaceState(null, '', url);
        syncInstitutionContext();
      });
      context.append(label, back, clear); header.append(context);
    }
  }
}

if (typeof document !== 'undefined') {
  syncInstitutionContext();
  window.addEventListener('popstate', syncInstitutionContext);
  window.addEventListener('research:context-changed', syncInstitutionContext);
}
