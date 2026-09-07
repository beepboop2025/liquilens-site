import test from "node:test";
import assert from "node:assert/strict";
import {SOURCES, acquisitionSource, questionLink, telegramLink} from "../start/acquisition.mjs";

test("arbitrary, duplicate and absent query values never become acquisition labels", () => {
  for (const search of ["", "?utm_source=private@example.org", "?utm_source=instagram&email=secret&prompt=private", "?utm_source=instagram&fbclid=secret"]) {
    assert.ok(SOURCES.includes(acquisitionSource(search)));
    assert.ok(!acquisitionSource(search).includes("secret"));
  }
  assert.equal(acquisitionSource("?utm_source=instagram&email=secret"), "instagram");
  for (const value of ["?utm_source=Instagram", "?utm_source=facebook&utM_source=x&private=secret&utm_source=x", "?utm_source=%3Cscript%3E"]) assert.equal(acquisitionSource(value), "unknown");
});

test("every social task produces a canonical question and a bounded private bot start token", () => {
  for (const source of SOURCES) for (const task of ["bank", "funding", "exit"]) {
    const question = new URL(questionLink(task, source, 100000));
    assert.equal(question.origin, "https://liquilens.in");
    assert.equal(acquisitionSource(question.search), source);
    assert.equal(question.searchParams.get("task"), task);
    const bot = new URL(telegramLink(task, source));
    assert.equal(bot.origin, "https://t.me");
    assert.match(bot.searchParams.get("start"), /^[A-Za-z0-9_-]{1,64}$/);
    assert.equal(bot.searchParams.get("startgroup"), null);
  }
});

test("new shares do not copy the original campaign, tracking IDs or operator flag", () => {
  const link = new URL(questionLink("exit", "shared", 10000));
  assert.equal(link.search, "?task=exit&utm_source=shared&size=10000");
  assert.equal(new URL(questionLink("bank")).searchParams.get("size"), null);
  assert.equal(new URL(questionLink("exit", "shared", -1)).searchParams.get("size"), null);
  assert.throws(() => questionLink("private", "instagram"));
  assert.throws(() => telegramLink("bank", "https://evil.test"));
});
