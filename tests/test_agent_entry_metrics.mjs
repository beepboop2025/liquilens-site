import test from "node:test";
import assert from "node:assert/strict";
import {entryEvent, createTracker} from "../agents/metrics.mjs";

test("only bounded setup intent reaches the transport, once per page", async () => {
  const calls = [];
  const track = createTracker({send: async (...args) => {calls.push(args); return {status:202};}});
  assert.equal(await track(entryEvent("config_copied", "hermes")), true);
  assert.equal(await track(entryEvent("config_copied", "hermes")), false);
  assert.equal(await track(entryEvent("config_copied", "private-account")), false);
  assert.equal(await track("prompt=private"), false);
  assert.equal(calls.length, 1);
  const [url, options] = calls[0];
  assert.equal(url, "https://api.liquilens.in/api/events");
  assert.deepEqual(JSON.parse(options.body), {surface:"agent_starter",event:"hermes_config_copied"});
  assert.equal(options.credentials, "omit");
  assert.equal(options.referrerPolicy, "no-referrer");
});

test("verification, privacy preference and failed transport cannot create repeated events", async () => {
  let calls = 0;
  const send = async () => {calls++; throw Error("offline");};
  for (const option of [{verification:true},{privacyOptOut:true}]) {
    assert.equal(await createTracker({...option,send})("kit_download_requested"), false);
  }
  assert.equal(calls, 0);
  const track = createTracker({send});
  assert.equal(await track("kit_download_requested"), false);
  assert.equal(await track("kit_download_requested"), false);
  assert.equal(calls, 1);
});
