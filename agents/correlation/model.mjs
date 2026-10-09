export const API = 'https://api.seiche.info/noisefloor';
export const MAX_BYTES = 750000;
export const CONTEXTS = {
  liquilens: 'Compare like-for-like peer funding measures. A common mode is research context, not a credit score.',
  seiche: 'Compare aligned funding changes. Review tenors, calendars and currencies before treating benchmarks as comparable.',
  undertow: 'Compare the same liquidity measure across venues or segments. Keep spreads, depth and exit-cost measures distinct.',
  riptide: 'Inspect shared scenario factors. Scenario similarity does not establish live losses or validated portfolio risk.',
  trading_agents: 'Inspect shared strategy-return exposure. The first point establishes the interval start; retain net-cost and vintage assumptions.',
  palimpsest: 'Inspect movement in source coverage counts. Coverage correlation is not an economic risk factor or an adjustment for sampling bias.',
};
export function parseRequest(text) {
  if (new TextEncoder().encode(text).length > MAX_BYTES) throw new Error('The request exceeds the 750 KB browser limit. Use a smaller panel or run locally.');
  let request;
  try { request = JSON.parse(text); } catch { throw new Error('Enter valid JSON or load an example.'); }
  if (!request || typeof request !== 'object' || !Array.isArray(request.series) || typeof request.as_of !== 'string') throw new Error('The request needs series and an explicit as_of timestamp.');
  return request;
}
export function assessment(body) {
  if (body?.schema !== 'noisefloor.spectral-assessment.v1' || body.execution_authority !== false || !Array.isArray(body.series) || !Array.isArray(body.windows)) throw new Error('Unexpected assessment contract. No result is displayed.');
  const latest = body.latest?.status === 'assessed' ? body.latest : null;
  const reasons = [...(body.reasons || []), ...body.series.flatMap(s => (s.reasons || []).map(r => `${s.id}: ${r}`)), ...(body.latest?.reasons || [])];
  return {latest, reasons};
}
export async function post(route, request, fetcher = fetch) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20000);
  try {
    const response = await fetcher(API + route, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(request), signal:controller.signal, credentials:'omit', referrerPolicy:'no-referrer'});
    const body = await response.json();
    if (!response.ok) throw new Error(`API ${response.status}: ${typeof body.error === 'string' ? body.error : body.error?.message || 'request refused'}`);
    return body;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('The request timed out. No assessment is available; retry explicitly.');
    throw error;
  } finally { clearTimeout(timer); }
}
