import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import test from "node:test";
import vm from "node:vm";

const source = readFileSync(new URL("../access/enquiry-copy.js", import.meta.url), "utf8");

function mount(clipboard) {
  const template = {value: "To: mrinal@liquilens.in\nSubject: Enquiry\nInstitution:",
    focus() { this.focused = true; }, select() { this.selected = true; }};
  const status = {textContent: "Copying the template does not send an email."};
  const button = {hidden: true, addEventListener(event, handler) {
    assert.equal(event, "click"); this.click = handler;
  }};
  // No fetch, storage, beacon or event dispatcher is exposed to the helper.
  vm.runInNewContext(source, {navigator: {clipboard}, document: {
    querySelector: () => button,
    getElementById: id => id === "enquiry-template" ? template : status,
  }});
  return {button, template, status};
}

test("native clipboard receives the visible template without sending an enquiry", async () => {
  let copied;
  const page = mount({writeText: async value => { copied = value; }});
  assert.equal(page.button.hidden, false);
  await page.button.click();
  assert.equal(copied, page.template.value);
  assert.match(page.status.textContent, /before sending/);
  assert.equal(page.template.selected, undefined);
});

for (const [reason, clipboard] of [
  ["denied", {writeText: async () => { throw new Error("NotAllowedError"); }}],
  ["unavailable", undefined],
]) {
  test(`clipboard ${reason} leaves the complete template focused and selected`, async () => {
    const page = mount(clipboard);
    await page.button.click();
    assert.equal(page.template.focused, true);
    assert.equal(page.template.selected, true);
    assert.match(page.status.textContent, /use your device's Copy command/);
    assert.ok(!page.status.textContent.includes("Template copied"));
  });
}
