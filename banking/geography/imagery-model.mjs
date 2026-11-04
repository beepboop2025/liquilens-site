export const LAYER = 'MODIS_Terra_CorrectedReflectance_TrueColor';
export const PRESETS = {
  india: {name: 'India overview', bbox: [66, 5, 99, 38]},
  north: {name: 'North India', bbox: [71, 24, 83, 36]},
  west: {name: 'West India', bbox: [67, 18, 79, 30]},
  east: {name: 'East and northeast India', bbox: [80, 20, 98, 32]},
  south: {name: 'South India', bbox: [72, 6, 85, 19]},
  jaipur: {name: 'Jaipur surroundings', bbox: [74.6, 25.9, 77.1, 28.4]},
};
export function validDate(value, today = new Date().toISOString().slice(0, 10)) {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
    && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value
    && value >= '2015-11-24' && value <= today;
}
export function validBox(box) {
  return Array.isArray(box) && box.length === 4 && box.every(Number.isFinite)
    && box[0] >= -180 && box[2] <= 180 && box[1] >= -85 && box[3] <= 85
    && box[2] - box[0] >= 0.25 && box[2] - box[0] <= 90
    && box[3] - box[1] >= 0.25 && box[3] - box[1] <= 90;
}
export function moveBox(box, scale = 1, dx = 0, dy = 0) {
  if (!validBox(box) || ![scale, dx, dy].every(Number.isFinite) || scale <= 0) throw new Error('Invalid view');
  const width = Math.min(90, Math.max(.25, (box[2] - box[0]) * scale));
  const height = Math.min(90, Math.max(.25, (box[3] - box[1]) * scale));
  const x = Math.min(180 - width / 2, Math.max(-180 + width / 2, (box[0] + box[2]) / 2 + dx));
  const y = Math.min(85 - height / 2, Math.max(-85 + height / 2, (box[1] + box[3]) / 2 + dy));
  return [x - width / 2, y - height / 2, x + width / 2, y + height / 2].map(n => Number(n.toFixed(6)));
}
export function imageURL(date, bbox) {
  if (!validDate(date) || !validBox(bbox)) throw new Error('Choose a valid observation date and map view.');
  const width = 1024, height = Math.min(2048, Math.max(128, Math.round(width * (bbox[3] - bbox[1]) / (bbox[2] - bbox[0]))));
  return `https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?${new URLSearchParams({
    SERVICE: 'WMS', REQUEST: 'GetMap', VERSION: '1.1.1', LAYERS: LAYER, STYLES: '',
    FORMAT: 'image/jpeg', SRS: 'EPSG:4326', BBOX: bbox.join(','), WIDTH: String(width), HEIGHT: String(height), TIME: date,
  })}`;
}
export function stateFromURL(search) {
  const q = new URLSearchParams(search);
  const bbox = q.get('view')?.split(',').map(Number);
  return {bbox: validBox(bbox) ? bbox : [...PRESETS.india.bbox],
    before: validDate(q.get('before')) ? q.get('before') : '2025-11-02',
    after: validDate(q.get('after')) ? q.get('after') : '2026-11-02'};
}
