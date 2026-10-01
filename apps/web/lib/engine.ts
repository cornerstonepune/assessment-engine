// The one place the app talks to the engine over HTTP.
//
// Everything else the app needs is a row it can read for itself. Two things are not: the scan of a
// child's paper, which lives on the school's disk beside the engine and never in the database
// (rule 6), and marking a corrected reading, which is computation and therefore the engine's
// (ARCHITECTURE.md §1). The key stays on the server — a browser never sees it, and never fetches
// the engine directly.
import type { EngineRoutes } from "./engine-routes";

// Read at call time, not at module load: the repo-root .env is loaded by `lib/db`, and which of
// these two modules a request touches first is not ours to decide.
const base = () => (process.env.ENGINE_URL ?? "http://localhost:8000").replace(/\/$/, "");

// The routes the engine serves, written from the engine itself (lib/engine-routes.ts): a path the engine does not
// have, or a body field one of its routes does not take, does not compile (goals/p1-types-hold.yaml). A caller
// writes a route as it calls it: each `{name}` in the engine's path is any text, and a query string may follow.
type Filled<P extends string> = P extends `${infer A}{${string}}${infer B}` ? `${A}${string}${Filled<B>}` : P;
type Called<P extends string> = Filled<P> | `${Filled<P>}?${string}`;
type Route = keyof EngineRoutes;
type PathOf<M extends string, R extends Route = Route> = R extends `${M} ${infer P}` ? Called<P> : never;
export type GetPath = PathOf<"GET">;
export type PostPath = PathOf<"POST">;
/** The body the engine's POST route at `P` takes, as the engine declares it. */
export type BodyOf<P extends string, R extends Route = Route> = R extends `POST ${infer Q}`
  ? P extends Called<Q>
    ? EngineRoutes[R]
    : never
  : never;

export class EngineDown extends Error {}

function key(): string {
  const k = process.env.ENGINE_KEY;
  if (!k) throw new EngineDown("ENGINE_KEY is not set, so this app cannot reach the engine.");
  return k;
}

// A call to the engine gives up after this long rather than holding a page or an action open until
// Vercel's five-minute limit. Rendering a printed paper takes a few seconds; nothing takes a minute.
const ENGINE_WAIT_MS = 30_000;

export async function engineGet(path: GetPath): Promise<Response> {
  try {
    return await fetch(`${base()}${path}`, {
      headers: { "X-Engine-Key": key() },
      cache: "no-store",
      signal: AbortSignal.timeout(ENGINE_WAIT_MS),
    });
  } catch {
    throw new EngineDown(`The engine is not answering on ${base()}.`);
  }
}

/** An image the engine makes or reads off the school's disk — a scan, a paper as printed, one
 *  question as it prints — handed on as the response. The caller has already checked that a member
 *  of staff is asking. */
export async function engineImage(path: GetPath): Promise<Response> {
  try {
    const res = await engineGet(path);
    if (!res.ok) {
      const why = ((await res.json().catch(() => ({}))) as { detail?: string }).detail ?? "not found on this machine";
      if (!/\.(jpg|png)(\?|$)/.test(path)) return new Response(why, { status: res.status });
      return said(why.startsWith("the scan is not on this machine") ? "The scan is not on the server yet." : "The engine has no picture for this.", why);
    }
    return new Response(res.body, {
      headers: {
        "content-type": res.headers.get("content-type") ?? "image/jpeg",
        "cache-control": "private, max-age=300",
      },
    });
  } catch (e) {
    const why = e instanceof EngineDown ? e.message : "could not fetch the page";
    if (!/\.(jpg|png)(\?|$)/.test(path)) return new Response(why, { status: 503 });
    return said("The engine is not answering.", why);
  }
}

/** Why there is no picture, as a picture: an <img> cannot show a sentence, and a broken-image icon told
 *  Nimish nothing (2026-09-25, a paper read on the Mac before the server had its scan). Shown to staff
 *  only — the route has already checked who is asking. */
function said(headline: string, detail = ""): Response {
  const esc = (s: string) => s.replace(/[<>&"]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;" })[c] ?? c);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120" viewBox="0 0 640 120">
  <rect width="640" height="120" fill="#f4f1ea" stroke="#c9c2b4"/>
  <text x="20" y="48" font-family="Georgia, serif" font-size="20" fill="#2a2622">${esc(headline)}</text>
  <text x="20" y="80" font-family="system-ui, sans-serif" font-size="13" fill="#6b645a">${esc(detail.slice(0, 90))}</text>
</svg>`;
  return new Response(svg, { status: 200, headers: { "content-type": "image/svg+xml", "cache-control": "no-store" } });
}

/** A POST whose whole answer the caller reads, status and body — for a call where a refusal is
 *  itself the answer, such as the engine saying in words why it would not take a correction. */
export async function engineSend<P extends PostPath>(path: P, body: BodyOf<P>): Promise<Response> {
  try {
    return await fetch(`${base()}${path}`, {
      method: "POST",
      headers: { "X-Engine-Key": key(), "content-type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
      signal: AbortSignal.timeout(ENGINE_WAIT_MS),
    });
  } catch {
    throw new EngineDown(`The engine is not answering on ${base()}. Start it and try again.`);
  }
}

export async function enginePost<P extends PostPath>(path: P, body: BodyOf<P>): Promise<unknown> {
  const res = await engineSend(path, body);
  if (!res.ok) throw new EngineDown(`The engine refused that (${res.status}). Nothing was changed.`);
  return await res.json();
}
