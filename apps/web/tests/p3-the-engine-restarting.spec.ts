/**
 * While the engine restarts, a person is told so in words, never "The engine refused (502)" (Nimish saw that on
 * 2026-10-16, HANDOFF.md) or a page that fails (goals/l8-deploy-without-downtime.yaml). The engine's door is Caddy: with
 * no engine behind it, it answers 502, and with Caddy itself restarting, nothing answers at all.
 */
import { expect, test } from "@playwright/test";
import { createServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { ENGINE_RESTARTING, EngineDown, engineGet, enginePost, engineSend } from "../lib/engine";

let door: Server;
let port = 0;
const saved = { url: process.env.ENGINE_URL, key: process.env.ENGINE_KEY };

test.beforeAll(async () => {
  // what Caddy answers with no engine behind it, and what the engine answers for a route it has
  door = createServer((req, res) => {
    const status = req.url?.startsWith("/runs/") ? 404 : 502;
    res.writeHead(status, { "content-type": "application/json" }).end(JSON.stringify({ detail: "x" }));
  });
  await new Promise<void>((done) => door.listen(0, "127.0.0.1", done));
  port = (door.address() as AddressInfo).port;
  process.env.ENGINE_KEY = "l8";
});

test.afterAll(async () => {
  await new Promise((done) => door.close(done));
  process.env.ENGINE_URL = saved.url;
  process.env.ENGINE_KEY = saved.key;
});

async function said(call: () => Promise<unknown>): Promise<string> {
  try {
    await call();
  } catch (e) {
    if (e instanceof EngineDown) return e.message;
    throw e;
  }
  return "it answered";
}

test("a restarting engine is said in words while its door answers 502", async () => {
  process.env.ENGINE_URL = `http://127.0.0.1:${port}`;
  expect(ENGINE_RESTARTING).toBe("The engine is restarting. Try again in a minute.");
  expect(await said(() => engineGet("/bank/proposals"))).toBe(ENGINE_RESTARTING);
  expect(await said(() => engineSend("/papers/plan", {} as never))).toBe(ENGINE_RESTARTING);
  expect(await said(() => enginePost("/capture/trusted", null))).toBe(ENGINE_RESTARTING);
});

test("a restarting engine is said in words while nothing answers at all", async () => {
  process.env.ENGINE_URL = "http://127.0.0.1:1";
  expect(await said(() => engineGet("/bank/proposals"))).toBe(ENGINE_RESTARTING);
  expect(await said(() => engineSend("/papers/plan", {} as never))).toBe(ENGINE_RESTARTING);
});

test("the engine's own answer still reaches the page that asked", async () => {
  process.env.ENGINE_URL = `http://127.0.0.1:${port}`;
  const res = await engineGet("/runs/none");
  expect(res.status).toBe(404);
});
