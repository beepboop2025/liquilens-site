import {boundedJson, configuration, safeUrl} from '../start/core.mjs';

export const DATA_ROOT = 'https://api.seiche.info/api/v2/research-data';
const count = value => Number.isSafeInteger(value) && value >= 0 ? value.toLocaleString('en-US') : 'Not published';
export function coverageRows(data) {
  if (data?.schema !== 'liquilens.research-data.v1' || !Array.isArray(data.datasets)) throw new Error('Unexpected source catalog.');
  return data.datasets.map(item => ({
    title: typeof item.metadata?.title === 'string' ? item.metadata.title : String(item.id),
    id: String(item.id), product: item.product,
    cells: [count(item.available), count(item.series_count), item.latest_observation || 'Not published',
      item.last_success || 'Not published', `${item.refresh_state || 'Unknown'} collection / ${item.observation_state || 'unknown'} observations`],
    source: safeUrl(item.metadata?.source_url), rights: item.metadata?.rights_state || 'Not published',
    coverageClock: item.catalog_generated_at || 'Not published',
  }));
}

if (typeof document !== 'undefined') {
  const button = document.getElementById('load-source-data');
  const status = document.getElementById('source-data-status');
  const tbody = document.getElementById('source-data-rows');
  const client = document.getElementById('client');
  const code = document.getElementById('source-data-config');
  const setConfig = () => {code.textContent = configuration(client.value, ['research-data']);};
  client.addEventListener('change', setConfig);
  setConfig();
  document.getElementById('copy-source-data').addEventListener('click', async () => {
    try {await navigator.clipboard.writeText(code.textContent); status.textContent = 'Source-data configuration copied.';}
    catch {status.textContent = 'Select and copy the configuration shown below.';}
  });
  button.addEventListener('click', async () => {
    button.disabled = true;
    status.textContent = 'Reading the published source catalog…';
    try {
      const response = await fetch(DATA_ROOT + '/catalog', {credentials: 'omit', redirect: 'error', signal: AbortSignal.timeout(15000)});
      if (!response.ok) throw new Error('Source catalog unavailable.');
      const data = await boundedJson(response);
      const rows = coverageRows(data);
      tbody.replaceChildren();
      for (const item of rows) {
        const tr = document.createElement('tr'), title = document.createElement('td'), link = document.createElement('a');
        const url = new URL(DATA_ROOT + '/');
        if (['seiche','liquilens','undertow'].includes(item.product)) url.searchParams.set('product', item.product);
        link.href = url.href; link.textContent = item.title; title.append(link);
        const detail = document.createElement('small'); detail.textContent = `${item.id} · ${item.rights}`;
        title.append(document.createElement('br'), detail);
        if (item.source) {const source = document.createElement('a'); source.href = item.source; source.textContent = 'Original source'; title.append(document.createElement('br'), source);}
        tr.append(title);
        for (const text of item.cells) {const td = document.createElement('td'); td.textContent = text; tr.append(td);}
        tr.title = 'Coverage count captured: ' + item.coverageClock;
        tbody.append(tr);
      }
      status.textContent = `${rows.length} published datasets. Catalog evaluated ${data.evaluated_at || data.generated_at || 'at an unknown time'}. Counts describe captured coverage; collection and observation clocks remain separate.`;
    } catch {
      status.textContent = tbody.children.length ? 'Refresh failed. The previously retrieved, dated catalog remains visible.' : 'The source catalog could not be loaded. Open the source workspaces below or retry.';
    } finally {button.disabled = false;}
  });
}
