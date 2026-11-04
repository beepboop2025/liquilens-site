import {initEvidence} from './evidence.mjs';
import {PRESETS, imageURL, moveBox, stateFromURL, validDate} from './imagery-model.mjs';

const $ = id => document.getElementById(id);
const state = stateFromURL(location.search);
function syncRegion() {
  $('region').value = Object.entries(PRESETS).find(([, preset]) => preset.bbox.every((value, index) => value === state.bbox[index]))?.[0] || 'custom';
}
syncRegion();
let generation = 0, controller, objectURLs = [], pointer;
const today = new Date().toISOString().slice(0, 10);
for (const key of ['before', 'after']) { $(key).value = state[key]; $(key).max = today; }
const images = [$('image-before'), $('image-after')];
const viewer = $('viewer');
function status(message, error = false) { $('image-status').textContent = message; $('image-status').classList.toggle('error', error); }
function swipe() {
  const value = Number($('swipe').value);
  images[0].style.clipPath = `inset(0 ${100 - value}% 0 0)`;
  $('divider').style.left = `${value}%`;
  $('swipe-value').textContent = `${value}%`;
  $('swipe').setAttribute('aria-valuetext', `${value}% earlier image, ${100 - value}% later image`);
}
function clearImages() {
  for (const img of images) { img.hidden = true; img.removeAttribute('src'); }
  for (const url of objectURLs) URL.revokeObjectURL(url);
  objectURLs = [];
  $('divider').hidden = true;
  $('before-label').textContent = ''; $('after-label').textContent = '';
}
async function fetchImage(url, signal) {
  const response = await fetch(url, {signal, mode: 'cors', credentials: 'omit'});
  if (!response.ok || !response.headers.get('content-type')?.startsWith('image/')) throw new Error('Image service unavailable for this date or view.');
  const reader = response.body.getReader(), chunks = []; let size = 0;
  try {
    while (true) {
      const {done, value} = await reader.read(); if (done) break;
      size += value.byteLength;
      if (size > 8 * 1024 * 1024) { await reader.cancel(); throw new Error('Image exceeds the display limit. Zoom to a smaller area.'); }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  return new Blob(chunks, {type: response.headers.get('content-type')});
}
async function loadImages() {
  const version = ++generation;
  controller?.abort(); clearImages();
  $('share').disabled = true; $('swipe').disabled = true;
  viewer.setAttribute('aria-busy', 'false');
  $('image-empty').hidden = false;
  const before = $('before').value, after = $('after').value;
  if (!validDate(before) || !validDate(after) || before >= after) {
    $('image-empty').textContent = 'Choose valid comparison dates, then Load images.';
    status('Choose two valid dates, with the earlier image before the later one.', true); return;
  }
  state.before = before; state.after = after;
  controller = new AbortController();
  const current = controller;
  const timer = setTimeout(() => current.abort(), 30000);
  clearImages(); viewer.setAttribute('aria-busy', 'true');
  $('image-empty').hidden = false; $('image-empty').textContent = 'Retrieving both dated images…';
  $('swipe').disabled = true;
  status('Loading both images from NASA GIBS…');
  const bbox = [...state.bbox];
  viewer.style.aspectRatio = String((bbox[2] - bbox[0]) / (bbox[3] - bbox[1]));
  $('view-coordinates').textContent = `View: ${bbox.map(n => n.toFixed(2)).join(', ')} (west, south, east, north)`;
  const urls = [];
  try {
    const blobs = await Promise.all([before, after].map(date => fetchImage(imageURL(date, bbox), current.signal)));
    if (version !== generation) return;
    for (const blob of blobs) urls.push(URL.createObjectURL(blob));
    const decoded = urls.map(url => {const image = new Image(); image.src = url; return image.decode();});
    await Promise.all(decoded);
    if (version !== generation) return;
    objectURLs = [...urls];
    $('share').disabled = false;
    images.forEach((img, i) => { img.src = urls[i]; img.alt = `NASA Terra MODIS true-colour imagery requested for ${i === 0 ? before : after}, view ${bbox.join(', ')}`; img.hidden = false; });
    $('before-label').textContent = `Earlier · ${before}`; $('after-label').textContent = `Later · ${after}`;
    $('image-empty').hidden = true; $('divider').hidden = false; $('swipe').disabled = false; swipe();
    status(`Images loaded for ${before} and ${after}. Swipe to compare; cloud and swath gaps may remain.`);
    const query = new URLSearchParams(location.search);
    query.set('before', before); query.set('after', after); query.set('view', bbox.join(','));
    history.replaceState(null, '', `${location.pathname}?${query}`);
  } catch (error) {
    if (version !== generation) return;
    current.abort(); clearImages();
    const message = error.name === 'AbortError' ? 'Image request timed out. Try Load images again or choose another date.' : `${error.message} Try Load images again or choose another date.`;
    status(message, true); $('image-empty').textContent = 'Images unavailable. Choose another date or retry.';
  } finally {
    clearTimeout(timer);
    for (const url of urls) if (!objectURLs.includes(url)) URL.revokeObjectURL(url);
    if (version === generation) viewer.setAttribute('aria-busy', 'false');
  }
}
function navigate(scale = 1, dx = 0, dy = 0) { state.bbox = moveBox(state.bbox, scale, dx, dy); syncRegion(); loadImages(); }
$('image-form').addEventListener('submit', event => {event.preventDefault(); loadImages();});
$('region').addEventListener('change', event => {state.bbox = [...PRESETS[event.target.value].bbox]; loadImages();});
$('swipe').addEventListener('input', swipe);
$('zoom-in').addEventListener('click', () => navigate(.6));
$('zoom-out').addEventListener('click', () => navigate(1 / .6));
$('reset').addEventListener('click', () => {$('region').value = 'india'; state.bbox = [...PRESETS.india.bbox]; loadImages();});
viewer.addEventListener('keydown', event => {
  const width = state.bbox[2] - state.bbox[0], height = state.bbox[3] - state.bbox[1];
  const actions = {ArrowLeft: [1, -width * .25, 0], ArrowRight: [1, width * .25, 0], ArrowUp: [1, 0, height * .25], ArrowDown: [1, 0, -height * .25], '+': [.6], '=': [.6], '-': [1 / .6]};
  if (actions[event.key]) {event.preventDefault(); navigate(...actions[event.key]);}
});
viewer.addEventListener('pointerdown', event => {if (!event.isPrimary || event.button !== 0) return; pointer = {id: event.pointerId, x: event.clientX, y: event.clientY}; viewer.setPointerCapture(event.pointerId);});
viewer.addEventListener('pointerup', event => {
  if (!pointer || pointer.id !== event.pointerId) return;
  const dx = event.clientX - pointer.x, dy = event.clientY - pointer.y; pointer = null;
  if (Math.hypot(dx, dy) < 10) return;
  const rect = viewer.getBoundingClientRect();
  navigate(1, -dx / rect.width * (state.bbox[2] - state.bbox[0]), dy / rect.height * (state.bbox[3] - state.bbox[1]));
});
viewer.addEventListener('pointercancel', () => {pointer = null;});
$('fullscreen').addEventListener('click', async () => {
  try {if (document.fullscreenElement) await document.exitFullscreen(); else await document.querySelector('.imagery-panel').requestFullscreen();}
  catch {status('Full screen is unavailable in this browser. Use browser zoom to enlarge the view.', true);}
});
document.addEventListener('fullscreenchange', () => {$('fullscreen').textContent = document.fullscreenElement ? 'Exit full screen' : 'Full screen';});
$('share').addEventListener('click', async () => {
  try {await navigator.clipboard.writeText(location.href); status('View link copied, including the displayed dates and area.');}
  catch {status('Copy the address from your browser to share this view.');}
});
initEvidence($('evidence'));
loadImages();
