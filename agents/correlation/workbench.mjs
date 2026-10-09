import {CONTEXTS, MAX_BYTES, parseRequest, assessment, post} from './model.mjs';
const $ = id => document.getElementById(id);
const element = (tag, text, parent) => {const node = document.createElement(tag); node.textContent = text; if (parent) parent.append(node); return node;};
const fmt = value => Number.isFinite(value) ? value.toFixed(2) : 'unresolved';
const pct = value => Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : 'unresolved';
let inputOrigin = 'Caller-supplied observations; declarations unverified', receipt = null, generation = 0;
const svgElement = (tag, attrs, parent) => { const node = document.createElementNS('http://www.w3.org/2000/svg', tag); for(const [key,value] of Object.entries(attrs)) node.setAttribute(key,String(value)); parent.append(node); return node; };
function chart(parent, title) { parent.replaceChildren(); const svg = svgElement('svg',{viewBox:'0 0 640 260',role:'img'},parent); svgElement('title',{},svg).textContent=title; return svg; }
function spectrum(latest) {
  const {eigenvalues: values, reference: ref} = latest;
  const svg=chart($('spectrum'),'Correlation eigenvalues with the asymptotic independent-data reference band');
  const top=Math.max(...values,ref.upper_edge)*1.14, y=v=>220-v/top*180;
  svgElement('rect',{x:45,y:y(ref.upper_edge),width:560,height:y(ref.lower_edge)-y(ref.upper_edge),fill:'#e4ead4'},svg);
  svgElement('line',{x1:45,x2:605,y1:220,y2:220,stroke:'#92a392'},svg);
  values.forEach((v,i)=>{const x=45+(i+.5)*560/values.length;svgElement('line',{x1:x,x2:x,y1:220,y2:y(v),stroke:'#26634d','stroke-width':Math.min(32,300/values.length)},svg);svgElement('text',{x,y:y(v)-8,'text-anchor':'middle'},svg).textContent=fmt(v);svgElement('text',{x,y:240,'text-anchor':'middle'},svg).textContent=String(i+1);});
  svgElement('text',{x:45,y:18},svg).textContent=`Reference band ${fmt(ref.lower_edge)}–${fmt(ref.upper_edge)} · not a significance test`;
  element('p', 'Eigenvalues, largest first. Shaded region: Marchenko–Pastur reference.', $('spectrum')).className='muted';
}
function showReport(body, origin) {
  const {latest,reasons}=assessment(body);
  $('empty').hidden=true; $('result').hidden=false; $('result-origin').textContent=origin;
  $('result-status').textContent=body.status.replaceAll('_',' ');
  $('result-clock').textContent=`Assessment clock: ${body.as_of} · ${body.alignment.aligned_points} aligned intervals · no filled points`;
  $('reasons').replaceChildren(); reasons.forEach(reason=>element('li',reason,$('reasons')));
  $('metrics').replaceChildren(); $('spectrum').replaceChildren();
  if(latest) { for(const [label,value] of [['Leading variance share',pct(latest.leading_variance_share)],['Effective rank',fmt(latest.effective_rank)],['Modes above reference',String(latest.reference.above_upper_count)]]){const card=element('div','',$('metrics'));card.className='metric';element('strong',value,card);element('span',label,card);} spectrum(latest); }
  const tbody=$('windows').querySelector('tbody');tbody.replaceChildren();
  for(const window of body.windows){const row=element('tr','',tbody);for(const value of [window.window_end,String(window.observations),pct(window.leading_variance_share),fmt(window.effective_rank)])element('td',value,row);}
  $('windows').hidden=!body.windows.length; $('sources').replaceChildren();
  for(const source of body.series)element('p',`${source.id} · ${source.transform} · ${source.unit} · observed ${source.observed_at ?? 'unknown'} · rights ${source.source.rights} · measurement counts: ${source.measurement_coverage.status}${source.warnings.length ? ' · '+source.warnings.join(', ') : ''}`,$('sources'));
  $('report').textContent=JSON.stringify(body,null,2);
}
function clearResult(){generation++;receipt=null;$('result').hidden=true;$('empty').hidden=false;$('status').textContent='';}
function callerInput(){inputOrigin='Caller-supplied observations; declarations unverified';$('input-origin').textContent=inputOrigin;clearResult();}
$('request').addEventListener('input',callerInput);
$('product').addEventListener('change',()=>{$('context').textContent=CONTEXTS[$('product').value];});
const profile=new URL(location.href).searchParams.get('product');if(Object.hasOwn(CONTEXTS,profile))$('product').value=profile;
$('context').textContent=CONTEXTS[$('product').value];
$('load-example').addEventListener('click',async()=>{
  const button=$('load-example');button.disabled=true;clearResult();
  try{const response=await fetch(`examples/${$('product').value}.json`);if(!response.ok)throw new Error('The example could not be loaded.');const request=await response.json();$('request').value=JSON.stringify(request,null,2);inputOrigin=`Synthetic ${$('product').selectedOptions[0].textContent} example`; $('input-origin').textContent=inputOrigin;$('status').textContent='Synthetic example loaded. Press Run to assess it.';}catch(error){$('status').textContent=error.message;}finally{button.disabled=false;}
});
$('file').addEventListener('change',async()=>{const file=$('file').files[0];if(!file)return;callerInput();try{if(file.size>MAX_BYTES)throw new Error('File exceeds the 750 KB browser limit.');const text=await file.text();parseRequest(text);$('request').value=text;}catch(error){$('request').value='';$('status').textContent=error.message;}$('file').value='';});
$('run').addEventListener('click',async()=>{
  clearResult();const button=$('run');button.disabled=true;
  try{const request=parseRequest($('request').value),origin=inputOrigin,runGeneration=generation;$('status').textContent='Assessing the supplied panel…';const body=await post('/v1/spectral/assess',request);if(runGeneration!==generation)return;showReport(body,origin);receipt={schema:'noisefloor.browser-review.v1',origin,request,response:body,received_at:new Date().toISOString(),execution_authority:false};$('status').textContent='Assessment received. Review source visibility and limitations.';}catch(error){$('status').textContent=error.message;}finally{button.disabled=false;}
});
$('download').addEventListener('click',()=>{if(!receipt)return;const url=URL.createObjectURL(new Blob([JSON.stringify(receipt,null,2)],{type:'application/json'}));const a=element('a','');a.href=url;a.download='noisefloor-review.json';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);});
$('simulate').addEventListener('click',async()=>{
  const button=$('simulate');button.disabled=true;$('dyson-chart').replaceChildren();$('dyson-detail').hidden=true;
  try{const seed=Number($('seed').value);if(!Number.isInteger(seed)||seed<0||seed>4294967295)throw new Error('Choose an integer seed between 0 and 4294967295.');$('dyson-status').textContent='Simulating a symmetric Brownian matrix…';const report=await post('/v1/research/dyson',{dimension:Number($('dimension').value),steps:60,dt:0.05,seed});if(report.schema!=='noisefloor.dyson-reference.v1'||report.status!=='synthetic'||report.market_calibrated!==false)throw new Error('Unexpected simulation contract.');
  const paths=report.path,all=paths.flatMap(p=>p.eigenvalues),lo=Math.min(...all),hi=Math.max(...all),last=paths.at(-1).time;
  const svg=chart($('dyson-chart'),'Synthetic ordered eigenvalue paths; horizontal axis is simulation time');const y=v=>220-(v-lo)/(hi-lo)*185;
  svgElement('line',{x1:50,x2:610,y1:y(0),y2:y(0),stroke:'#c3cec0','stroke-dasharray':'4 4'},svg);
  for(let i=0;i<report.parameters.dimension;i++)svgElement('polyline',{points:paths.map(p=>`${50+p.time/last*560},${y(p.eigenvalues[i])}`).join(' '),fill:'none',stroke:`hsl(${145+i*21} 45% 35%)`,'stroke-width':2},svg);
  for(const v of [lo,0,hi])svgElement('text',{x:5,y:y(v)+4},svg).textContent=fmt(v);
  svgElement('text',{x:50,y:245},svg).textContent='Time 0';svgElement('text',{x:555,y:245},svg).textContent=fmt(last);
  $('dyson-report').textContent=JSON.stringify(report,null,2);$('dyson-detail').hidden=false;$('dyson-status').textContent=`Synthetic reference · seed ${seed} · 60 sampled steps · not market-calibrated`;
  }catch(error){$('dyson-status').textContent=error.message;}finally{button.disabled=false;}
});
