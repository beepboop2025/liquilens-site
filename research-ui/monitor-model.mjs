import {dateOnly, sourceUrl} from './core.mjs';

export const MONITOR_API = 'https://api.liquilens.in/api/experimental/v1/banking/monitoring';
export const PRIORITIES = Object.freeze({urgent_review:'Deterioration review', evidence_review:'Evidence review', routine_review:'Routine review', historical_archive:'Historical archive'});
export const TYPES = Object.freeze({bank:'Commercial bank', sfb:'Small finance bank', ucb:'Co-operative bank', nbfc:'NBFC', mfi:'Microfinance lender', hfc:'Housing finance company'});
export const STATES = Object.freeze({review_required:'Review required', insufficient_visibility:'Visibility gaps', review_available:'Review available', historical:'Historical'});
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const text = (value, max=500) => typeof value === 'string' && value.length > 0 && value.length <= max;
const count = value => Number.isSafeInteger(value) && value >= 0;
const fail = message => { throw new Error(message || 'The monitoring evidence could not be verified.'); };
const isHash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);

function authority(data, today) {
  if (!object(data) || data.schema !== 'liquilens.institution-monitoring.v1' ||
      data.policy_version !== 'liquilens.institution-monitoring-policy.v1' ||
      data.score_authority !== false || data.training_eligible !== false ||
      data.can_authorize_credit !== false || data.human_review_required !== true ||
      !dateOnly(data.as_of) || data.as_of > today || typeof data.coverage_complete !== 'boolean') fail();
}

function rowCheck(row) {
  if (!object(row) || !text(row.slug,100) || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(row.slug) ||
      !text(row.name,200) || !Object.hasOwn(TYPES,row.institution_type) ||
      !Object.hasOwn(PRIORITIES,row.priority) || !Object.hasOwn(STATES,row.status) ||
      (row.latest_period !== null && !dateOnly(row.latest_period)) || !isHash(row.content_sha256) ||
      typeof row.coverage_complete !== 'boolean' || !Array.isArray(row.warnings) || row.warnings.length > 100 ||
      !Array.isArray(row.gaps) || row.gaps.length > 100 || !Array.isArray(row.categories) || row.categories.length !== 7) fail();
  const ids = new Set();
  for (const category of row.categories) {
    if (!object(category) || !text(category.id,80) || ids.has(category.id) || !text(category.label,200) ||
        !['observed','partial','insufficient_visibility'].includes(category.status)) fail();
    ids.add(category.id);
  }
  for (const warning of row.warnings) {
    if (!object(warning) || !text(warning.title) || !['deterioration','compound_deterioration'].includes(warning.kind)) fail();
  }
  for (const gap of row.gaps) {
    if (!object(gap) || !text(gap.field,100) || !text(gap.reason,2000) || !['unavailable','overdue'].includes(gap.status)) fail();
  }
  if (row.coverage_complete && row.gaps.length) fail();
  if (row.status === 'historical' ? row.priority !== 'historical_archive' : row.priority === 'historical_archive') fail();
}

/** Validate the complete register before showing any aggregate or review count. */
export function monitorModel(data, today=new Date().toISOString().slice(0,10)) {
  authority(data,today);
  if (data.watchlist_basis !== 'All tracked Indian institution records' ||
      !Array.isArray(data.rows) || data.rows.length > 1000 || !Array.isArray(data.not_covered) || data.not_covered.length ||
      !object(data.counts) || data.counts.selected !== data.rows.length || data.counts.tracked !== data.rows.length ||
      data.delivery?.status !== 'review_queue_only' || data.delivery.customer_delivery_verified !== false) fail('The complete monitoring register was not returned.');
  const seen = new Set();
  for (const row of data.rows) {
    rowCheck(row);
    if (seen.has(row.slug) || !count(row.current_metrics) || !count(row.overdue_metrics) ||
        row.review_url !== `/api/experimental/v1/banking/monitoring/institutions/${row.slug}`) fail();
    seen.add(row.slug);
  }
  const counts = {tracked:data.rows.length, current:data.rows.filter(r=>r.current_metrics>0).length,
    deterioration:data.rows.filter(r=>r.warnings.length>0).length, gaps:data.rows.filter(r=>r.gaps.length>0).length};
  if (data.counts.with_current_reviewed_metrics !== counts.current ||
      data.counts.with_deterioration !== counts.deterioration || data.counts.with_visibility_gaps !== counts.gaps ||
      data.coverage_complete !== (data.rows.length>0 && data.rows.every(r=>r.coverage_complete))) fail('Monitoring counts disagree with the evidence records.');
  return {rows:data.rows, counts, asOf:data.as_of, coverageComplete:data.coverage_complete};
}

export function monitorDetail(data, row, asOf, today=new Date().toISOString().slice(0,10)) {
  authority(data,today); rowCheck(data);
  if (data.slug !== row.slug || data.as_of !== asOf || data.content_sha256 !== row.content_sha256) fail('The evidence changed since this list was loaded. Refresh the register before reviewing this record.');
  if (!Array.isArray(data.metrics) || data.metrics.length>1000 ||
      data.validation?.historical_prediction_validated !== false) fail();
  for (const metric of data.metrics) {
    if (!object(metric) || !text(metric.label,500) || !text(metric.unit,80) || !dateOnly(metric.period_end) ||
        !['current','overdue','historical','source_review_hold','conflicting_evidence'].includes(metric.status) ||
        (metric.value !== null && (typeof metric.value !== 'number' || !Number.isFinite(metric.value))) ||
        !Array.isArray(metric.sources) || metric.sources.some(url=>!sourceUrl(url))) fail();
  }
  return data;
}

export function monitorRows(model, {query='', priority='all', type='all'}={}) {
  const terms=query.trim().toLocaleLowerCase('en-US').split(/\s+/).filter(Boolean);
  return model.rows.filter(row=>(priority==='all'||row.priority===priority) &&
    (type==='all'||row.institution_type===type) && terms.every(term=>`${row.name} ${row.slug}`.toLocaleLowerCase('en-US').includes(term)));
}

export function monitorCSVRows(model, rows=model.rows) {
  return [['Institution','Identifier','Type','Review priority','Evidence state','Latest reporting period','Current reviewed fields','Overdue fields','Review alerts','Visibility gaps','Coverage complete','Review cutoff','Evidence record'],
    ...rows.map(row=>[row.name,row.slug,TYPES[row.institution_type],PRIORITIES[row.priority],STATES[row.status],row.latest_period,
      row.current_metrics,row.overdue_metrics,row.warnings.length,row.gaps.length,row.coverage_complete,model.asOf,`${MONITOR_API}/institutions/${row.slug}?as_of=${model.asOf}`])];
}
