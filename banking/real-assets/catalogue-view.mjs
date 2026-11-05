import {FEATURED, QUESTIONS, RULES, entriesFor, searchDraft} from './indian-catalogue.mjs';

function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text != null) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function link(text, href) {
  const node = el('a', text);
  node.href = href;
  node.target = '_blank';
  node.rel = 'noopener noreferrer';
  return node;
}

export function drawCatalogue(root, {question, onQuestion, onDraft}) {
  const rules = root.querySelector('#catalogue-rules');
  const filters = root.querySelector('#catalogue-filters');
  const grid = root.querySelector('#catalogue-grid');
  rules.replaceChildren();
  filters.replaceChildren();
  grid.replaceChildren();
  for (const rule of RULES) {
    const card = el('article', null, 'policy-card');
    card.append(el('h3', rule.title), el('p', rule.text), link(rule.link, rule.href));
    rules.append(card);
  }
  for (const item of QUESTIONS) {
    const button = el('button', item.label);
    button.type = 'button';
    button.setAttribute('aria-pressed', String(item.id === question));
    button.addEventListener('click', () => onQuestion(item.id));
    filters.append(button);
  }
  const rows = entriesFor(question);
  for (const item of rows) {
    const card = el('article', null, 'catalogue-card');
    card.append(el('p', item.provider, 'catalogue-provider'), el('h3', item.name));
    if (item.kind === 'collection') card.append(el('code', item.id));
    card.append(el('p', item.access, 'catalogue-access'), el('p', item.note));
    const actions = el('div', null, 'catalogue-actions');
    actions.append(link('Official page', item.href));
    if (item.kind === 'collection') {
      const draft = el('button', 'Draft a search');
      draft.type = 'button';
      draft.addEventListener('click', () => onDraft(item.id));
      actions.append(draft);
    }
    card.append(actions);
    grid.append(card);
  }
  if (!rows.length) grid.append(el('p', 'No published route is tagged for this question.', 'quiet'));
  return rows.length;
}

export function draftText(collectionId, district, start, end, today) {
  if (!district) throw new Error('Choose a district before drafting a scene search.');
  const draft = searchDraft({collectionId, bbox: district.bbox, start, end}, today);
  return JSON.stringify(draft, null, 2);
}

export const featuredCount = FEATURED.length;
