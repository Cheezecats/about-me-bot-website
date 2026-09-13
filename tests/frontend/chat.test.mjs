import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "typescript";

// Use the project's existing compiler; no browser-test runtime is required.
const source = await readFile(new URL("../../src/lib/chat.ts", import.meta.url), "utf8");
const javascript = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
const { ChatClient, parseChatResponse, healthUrl, sourceExcerpt, trimLinkPunctuation } = await import(`data:text/javascript;base64,${Buffer.from(javascript).toString("base64")}`);
const reply = (answer = "Nikon Z8") => ({ status: "answered", answer, sources: [] });
const response = (body, status = 200) => new Response(JSON.stringify(body), { status });

test("reset discards a late reply and permits a new session immediately", async (t) => {
  const pending = [];
  t.mock.method(globalThis, "fetch", (_url, options) => new Promise((resolve) => pending.push({ resolve, options })));
  const client = new ChatClient();
  const old = client.send("/api/chat", "old question", "old-session").catch((e) => e);
  client.cancel();
  assert.equal(pending[0].options.signal.aborted, true);
  const current = client.send("/api/chat", "new question", "new-session");
  pending[0].resolve(response(reply("old answer")));
  assert.equal((await old).kind, "cancelled");
  assert.equal(client.busy, true);
  assert.equal(JSON.parse(pending[1].options.body).session_id, "new-session");
  pending[1].resolve(response(reply("new answer")));
  assert.equal((await current).answer, "new answer");
  assert.equal(client.busy, false);
});

test("rapid repeated sends produce one HTTP request", async (t) => {
  let finish;
  const fetch = t.mock.method(globalThis, "fetch", () => new Promise((resolve) => { finish = resolve; }));
  const client = new ChatClient();
  const first = client.send("/api/chat", "hello", "test");
  await assert.rejects(client.send("/api/chat", "hello", "test"), { kind: "busy" });
  assert.equal(fetch.mock.callCount(), 1);
  finish(response(reply()));
  await first;
});

test("timeouts release the request and keep retry available", async (t) => {
  t.mock.method(globalThis, "fetch", (_url, { signal }) => new Promise((_resolve, reject) => {
    signal.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
  }));
  const client = new ChatClient();
  await assert.rejects(client.send("/api/chat", "question", "test", 5), { kind: "timeout" });
  assert.equal(client.busy, false);
});

test("rate limits and HTTP 200 unavailable replies remain distinguishable", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async () => response({ answer: "Please wait." }, 429));
  const client = new ChatClient();
  await assert.rejects(client.send("/api/chat", "question", "test"), { kind: "http", status: 429 });
  fetch.mock.mockImplementation(async () => response({ status: "unavailable", answer: "Try again." }));
  assert.equal((await client.send("/api/chat", "question", "test")).status, "unavailable");
});

test("malformed successful responses cannot render blank or crash the widget", () => {
  for (const body of [null, {}, { status: "answered", answer: "" }, { status: "unexpected", answer: "hello" }]) {
    assert.throws(() => parseChatResponse(body), { kind: "invalid" });
  }
  const parsed = parseChatResponse({ ...reply(), sources: [null, {}, { chunk_id: "a", text: "fact", category: "bio", label: {} }], suggested_questions: [null, "Camera?", {}] });
  assert.equal(parsed.sources.length, 1);
  assert.equal(parsed.sources[0].label, undefined);
  assert.deepEqual(parsed.suggested_questions, ["Camera?"]);
});

test("health URLs, source excerpts, and links preserve usable content", () => {
  assert.equal(healthUrl("https://chat.example/api/chat/?key=public"), "https://chat.example/api/health?deep=true");
  assert.equal(sourceExcerpt({ title: "Math (IA)", text: "## Math (IA) A short fact." }), "A short fact.");
  assert.deepEqual(trimLinkPunctuation("https://github.com/Cheezecats."), ["https://github.com/Cheezecats", "."]);
});

test('actions are optional, bounded identifiers and absent on refusals', () => {
  assert.deepEqual(parseChatResponse(reply()).actions, []);
  assert.deepEqual(parseChatResponse({...reply(), actions: ['photography', 'photography', null, {}, 'https://evil.example']}).actions, ['photography']);
  assert.deepEqual(parseChatResponse({...reply(), status:'refused', actions:['photography']}).actions, []);
});
