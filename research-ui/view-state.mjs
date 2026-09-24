const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const STATES = new Set(['all', 'observed', 'stale', 'historical', 'unavailable']);
const SECTORS = new Set(['all', 'bank', 'sfb', 'ucb']);
export const STORAGE_KEY = 'liquilens.institution-view.v1';
const ids = values => [...new Set(Array.isArray(values) ? values.filter(v => typeof v === 'string' && v.length <= 100 && SLUG.test(v)) : [])].slice(0, 3);

export function normalizeView(value = {}) {
  if (!value || typeof value !== 'object') value = {};
  return {
    institution: typeof value.institution === 'string' && value.institution.length <= 100 && SLUG.test(value.institution) ? value.institution : null,
    query: typeof value.query === 'string' ? value.query.slice(0, 100) : '',
    sector: SECTORS.has(value.sector) ? value.sector : 'all',
    status: STATES.has(value.status) ? value.status : 'observed',
    comparison: ids(value.comparison),
  };
}

export function restoreView(url, storage) {
  let saved = {};
  try { saved = JSON.parse(storage?.getItem(STORAGE_KEY) || '{}'); } catch { /* Private browsing can refuse storage. */ }
  const params = new URL(url).searchParams;
  const explicit = ['institution', 'q', 'sector', 'evidence', 'compare'].some(key => params.has(key));
  return normalizeView(explicit ? {
    institution: params.get('institution'), query: params.get('q'), sector: params.get('sector'),
    status: params.get('evidence') || (params.has('institution') ? 'all' : 'observed'),
    comparison: (params.get('compare') || '').split(','),
  } : saved);
}

export function rememberView(url, value, storage) {
  const state = normalizeView(value), next = new URL(url);
  const params = {institution: state.institution, q: state.query, sector: state.sector === 'all' ? '' : state.sector,
    evidence: state.status, compare: state.comparison.join(',')};
  for (const [key, value] of Object.entries(params)) value ? next.searchParams.set(key, value) : next.searchParams.delete(key);
  try { storage?.setItem(STORAGE_KEY, JSON.stringify(state)); } catch { /* URL state remains usable. */ }
  return next;
}
