import {BASES, LIMITS, SCHEMA, SOURCES, casePack, csv, emptyBundle, normalisePrice, seriesSummary, validateBundle, validateCase} from './model.mjs';
import {appendObservation, replaceObservation, removeObservation, restoreObservation, planningFromFields, scenarioFromFields, SCENARIO_FIELDS} from './ui-model.mjs';
import {imageURL, LAYER, stateFromURL, validDate} from '../geography/imagery-model.mjs';
import {frameSelection, selectionFromURL, workspaceQuery} from '../geography/workspace-model.mjs';
import {drawCatalogue, draftText} from './catalogue-view.mjs';

const $ = id => document.getElementById(id);
const money = value => new Intl.NumberFormat('en-IN', {style: 'currency', currency: 'INR', maximumFractionDigits: 0}).format(value);
const number = value => new Intl.NumberFormat('en-IN', {maximumFractionDigits: 3}).format(value);
const fields = form => Object.fromEntries(new FormData(form));
let bundle = emptyBundle(), planning = [], scenarioResult = null, places = [], district = null;
let imageState = stateFromURL(location.search), displayedImagery = null, imageGeneration = 0, hasUnsavedChanges = false;
const initialSelection = selectionFromURL(location.search).id || new URLSearchParams(location.search).get('district');
let directoryReady;
let editingObservationId = null, lastRemoval = null, catalogueQuestion = 'crop';

function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text != null) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function anchor(text, href) {const a = el('a', text); a.href = href; a.target = '_blank'; a.rel = 'noopener noreferrer'; return a;}
function status(id, message, error = false) {$(id).textContent = message; $(id).classList.toggle('error', error);}
function table(headers, caption) {
  const wrap = el('div', null, 'table-scroll'), t = el('table', null, 'land-table'), head = el('thead'), row = el('tr'), body = el('tbody');
  headers.forEach(label => {const th = el('th', label); th.scope = 'col'; row.append(th);});
  head.append(row); if (caption) t.append(el('caption', caption)); t.append(head, body); wrap.append(t);
  return {wrap, body};
}
function empty(title, text, linkText, href) {
  const node = el('div', null, 'empty-evidence'); node.append(el('h3', title), el('p', text));
  if (href) {const a = el('a', linkText); a.href = href; node.append(a);}
  return node;
}
function setExportAvailability() {
  const evidence = bundle.observations.length > 0, any = evidence || planning.length > 0 || scenarioResult !== null;
  $('export-case').disabled = !any; $('export-print').disabled = !any;
  $('export-evidence').disabled = !evidence; $('export-csv').disabled = !evidence;
}
function updateSourceChoice() {
  const select = $('source-choice'), previous = select.value;
  select.replaceChildren(el('option', 'Add a new source')); select.firstChild.value = 'new';
  for (const source of bundle.sources) {const option = el('option', `${source.title} (${source.id})`); option.value = source.id; select.append(option);}
  select.value = bundle.sources.some(source => source.id === previous) ? previous : 'new';
  toggleSourceFields();
}
function toggleSourceFields() {
  const isNew = $('source-choice').value === 'new'; $('new-source-fields').hidden = !isNew;
  for (const input of $('new-source-fields').querySelectorAll('input')) input.required = isNew && input.name !== 'published_at';
}
$('source-choice').addEventListener('change', toggleSourceFields);

function drawSeries(summary, rows) {
  const chart = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  chart.setAttribute('viewBox', '0 0 640 210'); chart.setAttribute('role', 'img'); chart.setAttribute('aria-label', `${summary.id}: submitted observations from ${summary.first.as_of} to ${summary.last.as_of}`); chart.classList.add('price-chart');
  const svg = (tag, attrs, text) => {const node = document.createElementNS(chart.namespaceURI, tag); for (const [key,value] of Object.entries(attrs)) node.setAttribute(key, value); if (text != null) node.textContent = text; chart.append(node); return node;};
  const values = rows.map(row => row.value), min = Math.min(...values), max = Math.max(...values), spread = max - min || Math.max(max * .1, 1);
  const low = Math.max(0, min - spread * .12), high = max + spread * .12;
  const first = Date.parse(rows[0].as_of), elapsed = Date.parse(rows.at(-1).as_of) - first;
  const x = row => 74 + (Date.parse(row.as_of) - first) / elapsed * 548;
  const y = value => 172 - (value - low) / (high - low) * 140;
  for (const fraction of [0,.5,1]) {const value = low + fraction * (high-low); svg('line',{x1:74,x2:622,y1:y(value),y2:y(value),class:'price-grid'}); svg('text',{x:68,y:y(value)+4,'text-anchor':'end',class:'price-axis'},number(value));}
  svg('text',{x:74,y:16,class:'price-axis'},summary.last.unit);
  svg('polyline',{points:rows.map(row => `${x(row)},${y(row.value)}`).join(' '),class:'price-line'});
  rows.forEach(row => {const dot = svg('circle',{cx:x(row),cy:y(row.value),r:4,class:'price-dot'}); const title = document.createElementNS(chart.namespaceURI,'title'); title.textContent = `${row.as_of}: ${number(row.value)} ${row.unit}`; dot.append(title);});
  svg('text',{x:74,y:198,class:'price-axis'},summary.first.as_of); svg('text',{x:622,y:198,'text-anchor':'end',class:'price-axis'},summary.last.as_of);
  return chart;
}
function renderPrices() {
  $('record-count').textContent = `${bundle.observations.length} observation${bundle.observations.length === 1 ? '' : 's'}`;
  const results = $('price-results'), seriesRoot = $('series-results'); results.replaceChildren(); seriesRoot.replaceChildren();
  if (!bundle.observations.length) {
    results.append(empty('Your evidence starts here.', 'Add a reviewed price record or import a JSON evidence file. There are no preloaded property prices, synthetic comparables or assumed market rates.', 'Find official source portals', '#source-register'));
    return;
  }
  const {wrap, body} = table(['Place / asset','Price basis','Observation','Value','Source','Review'], 'Researcher-supplied records. District context does not automatically establish the location of a price record.');
  for (const observation of bundle.observations) {
    const source = bundle.sources.find(item => item.id === observation.source_id), row = el('tr');
    const place = el('td', observation.locality); place.append(el('small', `${observation.city_id} / ${observation.asset_type}`));
    const basis = el('td'); basis.append(el('span', BASES[observation.price_basis], 'source-basis'), el('small', `${observation.evidence_type}; ${observation.sample_size} source sample${observation.sample_size===1?'':'s'}`));
    const value = el('td', `${number(observation.value)} ${observation.unit}`, 'numeric'), normal = normalisePrice(observation);
    if (normal !== null && observation.unit !== 'INR/sqm') value.append(el('small', `${number(normal)} INR/sqm, converted`));
    const citation = el('td'); citation.append(anchor(source.title,source.url),el('small', `${source.locator} · rights: ${source.rights}`));
    const actions = el('td',null,'record-actions'), edit = el('button','Edit'), remove = el('button','Remove');
    edit.type='button';remove.type='button';edit.setAttribute('aria-label',`Edit ${observation.locality} observation dated ${observation.as_of}`);remove.setAttribute('aria-label',`Remove ${observation.locality} observation dated ${observation.as_of}`);
    edit.addEventListener('click',()=>editObservation(observation));
    remove.addEventListener('click',()=>{try{lastRemoval=removeObservation(bundle,observation.id);bundle=lastRemoval.bundle;if(editingObservationId===observation.id)cancelEdit();hasUnsavedChanges=true;render();$('undo-observation').hidden=false;status('case-status','Observation removed from this case. You can undo this removal; its source remains recorded.');}catch(error){status('case-status',error.message,true);}});
    actions.append(edit,remove);row.append(place,basis,el('td',observation.as_of),value,citation,actions); body.append(row);
  }
  results.append(wrap);
  for (const summary of seriesSummary(bundle)) {
    const card = el('article',null,'series-card'); card.append(el('h3',`${summary.last.locality} / ${BASES[summary.last.price_basis]}`),el('p',`${summary.id} · ${summary.last.methodology}`));
    if (summary.count < 2) card.append(el('p','One observation. Change and annualised change are unavailable until another comparable date is supplied.'));
    else {
      const facts = el('div',null,'series-summary');
      for (const [value,label] of [[`${number(summary.change_pct)}%`,'Change across supplied observations'],[`${number(summary.annualised_pct)}%`,'Annualised change across supplied dates']]) {const item = el('span'); item.append(el('strong',value),el('span',label)); facts.append(item);}
      card.append(facts,drawSeries(summary,bundle.observations.filter(row=>row.series_id===summary.id).sort((a,b)=>a.as_of.localeCompare(b.as_of))));
      card.append(el('p','Computed within this submitted series only. This is not a market-wide appreciation estimate or a forecast.'));
    }
    seriesRoot.append(card);
  }
}
function renderPlanning() {
  $('planning-count').textContent = `${planning.length} record${planning.length===1?'':'s'}`;
  const root = $('planning-results'); root.replaceChildren();
  if (!planning.length) {root.append(el('p','No planning records added. Record the relevant plan, amendment and area reference from the competent authority.', 'quiet'));return;}
  for (const record of planning) {
    const card = el('article',null,'planning-record'), place = places.find(item=>item.id===record.district_id);
    card.append(el('h3',record.area_reference),el('p',`Recorded designation: ${record.land_use}`),anchor(record.document_title,record.source_url),el('p',record.notes),el('small',`${place?.name ?? record.district_id} · source date ${record.as_of} · researcher-recorded, not independently verified`)); root.append(card);
  }
}
const scenarioLabels = {price_inr:'Purchase price',debt_inr:'Debt at purchase',annual_appreciation_pct:'Annual appreciation (%)',annual_interest_pct:'Annual interest (%)',annual_carry_pct:'Annual carrying cost (%)',entry_cost_pct:'Entry cost (%)',exit_cost_pct:'Exit cost (%)',exit_haircut_pct:'Exit haircut (%)',months:'Holding period (months)'};
function renderScenario() {
  const root = $('scenario-results'); root.replaceChildren(); if (!scenarioResult) return;
  const metrics = el('div',null,'scenario-results');
  for (const [key,label] of [['net_sale_inr','Net sale proceeds before debt'],['equity_profit_inr','Equity profit / loss'],['equity_contributed_inr','Total equity contributed'],['terminal_funding_shortfall_inr','Additional funding needed at exit']]) {
    const card = el('div',null,'scenario-metric'); card.append(el('small',label),el('strong',money(scenarioResult[key]))); metrics.append(card);
  }
  root.append(metrics);
  const details = table(['Component','INR'],'Arithmetic from your assumptions; no market forecast is used.');
  for (const [key,label] of [['gross_value_inr','Assumed gross value at exit'],['entry_cost_inr','Entry costs'],['interest_inr','Interest paid during holding'],['carrying_inr','Carrying costs'],['selling_cost_inr','Selling costs'],['equity_returned_inr','Equity returned after debt']]) {const tr=el('tr');tr.append(el('th',label),el('td',money(scenarioResult[key]),'numeric')); details.body.append(tr);}
  root.append(details.wrap); const limits=el('ul',null,'scenario-limits');scenarioResult.limitations.forEach(line=>limits.append(el('li',line)));root.append(limits);
}
function render() {renderPrices(); renderPlanning(); renderScenario(); updateSourceChoice(); setExportAvailability();}

function editObservation(observation) {
  editingObservationId=observation.id;const form=$('observation-form');
  for(const [key,value] of Object.entries(observation)){const input=form.elements.namedItem(key);if(input)input.value=String(value);}
  $('source-choice').value=observation.source_id;toggleSourceFields();$('price-entry').open=true;$('save-observation').textContent='Save record changes';$('cancel-edit').hidden=false;
  status('observation-status','Editing this observation. Its ID is retained when you save.');form.elements.namedItem('value').focus();
}
function cancelEdit() {editingObservationId=null;$('observation-form').reset();$('save-observation').textContent='Add reviewed record';$('cancel-edit').hidden=true;toggleSourceFields();}
$('cancel-edit').addEventListener('click',()=>{cancelEdit();status('observation-status','Edit cancelled. The stored observation is unchanged.');});
$('undo-observation').addEventListener('click',()=>{try{if(!lastRemoval)return;bundle=restoreObservation(bundle,lastRemoval);lastRemoval=null;$('undo-observation').hidden=true;hasUnsavedChanges=true;render();status('case-status','Removed observation restored.');}catch(error){status('case-status',`Cannot restore: ${error.message}`,true);}});

$('observation-form').addEventListener('submit', event => {
  event.preventDefault();
  try {
    const editing=editingObservationId;
    bundle = editing ? replaceObservation(bundle,editing,fields(event.currentTarget),crypto.randomUUID()) : appendObservation(bundle,fields(event.currentTarget),crypto.randomUUID());
    if(editing)cancelEdit();hasUnsavedChanges = true; render();
    status('observation-status',editing?'Observation updated. Its source and comparison basis were checked again.':'Observation added. Enter another comparable date or export your case.'); status('case-status', 'Case updated in this tab. Download the case to keep your work.');
  } catch(error) {status('observation-status',error.message,true);}
});
$('planning-form').addEventListener('submit', event => {
  event.preventDefault();
  try {planning.push(planningFromFields(fields(event.currentTarget),district));hasUnsavedChanges=true;renderPlanning();setExportAvailability();event.currentTarget.reset();status('planning-status','Planning record added with its source date and researcher-recorded status.');status('case-status','Case updated in this tab. Download the case to keep your work.');}
  catch(error){status('planning-status',error.message,true);}
});
$('scenario-form').addEventListener('submit', event => {
  event.preventDefault();
  try {scenarioResult=scenarioFromFields(fields(event.currentTarget));hasUnsavedChanges=true;renderScenario();setExportAvailability();status('scenario-status','Calculated from your assumptions. Results are separate from the price evidence.');status('case-status','Scenario updated. Download the case to keep its assumptions.');}
  catch(error){scenarioResult=null;renderScenario();setExportAvailability();status('scenario-status',error.message,true);}
});
// A changed assumption invalidates the previous result until recalculated.
$('scenario-form').addEventListener('input',()=>{if(scenarioResult){scenarioResult=null;renderScenario();setExportAvailability();status('scenario-status','Inputs changed. Calculate again to update the result.');hasUnsavedChanges=true;}});

function contextQuery() {return workspaceQuery(imageState,{id:district?.id,offset:0});}
function syncContextURL() {
  const query=contextQuery(); history.replaceState(null,'',`${location.pathname}?${query}`); $('open-geography').href=`/banking/geography/?${query}`;
}
function swipe() {const value=Number($('context-swipe').value);$('context-image-before').style.clipPath=`inset(0 ${100-value}% 0 0)`;$('context-swipe').setAttribute('aria-valuetext',`${value}% earlier, ${100-value}% later image`);}
$('context-swipe').addEventListener('input',swipe);
async function loadContext() {
  const generation=++imageGeneration;displayedImagery=null;
  const images=[$('context-image-before'),$('context-image-after')];images.forEach(image=>{image.hidden=true;image.removeAttribute('src');});
  $('context-before-label').textContent='';$('context-after-label').textContent='';$('context-empty').hidden=false;$('context-swipe').disabled=true;
  if(!district){$('context-empty').textContent='Choose a district to load dated satellite context.';return;}
  const before=$('context-before').value,after=$('context-after').value;
  if(!validDate(before)||!validDate(after)||before>=after){$('context-empty').textContent='Choose two valid ordered image dates.';status('context-status','Earlier image must precede the later image, with no future dates.',true);return;}
  imageState={...imageState,before,after};syncContextURL();$('context-empty').textContent='Loading both dated NASA images…';status('context-status','Retrieving satellite context. Cloud and swath gaps may remain.');
  try {
    const box=[...imageState.bbox];
    const requestedURLs=[imageURL(before,box),imageURL(after,box)], placeName=district.name;
    await Promise.all(requestedURLs.map(url=>new Promise((resolve,reject)=>{
      const probe=new Image();
      const timer=setTimeout(()=>{probe.onload=null;probe.onerror=null;probe.src='';reject(new Error('Satellite images timed out. Retry or choose other dates.'));},30000);
      probe.onload=()=>{clearTimeout(timer);probe.onload=null;probe.onerror=null;resolve();};
      probe.onerror=()=>{clearTimeout(timer);probe.onload=null;probe.onerror=null;reject(new Error('Satellite context is unavailable for these dates.'));};
      probe.src=url;
    })));
    if(generation!==imageGeneration)return;
    displayedImagery={provider:'NASA GIBS',layer:LAYER,before,after,bbox:box};images.forEach((image,index)=>{image.src=requestedURLs[index];image.alt=`NASA Terra MODIS landscape context for ${placeName}, requested ${index===0?before:after}`;image.hidden=false;});$('context-empty').hidden=true;$('context-swipe').disabled=false;swipe();
    $('context-before-label').textContent=before;$('context-after-label').textContent=after;
    const viewport=$('context-image-before').parentElement;viewport.style.aspectRatio=String((box[2]-box[0])/(box[3]-box[1]));
    status('context-status',`Images requested for ${before} and ${after}. Each record below keeps its own source date.`);
  }catch(error){if(generation!==imageGeneration)return;images.forEach(image=>image.hidden=true);$('context-empty').textContent='Images unavailable. Your evidence records are unaffected.';status('context-status',error.message,true);}
}
function paintCatalogue() {
  drawCatalogue($('indian-catalogue'), {question: catalogueQuestion, onQuestion(next){catalogueQuestion=next; paintCatalogue();}, onDraft(id){
    const draft=$('catalogue-draft');
    try {draft.hidden=false; draft.textContent=draftText(id, district, $('context-before').value, $('context-after').value, new Date().toISOString().slice(0,10)); status('case-status','Search draft prepared from the published collection identifier and the district extent. It stays on this page. No token is attached and Bhoonidhi is not called.');}
    catch(error){draft.hidden=false; draft.textContent=error.message; status('case-status', error.message, true);}
  }});
  $('catalogue-place').textContent=district?`${district.name}, ${district.state}. The catalogue stays national. A search draft can use this 2021 district extent, and it is not sent.`:'National catalogue. Choose a district to draft a scene search for that extent. This page does not query Bhoonidhi.';
}
function setDistrict(place, preserveViewport=false) {
  district=place;$('district-input').value=place?`${place.name}, ${place.state}`:'';
  $('context-heading').textContent=place?place.name:'District context';$('context-state').textContent=place?`${place.state} · 2021 district extent`:'Choose a district to frame the imagery.';
  const draft=$('catalogue-draft'); draft.hidden=true; draft.textContent='';
  paintCatalogue();
  if(place&&!preserveViewport){const frame=frameSelection({id:place.id,districts:[{id:place.id}]},places);if(frame)imageState.bbox=frame.bbox;}
  syncContextURL();loadContext();
}
$('district-form').addEventListener('submit',event=>{event.preventDefault();const query=$('district-input').value.trim().toLowerCase();const matches=places.filter(place=>`${place.name}, ${place.state}`.toLowerCase()===query||place.name.toLowerCase()===query||place.id===query);if(matches.length!==1){status('case-status',matches.length?'Choose the full district and state; this name occurs more than once.':'Choose a district from the suggestions.',true);return;}setDistrict(matches[0]);status('case-status','District context updated. Price locations and planning records retain their own references.');});
$('image-context-form').addEventListener('submit',event=>{event.preventDefault();loadContext();});
$('share-context').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(`https://liquilens.in/banking/real-assets/?${contextQuery()}`);status('case-status','Geographic context copied. Price records, planning notes and assumptions are not in the link.');}catch{status('case-status','Copy the browser address to share geographic context only.');}});

function currentPack() {return casePack({district,bundle,planning,scenarioResult,imagery:displayedImagery,places});}
function printableCase(pack) {
  const html=el('html');html.lang='en';const head=el('head'),meta=el('meta');meta.setAttribute('charset','utf-8');const title=el('title',`LiquiLens land research: ${pack.district?.name??'research case'}`);
  const style=el('style','body{font:14px/1.5 Arial,sans-serif;color:#142c3f;max-width:1100px;margin:auto;padding:30px}table{border-collapse:collapse;width:100%;font-size:11px}th,td{padding:7px;border-bottom:1px solid #cad8e2;text-align:left;vertical-align:top}h1{font-size:28px}h2{margin-top:26px}a{color:#17617a}small{display:block;color:#536b7b}tr{break-inside:avoid}thead{display:table-header-group}@media print{body{padding:0;font-size:11px}table{font-size:9px}}@page{size:A4;margin:15mm}');head.append(meta,title,style);html.append(head);const body=el('body');html.append(body);
  body.append(el('small','LiquiLens / Land and planning research'),el('h1',pack.district?`${pack.district.name}, ${pack.district.state}`:'Land research case'),el('p',`Researcher-supplied case. Exported ${pack.generated_at}. Use your browser’s Print command to save a PDF.`));
  body.append(el('h2','Price evidence'));
  if(bundle.observations.length){const t=table(['Place','Basis','Date','Value','Source']);for(const o of bundle.observations){const source=bundle.sources.find(s=>s.id===o.source_id),r=el('tr'),c=el('td');c.append(anchor(source.title,source.url),el('small',`${source.locator}; rights ${source.rights}; retrieved ${source.retrieved_at}`));r.append(el('td',`${o.locality} (${o.city_id})`),el('td',BASES[o.price_basis]),el('td',o.as_of),el('td',`${number(o.value)} ${o.unit}`),c);t.body.append(r);}body.append(t.wrap);}else body.append(el('p','No price observations supplied.'));
  body.append(el('h2','Planning records'));for(const p of planning){body.append(el('h3',p.area_reference),el('p',`${p.land_use} / ${p.as_of} / ${p.district_id}`),anchor(p.document_title,p.source_url),el('p',p.notes),el('small','Researcher-recorded. Not a confirmation of title or development permission.'));}if(!planning.length)body.append(el('p','No planning records supplied.'));
  body.append(el('h2','Satellite context'));body.append(el('p',pack.imagery_context?`NASA GIBS / Terra MODIS. Image dates ${pack.imagery_context.before} and ${pack.imagery_context.after}. View [west, south, east, north]: ${pack.imagery_context.bbox.join(', ')}. District context is not parcel geometry.`:'No successfully loaded imagery was available for this export.'));
  if(scenarioResult){body.append(el('h2','User-assumption scenario'));const t=table(['Assumption','Value']);for(const key of SCENARIO_FIELDS){const r=el('tr');r.append(el('th',scenarioLabels[key]),el('td',number(scenarioResult.inputs[key])));t.body.append(r);}body.append(t.wrap,el('p',`Net sale proceeds ${money(scenarioResult.net_sale_inr)}; equity profit / loss ${money(scenarioResult.equity_profit_inr)}; total equity contributed ${money(scenarioResult.equity_contributed_inr)}; exit funding shortfall ${money(scenarioResult.terminal_funding_shortfall_inr)}.`));scenarioResult.limitations.forEach(line=>body.append(el('p',line)));}
  body.append(el('h2','Interpretation and open checks'));const limits=el('ul');LIMITS.forEach(line=>limits.append(el('li',line)));body.append(limits);body.append(el('p','District viewport attribution: geoBoundaries 2021 IND ADM2 / Open Database License 1.0.'),anchor('Boundary provenance','https://liquilens.in/banking/geography/places-source.json'));
  return '<!doctype html>'+html.outerHTML;
}
function download(kind) {
  try{const pack=currentPack();let type='application/json',extension='json',content;
    if(kind==='case')content=JSON.stringify(pack,null,2);else if(kind==='evidence')content=JSON.stringify(bundle,null,2);else if(kind==='csv'){content=csv(bundle);type='text/csv;charset=utf-8';extension='csv';}else{content=printableCase(pack);type='text/html;charset=utf-8';extension='html';}
    const url=URL.createObjectURL(new Blob([content],{type})),a=el('a');a.href=url;a.download=`liquilens-land-${kind}-${district?.id??'case'}.${extension}`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);if(kind==='case')hasUnsavedChanges=false;
    status('case-status',kind==='print'?'Printable brief downloaded. Open it and use Print to save a PDF.':`${kind==='case'?'Research case':kind==='evidence'?'RealAssets-compatible evidence': 'Observation CSV'} downloaded. Source and scenario meanings remain separate.`);
  }catch(error){status('case-status',error.message,true);}
}
for(const kind of ['case','evidence','csv','print'])$(`export-${kind}`).addEventListener('click',()=>download(kind));
$('import-case').addEventListener('change',async event=>{
  const fileInput=event.currentTarget,file=fileInput.files?.[0];if(!file)return;
  try{if(file.size>1024*1024)throw new Error('Choose a JSON file no larger than 1 MiB.');await directoryReady;const input=JSON.parse(await file.text());
    let next;if(input.schema===SCHEMA)next=validateCase(input,{places});else next={evidence:validateBundle(input),planning:[],scenario:null,district:null,imagery_context:null};
    if((bundle.observations.length||planning.length||scenarioResult)&&!confirm('Replace the current case with this file? Download the existing case first if you want to keep it.'))return;
    bundle=next.evidence;planning=next.planning;scenarioResult=next.scenario;hasUnsavedChanges=false;lastRemoval=null;$('undo-observation').hidden=true;cancelEdit();
    if(next.imagery_context){imageState={bbox:next.imagery_context.bbox,before:next.imagery_context.before,after:next.imagery_context.after};$('context-before').value=imageState.before;$('context-after').value=imageState.after;}
    setDistrict(next.district?places.find(p=>p.id===next.district.id):null,Boolean(next.imagery_context));
    if(scenarioResult)for(const key of SCENARIO_FIELDS)$('scenario-form').elements.namedItem(key).value=String(scenarioResult.inputs[key]);
    else $('scenario-form').reset();render();status('case-status',`Imported ${bundle.observations.length} price observations and ${planning.length} planning records. Scenario results were recalculated from supplied inputs. Sources were not fetched.`);
  }catch(error){status('case-status',`Import rejected: ${error.message}`,true);}finally{fileInput.value='';}
});
const registry=el('div',null,'source-register');for(const source of SOURCES){const item=el('article');const h=el('h3');h.append(anchor(source.name,source.url));item.append(h,el('p',`${source.kind} / ${source.coverage}`),el('p',source.access,'access-state'),el('p',source.note));registry.append(item);}$('source-register-results').append(registry);
for(const input of document.querySelectorAll('input[type=date]'))input.max=new Date().toISOString().slice(0,10);
$('context-before').value=imageState.before;$('context-after').value=imageState.after;
render();
paintCatalogue();
directoryReady=fetch(new URL('../geography/places.json',import.meta.url),{credentials:'omit'}).then(async response=>{if(!response.ok)throw new Error('District directory unavailable.');const rows=await response.json();if(!Array.isArray(rows)||rows.length!==735||rows.some(row=>!row.id?.startsWith('in-dist-')||typeof row.name!=='string'||typeof row.state!=='string'||row.boundary_vintage!=='2021'))throw new Error('District directory could not be verified.');places=rows;const list=$('land-districts');for(const place of places){const option=el('option');option.value=`${place.name}, ${place.state}`;list.append(option);}const selected=places.find(p=>p.id===initialSelection);if(selected)setDistrict(selected,new URLSearchParams(location.search).has('view'));else if(initialSelection)status('case-status','Choose a district for land research. The previous state or lender selection is not a parcel or price location.');return places;}).catch(error=>{status('case-status',`${error.message} Reload before importing a full case or adding planning context.`,true);return [];});
addEventListener('beforeunload',event=>{if(hasUnsavedChanges){event.preventDefault();event.returnValue='';}});
addEventListener('pagehide',()=>{imageGeneration++;});
