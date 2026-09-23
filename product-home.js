import {runTask, TASKS} from "./start/core.mjs";
import {mountEditorial} from "./family-editorial.mjs";
/* Concept walkthrough: local presentation only, with no analytics or financial values. */
(() => {
  const steps = {
    institution: {kind: 'Institution review', title: 'Begin with a named institution.', description: 'Check that the institution is covered. Read the source dates, disclosed changes and limitations before drawing a conclusion.', rows: [['Identity', 'Exact institution'], ['Evidence', 'Disclosures and changes'], ['Limits', 'Coverage and freshness']]},
    funding: {kind: 'Funding context', title: 'Understand the conditions around it.', description: 'Bring in Seiche’s money-market observations. Keep their dates and limitations separate from institution-specific evidence.', rows: [['Context', 'Money markets'], ['Source', 'Seiche observations'], ['Boundary', 'Separate evidence, no combined score']]},
    brief: {kind: 'Review brief', title: 'Keep the evidence you can explain.', description: 'Select the records that matter. Download a brief with source dates, coverage gaps and open review questions for your team.', rows: [['Records', 'Your selected observations'], ['Export', 'Markdown or JSON'], ['Compliance', 'Unassessed']]}
  };
  document.querySelectorAll('[data-review-step]').forEach(button => {
    button.addEventListener('click', () => {
      const step = steps[button.dataset.reviewStep];
      if (!step) return;
      document.querySelectorAll('[data-review-step]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
      document.getElementById('review-kind').textContent = step.kind;
      document.getElementById('review-heading').textContent = step.title;
      document.getElementById('review-description').textContent = step.description;
      const rows = step.rows.map(([label, value]) => {
        const row = document.createElement('div');
        const key = document.createElement('span');
        const detail = document.createElement('b');
        key.textContent = label; detail.textContent = value;
        row.append(key, detail); return row;
      });
      document.getElementById('review-records').replaceChildren(...rows);
    });
  });
  const library = document.getElementById('evidence-library');
  let loaded = false;
  const loadEvidence = () => {
    if (loaded || !library?.open) return;
    loaded = true;
    const script = document.createElement('script');
    script.src = '/evidence-library.js';
    script.addEventListener('error', () => { loaded = false; });
    document.body.append(script);
  };
  library?.addEventListener('toggle', loadEvidence);
  const revealLinkedEvidence = () => {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    const target = id && document.getElementById(id);
    if (!target || !library?.contains(target)) return;
    library.open = true;
    loadEvidence();
    requestAnimationFrame(() => target.scrollIntoView({block: 'start', behavior: 'instant'}));
  };
  window.addEventListener('hashchange', revealLinkedEvidence);
  revealLinkedEvidence();
})();

mountEditorial(document.getElementById('family-editorial'));
const preview = document.getElementById('data-preview');
if (preview) {
  let task = 'funding';
  const run = document.getElementById('preview-run');
  const state = document.getElementById('preview-state');
  const output = document.getElementById('preview-output');
  const elapsed = document.getElementById('preview-time');
  const options = [...preview.querySelectorAll('[data-preview-task]')];
  const node = (tag, text) => {const item = document.createElement(tag); if (text !== undefined) item.textContent = text; return item;};
  options.forEach(button => button.addEventListener('click', () => {
    task = button.dataset.previewTask;
    options.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    document.getElementById('preview-provider').textContent = TASKS[task].product;
    document.getElementById('preview-question').textContent = TASKS[task].title;
    state.textContent = task === 'exit' ? 'BTC example: 100,000 USD sell size. Research estimate, not an executable quote.' : 'Ready to request public evidence.';
    elapsed.textContent = 'Response time appears after a request';
    output.replaceChildren();
  }));
  run.addEventListener('click', async () => {
    run.disabled = true; options.forEach(button => {button.disabled = true;});
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 25000);
    const started = performance.now();
    output.replaceChildren(); state.textContent = 'Requesting evidence from ' + TASKS[task].product + '…';
    elapsed.textContent = 'Request in progress';
    try {
      const result = await runTask(task, {size:100000, verification:new URLSearchParams(location.search).get('verification') === '1', signal:controller.signal});
      const seconds = (performance.now() - started) / 1000;
      elapsed.textContent = seconds.toFixed(2) + ' s · this browser request';
      state.textContent = result.view.state + ' · retrieved ' + result.retrievedAt;
      output.append(node('h4', result.view.title), node('p', result.view.note));
      const facts = node('dl');facts.className = 'preview-facts';
      for (const [label,value] of result.view.facts) {const fact=node('div');fact.append(node('dt',label),node('dd',value));facts.append(fact);}
      output.append(facts);
      const limits=node('details');limits.append(node('summary','Sources, observations and limits'));
      const details=node('dl');details.className='preview-details';
      for (const [label,value] of result.view.details) {const row=node('div');row.append(node('dt',label),node('dd',value));details.append(row);}
      const list=node('ul');for (const limit of result.view.limits) list.append(node('li',limit));
      limits.append(details,list);
      for (const url of result.view.sources) {const anchor=node('a',url);anchor.href=url;anchor.target='_blank';anchor.rel='noopener noreferrer';limits.append(anchor);}
      output.append(limits);
    } catch {
      elapsed.textContent = 'No completed result';
      state.textContent = 'This preview is unavailable right now. Open the review workspace or connect your agent to try the same source.';
    } finally {clearTimeout(timeout);run.disabled=false;options.forEach(button=>{button.disabled=false;});}
  });
}
