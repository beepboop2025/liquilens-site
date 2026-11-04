/** Small DOM fixture for running the real geography event handlers without a browser. */
export class Element {
  constructor(tagName) {
    this.tagName = tagName; this.children = []; this.listeners = {}; this.attributes = {};
    this.value = ''; this.textContent = ''; this.style = {}; this.classList = {add() {}, toggle() {}};
  }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  setAttribute(key, value) { this.attributes[key] = value; }
  removeAttribute(key) { delete this.attributes[key]; }
  addEventListener(type, callback) { this.listeners[type] = callback; }
  focus() { this.focused = true; }
  setPointerCapture() {}
  getBoundingClientRect() { return {width: 700, height: 700}; }
  get firstChild() { return this.children[0]; }
}
export const settle = () => new Promise(resolve => setImmediate(resolve));
export function installDOM(t, ids = []) {
  const nodes = new Map(ids.map(id => [id, new Element('div')]));
  t.mock.method(globalThis, 'fetch', async () => { throw new Error('Unexpected request'); });
  const originals = new Map(['document', 'Image', 'location', 'history'].map(key => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
  globalThis.document = {createElement: tag => new Element(tag), createElementNS: (_, tag) => new Element(tag), getElementById: id => nodes.get(id), addEventListener() {}};
  globalThis.Image = class { decode() { return Promise.resolve(); } };
  t.after(() => { for (const [key, descriptor] of originals) { if (descriptor) Object.defineProperty(globalThis, key, descriptor); else delete globalThis[key]; } });
  return nodes;
}
