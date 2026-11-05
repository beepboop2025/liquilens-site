// Price evidence and planning observations retain independent bases and clocks.
import {LAYER, validDate, validBox} from '../geography/imagery-model.mjs';
export const SCHEMA = 'liquilens.land-research.v1';
export const BASES = {registered_sale:'Registered sale',circle_rate:'DLC / circle rate',asking_price:'Asking price',valuation:'Reported valuation',housing_index:'Housing price index'};
export const UNITS = {'INR/sqm':1,'INR/sqft':0.09290304,'INR/sqyd':0.83612736};
export const LIMITS = [
  'Price records are supplied by the researcher. Validation checks structure, not authenticity or permission.',
  'Asking prices, registered consideration, administrative rates and valuations remain separate evidence.',
  'Housing indices describe a city series; they do not value a land parcel.',
  'District imagery and 2021 district extents provide regional context, not cadastral boundaries or legal land-use determinations.',
  'Planning records need confirmation from the competent authority. A plan label or satellite image does not establish development permission.',
];
export const SOURCES = [
  {name:'Rajasthan Urban GIS',url:'https://rajdharaa.rajasthan.gov.in/citizenudh/',kind:'Planning and cadastral context',coverage:'Rajasthan',access:'Official viewing portal',note:'Master plans, khasra and scheme layers are for viewing. Authenticate land use against the relevant authority’s records.'},
  {name:'Jaipur Development Authority',url:'https://lsg.urban.rajasthan.gov.in/content/raj/udh/jda---jaipur/en/town-planning/master-development--plan-2025.html',kind:'Published planning documents',coverage:'Jaipur',access:'Official document register',note:'Check amendments and applicable zonal plans. The published 2025 plan is not a statement of current parcel permission.'},
  {name:'Rajasthan e-Panjiyan',url:'https://epanjiyan.rajasthan.gov.in/',kind:'DLC and registration references',coverage:'Rajasthan',access:'Reviewed record entry',note:'Match locality, use, units and effective date. Administrative valuation and transaction consideration have different meanings.'},
  {name:'Rajasthan RERA',url:'https://rera.rajasthan.gov.in/',kind:'Project disclosures',coverage:'Rajasthan',access:'Reviewed record entry',note:'A project registration or promoter declaration does not independently establish title or solvency.'},
  {name:'NHB RESIDEX',url:'https://residex.nhbonline.org.in/',kind:'City housing indices',coverage:'Publisher-defined city series',access:'Feed not connected',note:'Retain the index base and methodology. Reproduction rights need separate confirmation.'},
  {name:'RBI Database on Indian Economy',url:'https://data.rbi.org.in/DBIE/#/dbie/home',kind:'Published housing-price indices',coverage:'Publisher-defined city series',access:'Official data portal',note:'Housing-price context is separate from parcel or locality pricing. Preserve base years and revisions.'},
  {name:'Bhoonidhi',url:'https://bhoonidhi.nrsc.gov.in/bhoonidhi/home.html',kind:'Indian Earth-observation discovery',coverage:'Scene-dependent',access:'API access required',note:'Open and priced products have their own access and licensing conditions. No Bhoonidhi scenes are loaded in this workspace.'},
  {name:'IN-SPACe',url:'https://www.inspace.gov.in/',kind:'Technical facilitation and programme access',coverage:'Programme-dependent',access:'Facilitation route',note:'IN-SPACe is a facilitation body, not an imagery or property-price feed.'},
];

export function safeURL(value) {
  if(typeof value!=='string'||value.length>4096||/[\s\\]/.test(value))return null;
  try {const u=new URL(value); if(!['https:','http:'].includes(u.protocol)||u.username||u.password||!u.hostname.includes('.')||u.port&&!['80','443'].includes(u.port)||/^(localhost|127\.|10\.|192\.168\.|169\.254\.)/i.test(u.hostname)||/\.(local|internal|invalid)$/i.test(u.hostname))return null;return u.href;}catch{return null;}
}
function text(value,label,max=2000){if(typeof value!=='string'||!value.trim()||value.length>max||/[\x00-\x1f]/.test(value))throw new Error(`${label} needs valid text.`);return value.trim();}
function identifier(value){if(typeof value!=='string'||! /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value))throw new Error('Use letters, digits, dots or hyphens for identifiers.');return value;}
function finite(value,label,min=0,max=1e15){if(typeof value!=='number'||!Number.isFinite(value)||value<min||value>max)throw new Error(`${label} is outside its allowed range.`);return value;}
export function date(value){if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value)||!Number.isFinite(Date.parse(value))||new Date(value).toISOString().slice(0,10)!==value||value>new Date().toISOString().slice(0,10))throw new Error('Use a valid observation date no later than today.');return value;}
function keys(row,expected,label){if(!row||typeof row!=='object'||Array.isArray(row)||Object.keys(row).sort().join('|')!==[...expected].sort().join('|'))throw new Error(`${label} has missing or unsupported fields.`);}
export function emptyBundle(){return {schema:'realassets.evidence.v1',sources:[],observations:[],links:[]};}

export function validateBundle(input) {
  keys(input,['schema','sources','observations','links'],'Evidence file');
  if(input.schema!=='realassets.evidence.v1'||!Array.isArray(input.sources)||input.sources.length>2000||!Array.isArray(input.observations)||input.observations.length>10000||!Array.isArray(input.links))throw new Error('Use a bounded RealAssets evidence file.');
  if(input.links.length)throw new Error('This land workspace does not import lender/charge relationships. Use the private RealAssets module for those records.');
  const sources=new Map(),ids=new Set(),series=new Map(),seen=new Set();
  for(const s of input.sources){
    keys(s,['id','title','url','published_at','retrieved_at','rights','locator'],'Source');
    identifier(s.id);if(ids.has(s.id))throw new Error('Duplicate record ID.');ids.add(s.id);
    text(s.title,'Source title');text(s.locator,'Document locator');
    if(!safeURL(s.url))throw new Error('Provide a public HTTP(S) source URL without credentials.');
    if(!['licensed','user_owned','restricted','unknown'].includes(s.rights))throw new Error('Use reviewed records with an explicit rights status. Synthetic records are not accepted here.');
    if(typeof s.retrieved_at!=='string'||!/(Z|[+-]\d\d:\d\d)$/.test(s.retrieved_at)||!Number.isFinite(Date.parse(s.retrieved_at))||Date.parse(s.retrieved_at)>Date.now())throw new Error('Source retrieval needs a valid past timestamp with timezone.');
    if(s.published_at!==null){date(s.published_at);if(s.published_at>new Date(s.retrieved_at).toISOString().slice(0,10))throw new Error('Publication cannot be after retrieval.');}
    sources.set(s.id,s);
  }
  for(const o of input.observations){
    keys(o,['id','source_id','city_id','locality','asset_type','price_basis','series_id','comparison_basis','unit','value','as_of','evidence_type','sample_size','methodology'],'Observation');
    for(const key of ['id','source_id','city_id','series_id'])identifier(o[key]);
    if(ids.has(o.id))throw new Error('Duplicate record ID.');ids.add(o.id);
    const source=sources.get(o.source_id);if(!source)throw new Error('Observation source is missing.');
    date(o.as_of);if(o.as_of>new Date(source.retrieved_at).toISOString().slice(0,10))throw new Error('Observation cannot be after source retrieval.');
    text(o.locality,'Locality');text(o.methodology,'Methodology');
    if(!['land','housing'].includes(o.asset_type)||!Object.hasOwn(BASES,o.price_basis)||!['reported','declared'].includes(o.evidence_type)||!['same_asset','published_index','reviewed_comparables'].includes(o.comparison_basis))throw new Error('Unsupported observation basis.');
    finite(o.value,'Price or index',1e-12);finite(o.sample_size,'Sample count',1,1000000);if(!Number.isInteger(o.sample_size))throw new Error('Sample count must be an integer.');
    const index=o.price_basis==='housing_index';
    if(index){if(o.unit!=='index'||o.asset_type!=='housing'||o.comparison_basis!=='published_index'||! /\bbase\b.*\b(?:19|20)\d{2}/i.test(o.methodology))throw new Error('Housing indices need index units, housing, a published-index comparison and a stated base year.');}
    else if(!Object.hasOwn(UNITS,o.unit)||o.comparison_basis==='published_index')throw new Error('Prices need a supported area unit and comparable-price basis.');
    if(o.comparison_basis==='reviewed_comparables'&&o.sample_size<2)throw new Error('Reviewed comparables need at least two samples.');
    const signature=JSON.stringify([o.city_id,o.locality,o.asset_type,o.price_basis,o.comparison_basis,o.unit,o.evidence_type,o.methodology]);
    if(series.has(o.series_id)&&series.get(o.series_id)!==signature)throw new Error('A series cannot mix places, price bases, units or methodologies. Use a separate series.');
    series.set(o.series_id,signature);const k=o.series_id+'|'+o.as_of;if(seen.has(k))throw new Error('Duplicate series date. Resolve revisions before importing.');seen.add(k);
  }
  return structuredClone(input);
}

export function normalisePrice(row){return Object.hasOwn(UNITS,row.unit)&&row.price_basis!=='housing_index'?row.value/UNITS[row.unit]:null;}
export function seriesSummary(bundle){
  const valid=validateBundle(bundle),groups=new Map();
  for(const row of valid.observations){if(!groups.has(row.series_id))groups.set(row.series_id,[]);groups.get(row.series_id).push(row);}
  return [...groups.entries()].map(([id,rows])=>{rows.sort((a,b)=>a.as_of.localeCompare(b.as_of));const first=rows[0],last=rows.at(-1);const years=(Date.parse(last.as_of)-Date.parse(first.as_of))/(365.25*86400000);return {id,first,last,count:rows.length,change_pct:years>0?(last.value/first.value-1)*100:null,annualised_pct:years>0?(Math.pow(last.value/first.value,1/years)-1)*100:null};});
}
export function scenario(input){
  const names=['price_inr','debt_inr','annual_appreciation_pct','annual_interest_pct','annual_carry_pct','entry_cost_pct','exit_cost_pct','exit_haircut_pct','months'];
  keys(input,names,'Scenario');
  finite(input.price_inr,'Purchase price',1);finite(input.debt_inr,'Debt',0,input.price_inr);finite(input.annual_appreciation_pct,'Appreciation',-99,100);
  for(const key of ['annual_interest_pct','annual_carry_pct','entry_cost_pct','exit_cost_pct','exit_haircut_pct'])finite(input[key],key,0,99.99);
  finite(input.months,'Holding months',1,120);if(!Number.isInteger(input.months))throw new Error('Holding months must be a whole number.');
  const p=input.price_inr,years=input.months/12,gross=p*(1+input.annual_appreciation_pct/100)**years;
  const discounted=gross*(1-input.exit_haircut_pct/100),selling=discounted*input.exit_cost_pct/100;
  const interest=input.debt_inr*input.annual_interest_pct/100*years,carry=p*input.annual_carry_pct/100*years,entry=p*input.entry_cost_pct/100;
  const net=discounted-selling,terminal=net-input.debt_inr,shortfall=Math.max(0,-terminal),contributed=p-input.debt_inr+entry+interest+carry+shortfall;
  return {classification:'user_assumption_scenario',inputs:structuredClone(input),gross_value_inr:gross,net_sale_inr:net,interest_inr:interest,carrying_inr:carry,entry_cost_inr:entry,selling_cost_inr:selling,terminal_funding_shortfall_inr:shortfall,equity_contributed_inr:contributed,equity_returned_inr:Math.max(0,terminal),equity_profit_inr:net-p-entry-interest-carry,limitations:['User assumptions, not a forecast or valuation.','Bullet loan; interest and carrying costs paid from equity. Principal repaid at exit.','No rent, tax, construction draws, refinancing or legal-cost model.']};
}
export function validatePlanning(rows){if(!Array.isArray(rows)||rows.length>200)throw new Error('Planning records must be a bounded list.');return rows.map(row=>{keys(row,['district_id','area_reference','document_title','land_use','as_of','source_url','notes','status'],'Planning record');identifier(row.district_id);for(const k of ['area_reference','document_title','land_use'])text(row[k],k);date(row.as_of);if(!safeURL(row.source_url)||row.status!=='researcher_recorded')throw new Error('Planning entries require a source URL and researcher-recorded status.');if(typeof row.notes!=='string'||row.notes.length>2000)throw new Error('Planning notes are too long.');return structuredClone(row);});}
function imageryContext(input){
  if(input===null||input===undefined)return null;
  keys(input,['provider','layer','before','after','bbox'],'Imagery context');
  if(input.provider!=='NASA GIBS'||input.layer!==LAYER||!validDate(input.before)||!validDate(input.after)||input.before>input.after||!validBox(input.bbox))throw new Error('Imagery context must contain valid ordered dates and the displayed NASA layer.');
  return structuredClone(input);
}
export function casePack({district,bundle,planning=[],scenarioResult=null,imagery,places}){
  if(district&&places){district=places.find(row=>row.id===district.id);if(!district)throw new Error('Unknown district.');}
  const records=validatePlanning(planning);
  if(places&&records.some(row=>!places.some(place=>place.id===row.district_id)))throw new Error('Planning entry has an unknown district.');
  return {schema:SCHEMA,generated_at:new Date().toISOString(),classification:'researcher_supplied_case',district:district?{id:district.id,name:district.name,state:district.state,bbox:district.bbox,boundary_vintage:district.boundary_vintage}:null,imagery_context:imageryContext(imagery),evidence:validateBundle(bundle),planning:records,scenario:scenarioResult?scenario(scenarioResult.inputs):null,limitations:[...LIMITS]};
}
export function validateCase(input,{places}={}){
  keys(input,['schema','generated_at','classification','district','imagery_context','evidence','planning','scenario','limitations'],'Research case');
  if(input.schema!==SCHEMA||input.classification!=='researcher_supplied_case'||!Array.isArray(places)||!places.length)throw new Error('Use a supported research case and the verified district catalogue.');
  if(typeof input.generated_at!=='string'||!/(Z|[+-]\d\d:\d\d)$/.test(input.generated_at)||!Number.isFinite(Date.parse(input.generated_at))||Date.parse(input.generated_at)>Date.now())throw new Error('Case creation time is invalid.');
  if(input.district!==null&&(!input.district||typeof input.district.id!=='string'))throw new Error('Case district is invalid.');
  if(input.scenario!==null&&(!input.scenario||typeof input.scenario.inputs!=='object'))throw new Error('Scenario inputs are missing.');
  const result=casePack({district:input.district,bundle:input.evidence,planning:input.planning,scenarioResult:input.scenario,imagery:input.imagery_context,places});
  result.generated_at=input.generated_at;
  return result;
}
export function csv(bundle){const quote=v=>'"'+String(v??'').replaceAll('"','""').replace(/^[=+@\t\r-]/,"'$&")+'"';const fields=['id','city_id','locality','asset_type','price_basis','unit','value','as_of','series_id','source_id','methodology'];return [fields,...validateBundle(bundle).observations.map(o=>fields.map(k=>o[k]))].map(r=>r.map(quote).join(',')).join('\r\n');}
