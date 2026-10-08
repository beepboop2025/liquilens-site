import {element as el, link, readJSON, dateText, csv, download} from './core.mjs';
import {MONITOR_API, PRIORITIES, TYPES, STATES, monitorModel, monitorDetail, monitorRows, monitorCSVRows} from './monitor-model.mjs';

/** One public presentation for the homepage preview and complete review workspace. */
class InstitutionMonitor extends HTMLElement {
  connectedCallback() {
    if (this.started) return;
    this.started=true; this.page=0; this.model=null; this.selected=null; this.generation=0;
    this.preview=this.hasAttribute('preview'); this.pageSize=this.preview?5:10;
    this.classList.add('institution-monitor');
    this.replaceChildren();
    const heading=el('div',undefined,'monitor-heading');
    heading.append(el('h2',this.preview?'What needs an institution review?':'Institution review queue'),
      el('p','Dated disclosures, changes and missing evidence across banks, NBFCs and microfinance lenders.'));
    this.append(heading);
    this.summary=el('dl',undefined,'monitor-summary');this.summary.setAttribute('aria-label','Institution monitoring coverage');
    for(const label of ['Tracked institutions','Some current reviewed fields','Deterioration review','Visibility gaps']) {
      const item=el('div');item.append(el('dt',label),el('dd','—'));this.summary.append(item);
    }
    this.append(this.summary);
    this.notice=el('p','Loading the public monitoring register…','monitor-notice');this.notice.setAttribute('role','status');this.append(this.notice);
    const toolbar=el('div',undefined,'monitor-toolbar');
    const control=(label,input)=>{const wrapper=el('label',label);wrapper.append(input);toolbar.append(wrapper);return input;};
    this.search=el('input');this.search.type='search';this.search.placeholder='Name or identifier';
    control('Search monitored institutions',this.search);
    const select=(label,values)=>{const input=el('select');for(const [value,name] of Object.entries(values)){const option=el('option',name);option.value=value;input.append(option);}return control(label,input);};
    this.priority=select('Review priority',{all:'All review priorities',...PRIORITIES});
    this.type=select('Institution type',{all:'All institution types',...TYPES});
    this.refreshButton=el('button','Refresh register','rw-button');this.refreshButton.type='button';
    this.exportButton=el('button','Export visible results','rw-button');this.exportButton.type='button';this.exportButton.disabled=true;
    toolbar.append(this.refreshButton,this.exportButton);
    if(this.preview){this.search.parentElement.hidden=true;this.priority.parentElement.hidden=true;this.type.parentElement.hidden=true;this.exportButton.hidden=true;}
    this.append(toolbar);
    const scroll=el('div',undefined,'monitor-scroll');scroll.tabIndex=0;scroll.setAttribute('aria-label','Institution review results');
    const table=el('table');const caption=el('caption','Review priority is a request to inspect evidence, not a credit rating.');table.append(caption);
    const head=el('thead'),tr=el('tr');for(const label of ['Institution','Review priority','Reporting period','Evidence gaps']){const cell=el('th',label);cell.scope='col';tr.append(cell);}head.append(tr);
    this.rows=el('tbody');table.append(head,this.rows);scroll.append(table);this.append(scroll);
    this.resultCount=el('p','','monitor-count');this.resultCount.setAttribute('role','status');this.append(this.resultCount);
    this.pager=el('div',undefined,'monitor-toolbar');
    this.previous=el('button','Previous results','rw-button');this.next=el('button','Next results','rw-button');
    for(const button of [this.previous,this.next]){button.type='button';button.disabled=true;this.pager.append(button);}this.pager.hidden=this.preview;this.append(this.pager);
    this.detail=el('section',undefined,'monitor-detail');this.detail.hidden=true;this.detail.setAttribute('aria-label','Selected institution evidence');this.append(this.detail);
    const boundary=el('p','These counts overlap. Current fields do not imply complete coverage or institutional safety. Alerts require human review; they do not change scores or authorize credit.','monitor-boundary');
    this.append(boundary);
    if(this.preview)this.append(link('Open the full institution monitor','/banking/monitoring/'));
    else this.append(link('Read the source register',`${MONITOR_API}/watchlist`));
    this.search.addEventListener('input',()=>this.filter());this.priority.addEventListener('change',()=>this.filter());this.type.addEventListener('change',()=>this.filter());
    this.previous.addEventListener('click',()=>{this.page--;this.clearDetail();this.renderRows();});
    this.next.addEventListener('click',()=>{this.page++;this.clearDetail();this.renderRows();});
    this.refreshButton.addEventListener('click',()=>void this.refresh());
    this.exportButton.addEventListener('click',()=>{if(this.model)download(`liquilens-institution-review-${this.model.asOf}.csv`,csv(monitorCSVRows(this.model,this.visible())));});
    void this.refresh();
  }
  disconnectedCallback(){this.request?.abort();this.detailRequest?.abort();this.started=false;}
  visible(){return this.model?monitorRows(this.model,{query:this.search.value,priority:this.priority.value,type:this.type.value}):[];}
  clearDetail(){this.detailRequest?.abort();this.selected=null;this.detail.hidden=true;this.detail.replaceChildren();}
  filter(){this.page=0;this.clearDetail();this.renderRows();}
  renderRows(){
    const rows=this.visible();this.page=Math.max(0,Math.min(this.page,Math.max(0,Math.ceil(rows.length/this.pageSize)-1)));
    this.rows.replaceChildren();
    for(const row of rows.slice(this.page*this.pageSize,(this.page+1)*this.pageSize)){
      const tr=el('tr'),name=el('td');
      if(this.preview)name.append(link(row.name,`/banking/monitoring/?institution=${encodeURIComponent(row.slug)}`));
      else {const button=el('button',row.name,'monitor-record');button.type='button';button.dataset.institution=row.slug;button.setAttribute('aria-pressed',String(this.selected===row.slug));button.addEventListener('click',()=>void this.select(row));name.append(button);}
      name.append(el('small',TYPES[row.institution_type]));
      const priority=el('td');priority.append(el('span',PRIORITIES[row.priority],`monitor-priority monitor-priority--${row.priority}`),el('small',STATES[row.status]));
      tr.append(name,priority,el('td',dateText(row.latest_period)),el('td',`${row.gaps.length} missing or overdue`));this.rows.append(tr);
    }
    if(!rows.length){const tr=el('tr'),cell=el('td',this.model?'No records match these filters. This does not establish that institutions are safe.':'The monitoring register is not available yet.');cell.colSpan=4;tr.append(cell);this.rows.append(tr);}
    const start=rows.length?this.page*this.pageSize+1:0,end=Math.min(rows.length,(this.page+1)*this.pageSize);
    this.resultCount.textContent=this.model?`Showing ${start}–${end} of ${rows.length} matching records; ${this.model.counts.tracked} tracked. Review cutoff ${dateText(this.model.asOf)}.`:'';
    this.previous.disabled=this.page===0;this.next.disabled=end>=rows.length;this.exportButton.disabled=!rows.length;
  }
  async refresh(){
    if(this.request)return;
    const controller=new AbortController();this.request=controller;this.refreshButton.disabled=true;
    this.notice.textContent='Checking the complete source register…';this.notice.setAttribute('role','status');
    const timer=setTimeout(()=>controller.abort(),15000);
    try{
      const model=monitorModel(await readJSON(`${MONITOR_API}/watchlist`,{signal:controller.signal}));
      if(!this.isConnected)return;
      this.model=model;this.generation++;this.clearDetail();this.renderRows();
      const values=[model.counts.tracked,model.counts.current,model.counts.deterioration,model.counts.gaps];
      this.summary.querySelectorAll('dd').forEach((node,i)=>{node.textContent=String(values[i]);});
      this.notice.textContent=`Review cutoff ${dateText(model.asOf)}. Filing periods remain attached to each record; refreshing does not make the underlying evidence newer.`;
      if(!this.preview){const slug=new URL(location.href).searchParams.get('institution');const row=model.rows.find(r=>r.slug===slug);if(row)void this.select(row);}
    }catch(error){
      if(this.isConnected){this.notice.setAttribute('role','alert');this.notice.textContent=`${this.model?'Refresh failed. Previously retrieved records remain visible with their original dates.':'The monitoring register is unavailable.'} ${error.name==='AbortError'?'The source request timed out.':error.message}`;this.renderRows();}
    }finally{clearTimeout(timer);this.request=null;this.refreshButton.disabled=false;}
  }
  async select(row){
    this.detailRequest?.abort();const controller=new AbortController();this.detailRequest=controller;
    const generation=this.generation,asOf=this.model.asOf;this.selected=row.slug;
    this.rows.querySelectorAll('.monitor-record').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.institution===row.slug)));
    this.detail.hidden=false;this.detail.setAttribute('aria-busy','true');this.detail.replaceChildren(el('h3',row.name),el('p','Loading the source-bound evidence record…'));
    const timer=setTimeout(()=>controller.abort(),15000);
    try{
      const data=monitorDetail(await readJSON(`${MONITOR_API}/institutions/${row.slug}?as_of=${asOf}`,{signal:controller.signal}),row,asOf);
      if(!this.isConnected||this.detailRequest!==controller||this.generation!==generation)return;
      this.renderDetail(data);
    }catch(error){
      if(this.isConnected&&this.detailRequest===controller&&this.generation===generation){this.detail.replaceChildren(el('h3',row.name),el('p',error.name==='AbortError'?'The evidence request timed out. Select the institution again to retry.':error.message));}
    }finally{clearTimeout(timer);if(this.detailRequest===controller)this.detail.setAttribute('aria-busy','false');}
  }
  renderDetail(data){
    this.detail.replaceChildren(el('h3',data.name),el('p',`${PRIORITIES[data.priority]}. Latest reporting period: ${dateText(data.latest_period)}. Review cutoff: ${dateText(data.as_of)}.`));
    const alerts=el('div');alerts.append(el('h4','Changes requiring review'));
    if(!data.warnings.length)alerts.append(el('p','No deterioration rule is reported for the available evidence. Read the visibility gaps before drawing any conclusion.'));
    for(const warning of data.warnings)alerts.append(el('p',warning.title));this.detail.append(alerts);
    const categories=el('ul',undefined,'monitor-categories');for(const category of data.categories)categories.append(el('li',`${category.label}: ${category.status.replaceAll('_',' ')}`));this.detail.append(categories);
    const facts=el('details');facts.append(el('summary',`Disclosed fields and source clocks (${data.metrics.length})`));
    for(const metric of data.metrics){
      const item=el('article',undefined,'monitor-fact');
      const value=metric.value===null?'Not reported':`${new Intl.NumberFormat('en-GB',{maximumFractionDigits:4}).format(metric.value)} ${metric.unit}`;
      item.append(el('h4',metric.label),el('p',`${value} · ${metric.status.replaceAll('_',' ')}`),el('p',`Reporting period: ${dateText(metric.period_end)}. Publication: ${metric.published_at||'Unknown'}. Known to product: ${metric.available_at||'Unknown'}. Retrieved: ${metric.retrieved_at||'Unknown'}.`));
      if(metric.scope)item.append(el('p',`Statement scope: ${metric.scope}. ${metric.basis||''}`));
      for(const url of metric.sources){const anchor=link(new URL(url).hostname,url);anchor.target='_blank';anchor.rel='noopener noreferrer';item.append(anchor);}facts.append(item);
    }
    this.detail.append(facts);
    const gaps=el('details');gaps.open=true;gaps.append(el('summary',`Missing or overdue evidence (${data.gaps.length})`));
    const list=el('ul');for(const gap of data.gaps)list.append(el('li',gap.reason));gaps.append(list);this.detail.append(gaps);
    const connections=el('p',undefined,'monitor-connections');connections.append(link('Funding conditions in Seiche','https://seiche.info/#money%20markets'),document.createTextNode(' · '),link('Market liquidity in Undertow','https://liquilens-undertow.com/markets/'));
    this.detail.append(connections,el('p','These links provide separate market context. Market depth is not a measure of this institution’s deposit liquidity.','monitor-boundary'),link('Open this source record',`${MONITOR_API}/institutions/${data.slug}?as_of=${data.as_of}`));
  }
}
customElements.define('institution-monitor',InstitutionMonitor);
