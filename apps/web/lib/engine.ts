// The one place the app talks to the engine over HTTP.
//
// Everything else the app needs is a row it can read for itself. Two things are not: the scan of a
// child's paper, which lives on the school's disk beside the engine and never in the database
// (rule 6), and marking a corrected reading, which is computation and therefore the engine's
// (ARCHITECTURE.md §1). The key stays on the server — a browser never sees it, and never fetches
// the engine directly.
// Read at call time, not at module load: the repo-root .env is loaded by `lib/db`, and which of
// these two modules a request touches first is not ours to decide.
const base = () => (process.env.ENGINE_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class EngineDown extends Error {}

function key(): string {
  const k = process.env.ENGINE_KEY;
  if (!k) throw new EngineDown("ENGINE_KEY is not set, so this app cannot reach the engine.");
  return k;
}

// A call to the engine gives up after this long rather than holding a page or an action open until
// Vercel's five-minute limit. Rendering a printed paper takes a few seconds; nothing takes a minute.
const ENGINE_WAIT_MS = 30_000;

export async function engineGet(path: string): Promise<Response> {
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
export async function engineImage(path: string): Promise<Response> {
  try {
    const res = await engineGet(path);
    if (!res.ok) return new Response("not found on this machine", { status: res.status });
    return new Response(res.body, {
      headers: {
        "content-type": res.headers.get("content-type") ?? "image/jpeg",
        "cache-control": "private, max-age=300",
      },
    });
  } catch (e) {
    return new Response(e instanceof EngineDown ? e.message : "could not fetch the page", { status: 503 });
  }
}

/** A POST whose whole answer the caller reads, status and body — for a call where a refusal is
 *  itself the answer, such as the engine saying in words why it would not take a correction. */
export async function engineSend(path: string, body: unknown): Promise<Response> {
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

export async function enginePost<T>(path: string, body: unknown): Promise<T> {
  const res = await engineSend(path, body);
  if (!res.ok) throw new EngineDown(`The engine refused that (${res.status}). Nothing was changed.`);
  return (await res.json()) as T;
}
