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

export async function engineGet(path: string): Promise<Response> {
  try {
    return await fetch(`${base()}${path}`, { headers: { "X-Engine-Key": key() }, cache: "no-store" });
  } catch {
    throw new EngineDown(`The engine is not answering on ${base()}.`);
  }
}

export async function enginePost<T>(path: string, body: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${base()}${path}`, {
      method: "POST",
      headers: { "X-Engine-Key": key(), "content-type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    throw new EngineDown(`The engine is not answering on ${base()}. Start it and try again.`);
  }
  if (!res.ok) throw new EngineDown(`The engine refused that (${res.status}). Nothing was changed.`);
  return (await res.json()) as T;
}
