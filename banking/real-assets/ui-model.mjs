import {scenario, validateBundle, validatePlanning} from './model.mjs';

export function inputNumber(value, label) {
  if (typeof value !== 'string' || !value.trim() || !Number.isFinite(Number(value))) throw new Error(`Enter a number for ${label}. Blank inputs are not zero.`);
  return Number(value);
}

export function appendObservation(bundle, fields, suffix) {
  const next = validateBundle(bundle);
  const sourceId = fields.source_choice === 'new' ? `source-${suffix}` : fields.source_choice;
  if (fields.source_choice === 'new') {
    if (!fields.retrieved_at || !Number.isFinite(Date.parse(fields.retrieved_at))) throw new Error('Enter when you accessed the source.');
    next.sources.push({id: sourceId, title: fields.source_title, url: fields.source_url,
      published_at: fields.published_at || null, retrieved_at: new Date(fields.retrieved_at).toISOString(),
      rights: fields.rights, locator: fields.locator});
  }
  next.observations.push({id: `observation-${suffix}`, source_id: sourceId, city_id: fields.city_id,
    locality: fields.locality, asset_type: fields.asset_type, price_basis: fields.price_basis,
    series_id: fields.series_id, comparison_basis: fields.comparison_basis, unit: fields.unit,
    value: inputNumber(fields.value, 'value'), as_of: fields.as_of, evidence_type: fields.evidence_type,
    sample_size: inputNumber(fields.sample_size, 'sample count'), methodology: fields.methodology});
  return validateBundle(next);
}

export function replaceObservation(bundle, id, fields, suffix) {
  const base = validateBundle(bundle);
  if (!base.observations.some(row => row.id === id)) throw new Error('The observation to edit is no longer in this case.');
  base.observations = base.observations.filter(row => row.id !== id);
  const next = appendObservation(base, fields, suffix);
  next.observations.at(-1).id = id;
  return validateBundle(next);
}

export function removeObservation(bundle, id) {
  const next = validateBundle(bundle), index = next.observations.findIndex(row => row.id === id);
  if (index < 0) throw new Error('The observation is no longer in this case.');
  const [removed] = next.observations.splice(index, 1);
  return {bundle: next, removed, index};
}

export function restoreObservation(bundle, removal) {
  const next = validateBundle(bundle);
  next.observations.splice(Math.min(removal.index, next.observations.length), 0, removal.removed);
  return validateBundle(next);
}

export function planningFromFields(fields, district) {
  if (!district?.id) throw new Error('Choose a district before adding a planning record.');
  return validatePlanning([{district_id: district.id, area_reference: fields.area_reference,
    document_title: fields.document_title, land_use: fields.land_use, as_of: fields.as_of,
    source_url: fields.source_url, notes: fields.notes || '', status: 'researcher_recorded'}])[0];
}

export const SCENARIO_FIELDS = ['price_inr', 'debt_inr', 'annual_appreciation_pct', 'annual_interest_pct', 'annual_carry_pct', 'entry_cost_pct', 'exit_cost_pct', 'exit_haircut_pct', 'months'];
export function scenarioFromFields(fields) {
  return scenario(Object.fromEntries(SCENARIO_FIELDS.map(key => [key, inputNumber(fields[key], key.replaceAll('_', ' '))])));
}
