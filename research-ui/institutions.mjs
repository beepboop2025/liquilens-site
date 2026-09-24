import {API,reviewModel} from '../banking/model.mjs';
import {BANK_STATES,SECTORS,bankCoverage,filterRows,dateOnly,dateText,finite,sourceUrl,csv,download,readJSON,element as el,link,statusBadge,sourceDetails,visibleRefresh} from './core.mjs';
import {restoreView,rememberView} from './view-state.mjs';

const root=document.querySelector('[data-institution-workspace]');
if(root){
  const byId=id=>document.getElementById(id);
  let storage;try{storage=localStorage;}catch{/* Storage may be disabled. */}
  const initialView=restoreView(location.href,storage);
  let coverage=null,selected=initialView.institution,selectedData=null,detailRequest=null,coverageRequest=null,disposed=false;
  const comparisons=new Map();
  const comparisonIds=new Set(initialView.comparison);
  byId('institution-search').value=initialView.query;
  byId('institution-status').value=initialView.status;
  byId('institution-sector').value=initialView.sector;
  const choices=()=>({query:byId('institution-search').value,status:byId('institution-status').value,sector:byId('institution-sector').value});
  const visible=()=>coverage?filterRows(coverage.rows,choices()):[];
  const notice=byId('institution-notice');
  const remember=()=>{history.replaceState(null,'',rememberView(location.href,{...choices(),institution:selected,comparison:[...comparisonIds]},storage));window.dispatchEvent(new Event('research:context-changed'));};
  function reconcileSelection(){
    const rows=visible();renderRows();remember();
    if(rows.some(row=>row.slug===selected))return;
    if(rows.length){void select(rows[0].slug);return;}
    detailRequest?.abort();detailRequest=null;selected=null;selectedData=null;
    byId('institution-detail').setAttribute('aria-busy','false');
    byId('institution-detail').replaceChildren(el('h2','No matching institution'),el('p','Adjust the filters to inspect a disclosure record.'));
    remember();
  }
  function renderRows(){
    const rows=visible(),body=byId('institution-rows');body.replaceChildren();
    for(const row of rows){
      const tr=el('tr');tr.dataset.selected=String(row.slug===selected);
      const heading=el('th');heading.scope='row';const button=el('button',row.name);button.type='button';button.setAttribute('aria-pressed',String(row.slug===selected));button.addEventListener('click',()=>void select(row.slug,true));
      heading.append(button,el('small',SECTORS[row.sector]));
      const state=el('td');state.append(statusBadge(BANK_STATES[row.status],row.status));
      tr.append(heading,state,el('td',dateText(row.period)));body.append(tr);
    }
    if(!rows.length){const tr=el('tr'),cell=el('td','No institutions match these filters. Try a different name, sector or evidence state.','rw-empty');cell.colSpan=3;tr.append(cell);body.append(tr);}
    byId('institution-count').textContent=`${rows.length} of ${coverage?.rows.length||0} dossiers shown. Select an institution to inspect its disclosures.`;
    byId('institution-export').disabled=!rows.length;
  }
  function table(headers,rows){
    const scroll=el('div',undefined,'rw-table-scroll'),table=el('table',undefined,'rw-table'),head=el('thead'),tr=el('tr');
    headers.forEach(title=>{const cell=el('th',title);cell.scope='col';tr.append(cell);});head.append(tr);table.append(head);
    const body=el('tbody');for(const row of rows){const tr=el('tr');row.forEach((value,index)=>{const cell=el(index?'td':'th',value);if(!index)cell.scope='row';tr.append(cell);});body.append(tr);}table.append(body);scroll.append(table);return scroll;
  }
  function chart(data){
    const points=(Array.isArray(data.history)?data.history:[]).filter(row=>dateOnly(row.period_end)&&row.metrics?.gnpa_pct?.status==='observed'&&row.metrics.gnpa_pct.unit==='percent'&&finite(row.metrics.gnpa_pct.value)!==null).map(row=>({date:row.period_end,value:row.metrics.gnpa_pct.value})).sort((a,b)=>a.date.localeCompare(b.date));
    if(points.length<2)return el('p','At least two comparable GNPA observations are needed for a trend. The disclosure table below retains the available record.');
    const figure=el('figure',undefined,'rw-chart'),ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 460 150');svg.setAttribute('role','img');
    const title=document.createElementNS(ns,'title');title.textContent='Disclosed gross non-performing assets as a percentage: '+points.map(p=>`${p.date}: ${p.value}%`).join('; ');svg.append(title);
    const maximum=Math.max(...points.map(p=>p.value),.1)*1.15,start=Date.parse(points[0].date),end=Date.parse(points.at(-1).date);
    if(start===end)return el('p','The available observations have the same reporting date. Read the history table for details.');
    const coordinates=points.map(p=>[38+(Date.parse(p.date)-start)/(end-start)*409,124-p.value/maximum*102]);
    for(const level of [0,maximum/2,maximum]){const y=124-level/maximum*102,line=document.createElementNS(ns,'line');for(const [key,value]of Object.entries({x1:38,x2:450,y1:y,y2:y,stroke:'var(--research-line)'}))line.setAttribute(key,String(value));svg.append(line);const text=document.createElementNS(ns,'text');text.setAttribute('x','30');text.setAttribute('y',String(y+4));text.setAttribute('text-anchor','end');text.setAttribute('fill','var(--research-muted)');text.setAttribute('font-size','10');text.textContent=level.toFixed(1)+'%';svg.append(text);}
    const path=document.createElementNS(ns,'path');path.setAttribute('d',coordinates.map(([x,y],i)=>`${i?'L':'M'}${x.toFixed(2)},${y.toFixed(2)}`).join(' '));path.setAttribute('fill','none');path.setAttribute('stroke','var(--research-accent)');path.setAttribute('stroke-width','2');svg.append(path);
    for(const [i,[x,y]] of coordinates.entries()){const point=document.createElementNS(ns,'circle');point.setAttribute('cx',String(x));point.setAttribute('cy',String(y));point.setAttribute('r','3');point.setAttribute('fill','var(--research-accent)');const title=document.createElementNS(ns,'title');title.textContent=`${points[i].date}: ${points[i].value}%`;point.append(title);svg.append(point);}
    const caption=el('figcaption');caption.append(el('span',dateText(points[0].date)),el('span','Gross NPAs / advances (%)'),el('span',dateText(points.at(-1).date)));figure.append(svg,caption);return figure;
  }
  function renderComparison(){
    const section=byId('institution-comparison');section.hidden=comparisons.size===0;section.replaceChildren();if(!comparisons.size)return;
    section.append(el('h2','Compare disclosed evidence'));
    const rows=[...comparisons.values()].map(({data,model})=>[model.name,dateText(data.period_end),BANK_STATES[data.status],...model.metrics.slice(0,3).map(m=>m.value)]);
    section.append(table(['Institution','Reporting date','Evidence','Gross NPA','Net NPA','Capital ratio'],rows),el('p','Reporting dates and definitions may differ. This comparison does not rank institutions or establish creditworthiness.','rw-caption'));
    if([...comparisons.values()].some(row=>row.refreshFailed))section.append(el('p','Some comparison records could not be refreshed. Their previously retrieved, dated evidence remains visible.','rw-caption'));
    const clear=el('button','Clear comparison','rw-button');clear.type='button';clear.addEventListener('click',()=>{comparisonIds.clear();comparisons.clear();remember();renderComparison();if(selectedData)renderDetail(selectedData);});section.append(clear);
  }
  async function refreshComparisons(){
    for(const slug of [...comparisonIds]){
      if(!coverage?.rows.some(row=>row.slug===slug)){comparisonIds.delete(slug);comparisons.delete(slug);continue;}
      try{
        const data=await readJSON(`${API}/institutions/${encodeURIComponent(slug)}?include_history=true`,{signal:AbortSignal.timeout(15000)});
        if(!disposed&&comparisonIds.has(slug))comparisons.set(slug,{data,model:reviewModel(data)});
      }catch{if(comparisons.has(slug))comparisons.get(slug).refreshFailed=true;}
    }
    if(!disposed){remember();renderComparison();}
  }
  function renderDetail(data){
    const model=reviewModel(data),panel=byId('institution-detail');
    const openDetails=[...panel.querySelectorAll('details')].map(item=>item.open);
    panel.replaceChildren();panel.setAttribute('aria-busy','false');selectedData=data;
    panel.append(statusBadge(model.status,data.status),el('h2',model.name),el('p',model.clock,'rw-clock'));
    const metrics=el('dl',undefined,'rw-metrics');
    for(const metric of model.metrics.slice(0,6)){const item=el('div'),value=el('dd',metric.value,metric.value==='Not disclosed'?'rw-missing':undefined);item.append(el('dt',metric.label),value);metrics.append(item);}panel.append(metrics);
    panel.append(el('h3','Disclosed asset quality'),chart(data));
    const history=el('details',undefined,'rw-detail');history.append(el('summary',`Reporting history (${model.history.length} periods)`));
    history.append(model.history.length?table(['Reporting period','Gross NPA','Net NPA','Capital ratio'],model.history.map(row=>[dateText(row.period),...row.values])):el('p','No comparable historical periods were supplied.'));panel.append(history);
    const metricsDetail=el('details',undefined,'rw-detail');metricsDetail.append(el('summary','All disclosed metrics and definitions'),table(['Metric','Disclosed value'],model.metrics.map(row=>[row.label,row.value])));for(const row of model.metrics.filter(row=>row.basis))metricsDetail.append(el('p',`${row.label}: ${row.basis}`));panel.append(metricsDetail);
    const sources=el('details',undefined,'rw-detail');sources.append(el('summary',`Source documents (${model.sources.length})`));const list=el('ul');for(const url of model.sources){const item=el('li'),anchor=link(new URL(url).hostname,url);anchor.target='_blank';anchor.rel='noopener noreferrer';item.append(anchor);list.append(item);}sources.append(list);if(!model.sources.length)sources.append(el('p','No source links were supplied by this record.'));panel.append(sources);
    panel.append(sourceDetails('Evidence limits and open questions',[...model.limits,model.regulatory]));
    const actions=el('div',undefined,'rw-actions'),compare=el('button',comparisonIds.has(selected)?'Remove from comparison':'Add to comparison','rw-button');compare.type='button';compare.addEventListener('click',()=>{if(comparisonIds.has(selected)){comparisonIds.delete(selected);comparisons.delete(selected);}else if(comparisonIds.size<3){comparisonIds.add(selected);comparisons.set(selected,{data,model});}else {notice.textContent='Three institutions are already selected. Clear the comparison before adding another.';return;}remember();renderComparison();renderDetail(data);});
    const raw=link('Open structured JSON',`${API}/institutions/${encodeURIComponent(selected)}?include_history=true`);raw.target='_blank';raw.rel='noopener noreferrer';actions.append(compare,raw);panel.append(actions);
    const related=el('div',undefined,'rw-related');related.append(el('h3','Continue this review'),el('p','Connect these disclosures to funding conditions and market liquidity.'));
    related.append(link('Funding conditions in Seiche →',`https://seiche.info/?institution=${encodeURIComponent(selected)}#money%20markets`),document.createTextNode(' · '),link('Market evidence in Undertow →',`https://liquilens-undertow.com/?institution=${encodeURIComponent(selected)}`));panel.append(related);
    panel.querySelectorAll('details').forEach((item,index)=>{item.open=Boolean(openDetails[index]);});
  }
  async function select(slug,interaction=false){
    if(!coverage?.rows.some(row=>row.slug===slug))return;
    const previous=selected===slug?selectedData:null;
    selected=slug;if(!previous)selectedData=null;detailRequest?.abort();const controller=new AbortController();detailRequest=controller;
    remember();renderRows();const panel=byId('institution-detail');panel.setAttribute('aria-busy','true');if(!previous)panel.replaceChildren(el('p','Loading the selected institution’s disclosure record…','rw-loading'));
    const timer=setTimeout(()=>controller.abort(),15000);
    try{const data=await readJSON(`${API}/institutions/${encodeURIComponent(slug)}?include_history=true`,{signal:controller.signal});if(!disposed&&detailRequest===controller)renderDetail(data);}
    catch{if(!disposed&&detailRequest===controller){panel.setAttribute('aria-busy','false');if(previous){notice.textContent='The record refresh failed. The previously retrieved, dated disclosure remains visible.';}else{panel.replaceChildren(el('h2','This record could not be loaded'),el('p','Coverage remains visible in the table. Retry the disclosure request or open its structured record.'));const retry=el('button','Retry record','rw-button');retry.type='button';retry.addEventListener('click',()=>void select(slug));panel.append(retry);}}}
    finally{clearTimeout(timer);}
    if(interaction&&matchMedia('(max-width:760px)').matches)panel.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion:reduce)').matches?'instant':'smooth',block:'start'});
  }
  async function refresh(){
    if(coverageRequest)return;
    const controller=new AbortController();coverageRequest=controller;byId('institution-refresh').disabled=true;const timer=setTimeout(()=>controller.abort(),15000);
    try{
      const next=bankCoverage(await readJSON(`${API}/coverage`,{signal:controller.signal}));if(disposed)return;coverage=next;
      byId('coverage-total').textContent=String(next.rows.length);byId('coverage-accepted').textContent=String(next.counts.observed);byId('coverage-stale').textContent=String(next.counts.stale);byId('coverage-historical').textContent=String(next.counts.historical);
      notice.textContent=`Coverage as of ${dateText(next.asOf)}. Checked ${new Date().toLocaleTimeString('en-GB',{timeZone:'UTC',hour:'2-digit',minute:'2-digit'})} UTC. Filing dates and evidence states remain unchanged by a refresh.`;notice.removeAttribute('role');
      renderRows();const rows=visible();if(rows.length)void select(rows.some(row=>row.slug===selected)?selected:rows[0].slug);else reconcileSelection();
      void refreshComparisons();
    }catch(error){if(!disposed){notice.setAttribute('role','alert');notice.textContent=(coverage?'The refresh failed; the previously retrieved coverage remains visible. ':'Coverage is unavailable. ')+(error.name==='AbortError'?'The source request timed out.':error.message);}}
    finally{clearTimeout(timer);coverageRequest=null;if(!disposed)byId('institution-refresh').disabled=false;}
  }
  for(const id of ['institution-search','institution-status','institution-sector'])byId(id).addEventListener(id==='institution-search'?'input':'change',reconcileSelection);
  byId('institution-refresh').addEventListener('click',()=>void refresh());
  byId('institution-export').addEventListener('click',()=>download('liquilens-institution-coverage.csv',csv([['Institution','Sector','Evidence state','Reporting date','Coverage as of'],...visible().map(row=>[row.name,SECTORS[row.sector],BANK_STATES[row.status],row.period,coverage.asOf])])));
  const stop=visibleRefresh(refresh);
  addEventListener('pagehide',()=>{disposed=true;stop();detailRequest?.abort();coverageRequest?.abort();},{once:true});
  readJSON('/articles/feed.json',{signal:AbortSignal.timeout(12000)}).then(feed=>{
    if(disposed||feed.version!=='https://jsonfeed.org/version/1.1'||!Array.isArray(feed.items))return;
    const items=feed.items.filter(row=>sourceUrl(row.url)&&new URL(row.url).origin==='https://liquilens.in'&&typeof row.title==='string'&&Number.isFinite(Date.parse(row.date_published))).sort((a,b)=>Date.parse(b.date_published)-Date.parse(a.date_published)).slice(0,3);
    if(!items.length)return;const target=byId('institution-activity');target.replaceChildren();
    for(const row of items){const article=el('article'),time=el('time',dateText(row.date_published.slice(0,10)));time.dateTime=row.date_published;const heading=el('h3');heading.append(link(row.title,row.url));article.append(time,heading,el('p',String(row.summary||'').slice(0,240)));target.append(article);}
  }).catch(()=>{});
}
