import {createEvidenceLoader, DEFAULT_PLACE, formatNumber, validPlace} from './evidence-model.mjs';

function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text != null) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function button(text, action) {
  const node = el('button', text); node.type = 'button'; node.addEventListener('click', action); return node;
}
function metric(row) {
  const card = el('article', null, 'evidence-card');
  card.append(el('h4', row.label), el('strong', row.value), el('p', row.date, 'evidence-date'), el('p', row.detail, 'evidence-muted'));
  return card;
}
function showMonths(months) {
  const wrap = el('section', null, 'evidence-months');
  wrap.append(el('h4', 'Explore monthly rainfall'));
  if (!months.length) {wrap.append(el('p', 'Monthly history is not available.')); return wrap;}
  const label = el('label', 'Observation month '), select = el('select');
  select.setAttribute('aria-label', 'Rainfall observation month');
  months.forEach(row => {const option = el('option', row.month); option.value = row.month; select.append(option);});
  select.value = months.at(-1).month; label.append(select);
  const summary = el('p', null, 'evidence-month-summary'); summary.setAttribute('aria-live', 'polite');
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 640 220'); svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', 'Monthly rainfall bars; full values are in the table below.'); svg.classList.add('evidence-chart');
  const maximum = Math.max(1, ...months.flatMap(row => [row.mm, row.normal].filter(value => typeof value === 'number')));
  const chartNodes = [];
  for (const fraction of [0, .5, 1]) {
    const y = 176 - fraction * 144;
    const line = document.createElementNS(svg.namespaceURI, 'line');
    line.setAttribute('x1', '48'); line.setAttribute('x2', '630'); line.setAttribute('y1', String(y)); line.setAttribute('y2', String(y)); line.setAttribute('class', 'chart-grid'); svg.append(line);
    const tick = document.createElementNS(svg.namespaceURI, 'text'); tick.setAttribute('x', '42'); tick.setAttribute('y', String(y + 4)); tick.setAttribute('text-anchor', 'end'); tick.setAttribute('class', 'chart-axis'); tick.textContent = formatNumber(Math.round(maximum * fraction)); svg.append(tick);
  }
  const unit = document.createElementNS(svg.namespaceURI, 'text'); unit.setAttribute('x', '48'); unit.setAttribute('y', '16'); unit.setAttribute('class', 'chart-axis'); unit.textContent = 'Rainfall (mm)'; svg.append(unit);
  months.forEach((row, index) => {
    const x = 50 + index * 578 / months.length, step = 578 / months.length;
    if (index === 0 || index === Math.floor(months.length / 2) || index === months.length - 1) {
      const tick = document.createElementNS(svg.namespaceURI, 'text'); tick.setAttribute('x', String(x + step / 2)); tick.setAttribute('y', '202'); tick.setAttribute('text-anchor', index === 0 ? 'start' : index === months.length - 1 ? 'end' : 'middle'); tick.setAttribute('class', 'chart-axis'); tick.textContent = row.month; svg.append(tick);
    }
    for (const [key, offset, css] of [['normal', 0, 'evidence-bar-normal'], ['mm', step * 0.4, 'evidence-bar-observed']]) {
      if (row[key] == null) continue;
      const rect = document.createElementNS(svg.namespaceURI, 'rect');
      rect.setAttribute('x', String(x + offset)); rect.setAttribute('y', String(176 - row[key] / maximum * 144));
      rect.setAttribute('width', String(step * 0.35)); rect.setAttribute('height', String(Math.max(0, row[key] / maximum * 144))); rect.setAttribute('class', css);
      chartNodes.push({node: rect, month: row.month});
      const title = document.createElementNS(svg.namespaceURI, 'title'); title.textContent = `${row.month} ${key === 'mm' ? 'observed' : 'normal'}: ${formatNumber(row[key])} mm`; rect.append(title); svg.append(rect);
    }
  });
  const details = el('details'); details.append(el('summary', 'Show all monthly values'));
  const scroller = el('div', null, 'evidence-table-wrap'), table = el('table', null, 'evidence-table'), head = el('thead'), heading = el('tr');
  for (const name of ['Month', 'Rainfall (mm)', 'Normal (mm)', 'Departure (%)', 'Context']) {const th = el('th', name); th.scope = 'col'; heading.append(th);}
  head.append(heading); table.append(el('caption', 'CHIRPS monthly rainfall; normal is the 1991–2020 mean.'), head);
  const body = el('tbody');
  months.forEach(row => {
    const tr = el('tr'); tr.append(el('th', row.month), ...[formatNumber(row.mm), formatNumber(row.normal), formatNumber(row.departure), row.lowNormal ? 'Low normal: less than 10 mm' : ''].map(value => el('td', value)));
    tr.firstChild.scope = 'row'; body.append(tr);
  });
  table.append(body); scroller.append(table); details.append(scroller);
  const update = () => {
    const row = months.find(item => item.month === select.value);
    for (const mark of chartNodes) mark.node.setAttribute('data-selected', String(mark.month === row.month));
    summary.textContent = `${row.month}: ${formatNumber(row.mm)} mm · normal ${formatNumber(row.normal)} mm · departure ${formatNumber(row.departure)}%.${row.lowNormal ? ' Normal is below 10 mm; small changes can produce large percentage departures.' : ''}`;
  };
  select.addEventListener('change', update); update();
  wrap.append(label, summary, svg, el('p', 'Paired bars: slate = normal; blue = observed. The selected month is outlined in amber. Missing values have no bar.', 'evidence-muted'), details);
  return wrap;
}

export function initEvidence(root, options = {}) {
  const loader = createEvidenceLoader();
  const directoryController = new AbortController(); let disposed = false;
  let currentId = DEFAULT_PLACE, currentOffset = 0, history = [], places = [];
  const discovery = el('div', null, 'evidence-discovery');
  const stateLabel = el('label', 'Browse a state '), stateSelect = el('select');
  stateSelect.append(el('option', 'All India')); stateSelect.firstChild.value = '';
  stateSelect.setAttribute('aria-label', 'Filter districts by state'); stateLabel.append(stateSelect);
  const districtForm = el('form', null, 'evidence-form'), districtLabel = el('label', 'Find a district '), districtInput = el('input');
  districtInput.setAttribute('list', 'geography-districts'); districtInput.placeholder = 'Type a district name'; districtInput.autocomplete = 'off';
  const datalist = el('datalist'); datalist.id = 'geography-districts'; districtLabel.append(districtInput);
  const districtSubmit = el('button', 'Open district'); districtSubmit.type = 'submit'; districtForm.append(districtLabel, districtSubmit);
  const stateButton = button('Browse state evidence', () => {if (stateSelect.value) load(`in-state-${stateSelect.value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')}`);}); stateButton.disabled = true;
  discovery.append(stateLabel, stateButton, districtForm, datalist);
  const form = el('form', null, 'evidence-form'), label = el('label', 'District, state, or cooperative-bank ID');
  const input = el('input'); input.name = 'place'; input.type = 'text'; input.required = true; input.maxLength = 120;
  input.placeholder = DEFAULT_PLACE; input.spellcheck = false; input.autocomplete = 'off'; label.append(input);
  const submit = el('button', 'Load evidence'); submit.type = 'submit'; form.append(label, submit);
  const examples = el('div', null, 'evidence-links');
  for (const [name, id] of [['Jaipur district', DEFAULT_PLACE], ['Jaipur cooperative bank', 'in-dccb-rajasthan-jaipur'], ['Rajasthan districts', 'in-state-rajasthan']]) examples.append(button(name, () => load(id, 0)));
  const help = el('p', 'Choose a district or state to explore the evidence. Districts use 2021 boundaries. These are district aggregates, not readings from the image pixels; image dates and measurement dates are independent.', 'evidence-muted');
  const status = el('p', '', 'evidence-status'); status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
  const results = el('div', null, 'evidence-results');
  const exact = el('details'); exact.append(el('summary', 'Look up an exact bank or district ID'), form);
  root.replaceChildren(discovery, examples, exact, help, status, results);
  let searchVisible = true;
  const toggleSearch = button('Change place', () => setSearchVisible(!searchVisible));
  toggleSearch.className = 'place-toggle'; toggleSearch.hidden = true;
  root.append(toggleSearch);
  function setSearchVisible(visible) {
    searchVisible = visible;
    for (const control of [discovery, examples, exact, help]) control.hidden = !visible;
    toggleSearch.textContent = visible ? 'Hide place search' : 'Change place';
    toggleSearch.setAttribute('aria-expanded', String(visible));
  }
  status.textContent = 'All India · choose a district or state to load its evidence.';
  const refreshDistricts = () => {
    datalist.replaceChildren();
    for (const place of places.filter(item => !stateSelect.value || item.state === stateSelect.value)) {
      const option = el('option'); option.value = `${place.name}, ${place.state}`; datalist.append(option);
    }
    stateButton.disabled = !stateSelect.value; districtInput.value = '';
  };
  stateSelect.addEventListener('change', refreshDistricts);
  districtForm.addEventListener('submit', event => {
    event.preventDefault();
    const query = districtInput.value.trim().toLowerCase();
    const matching = places.filter(place => (!stateSelect.value || place.state === stateSelect.value) &&
      (`${place.name}, ${place.state}`.toLowerCase() === query || place.name.toLowerCase() === query));
    if (matching.length !== 1) {loader.cancel(); options.onInvalid?.(); results.replaceChildren(); results.setAttribute('aria-busy', 'false'); status.textContent = matching.length > 1 ? 'That district name occurs in more than one state. Choose a state or the full district name.' : 'Choose a district from the suggestions, or use an exact research ID.'; districtInput.focus(); return;}
    load(matching[0].id);
  });
  fetch(new URL('./places.json', import.meta.url), {credentials: 'omit', signal: directoryController.signal}).then(response => {
    if (!response.ok) throw new Error('District directory unavailable'); return response.json();
  }).then(rows => {
    if (disposed) return;
    if (!Array.isArray(rows) || rows.length > 2000 || rows.some(row => !validPlace(row.id) || typeof row.name !== 'string' || typeof row.state !== 'string')) throw new Error('Invalid district directory');
    places = rows;
    [...new Set(rows.map(row => row.state))].sort().forEach(state => {const option = el('option', state); option.value = state; stateSelect.append(option);});
    refreshDistricts();
    options.onDirectory?.(places);
  }).catch(() => {if (!disposed) discovery.append(el('p', 'The district directory could not be loaded. Use the examples or an exact ID below.', 'evidence-error'));});

  async function load(id, offset = 0, previous = null) {
    if (!validPlace(id)) {loader.cancel(); options.onInvalid?.(); results.replaceChildren(); results.setAttribute('aria-busy', 'false'); status.textContent = 'Enter an exact ID beginning in-dist-, in-state-, in-dccb-, or in-stcb-.'; input.focus(); return;}
    currentId = id; currentOffset = offset; input.value = id;
    options.onLoading?.({id, offset});
    history = previous ?? [];
    results.replaceChildren(); results.setAttribute('aria-busy', 'true');
    status.textContent = `Loading evidence for ${id}…`;
    try {
      const model = await loader.load(id, offset);
      if (!model) return;
      if (disposed) return;
      options.onModel?.(model, places);
      if (model.districts.length) {toggleSearch.hidden = false; setSearchVisible(false);}
      results.setAttribute('aria-busy', 'false');
      status.textContent = `${model.name} · ${model.status.replaceAll('_', ' ')}. Response dated ${model.generated}; observation dates are shown separately.`;
      if (!model.districts.length) {
        results.append(el('p', model.reason || 'No district observations are available for this place.', 'evidence-muted'));
        return;
      }
      const title = el('h3', model.name); results.append(title);
      for (const district of model.districts) {
        const section = el('section', null, 'evidence-district');
        if (id !== district.id) section.append(el('h3', `${district.name}, ${district.state}`));
        if (id !== district.id) section.append(button('Open district history', () => load(district.id)));
        if (district.basis) section.append(el('p', `Lender link: ${district.basis}. This does not measure lending shares.`, 'evidence-muted'));
        const metrics = el('div', null, 'evidence-grid'); [...district.rainfall, ...district.signals].forEach(row => metrics.append(metric(row))); section.append(metrics);
        section.append(el('p', district.droughtYears === null ? 'Declared drought history: not supplied.' : district.droughtYears.length ? `Declared drought years: ${district.droughtYears.join(', ')}. Source: ${district.droughtSource || 'Source not supplied'}.` : `No declared drought years listed in ${district.droughtSource || 'the supplied record'}; this is not evidence of no drought.`));
        section.append(showMonths(district.months)); results.append(section);
      }
      if (model.total > 1 || model.offset > 0) {
        const pagination = el('nav', null, 'evidence-pagination'); pagination.setAttribute('aria-label', 'District pages');
        const back = button('Previous districts', () => {const nextHistory = history.slice(); const prior = nextHistory.pop() ?? Math.max(0, model.offset - 5); load(id, prior, nextHistory);});
        back.disabled = model.offset === 0;
        const next = button('Next districts', () => load(id, model.nextOffset, [...history, model.offset])); next.disabled = model.nextOffset === null;
        pagination.append(back, el('span', `Districts ${model.offset + 1}–${model.offset + model.districts.length} of ${model.total}`), next); results.append(pagination);
      }
      if (model.institutions.length) {
        const links = el('details', null, 'evidence-institutions'); links.append(el('summary', `Linked cooperative banks (${model.institutions.length})`));
        const list = el('ul', null, 'evidence-links');
        model.institutions.forEach(item => {const li = el('li'); li.append(button(item.id, () => load(item.id))); if (item.basis) li.append(el('span', ` · ${item.basis}`)); list.append(li);});
        links.append(list); results.append(links);
      }
      const provenance = el('details', null, 'evidence-sources'); provenance.append(el('summary', 'Sources and interpretation limits'));
      const list = el('ul'); model.sources.forEach(source => {
        const item = el('li');
        if (source.url) {const a = el('a', source.label); a.href = source.url; a.target = '_blank'; a.rel = 'noopener noreferrer'; item.append(a);} else item.append(el('strong', source.label));
        item.append(el('p', source.detail)); list.append(item);
      });
      provenance.append(list); model.limits.forEach(limit => provenance.append(el('p', limit))); results.append(provenance);
    } catch (error) {
      if (disposed) return;
      options.onError?.(error);
      results.setAttribute('aria-busy', 'false'); status.textContent = 'Evidence could not be loaded.';
      results.replaceChildren(el('p', error.message || 'A network error occurred.', 'evidence-error'), button('Retry this place', () => load(currentId, currentOffset, history)));
    }
  }
  form.addEventListener('submit', event => {event.preventDefault(); load(input.value.trim(), 0);});
  return {load, destroy() {disposed = true; directoryController.abort(); loader.cancel(); root.replaceChildren();}};
}
