import { EngineDown, engineSend } from "./engine";

export type Area = { skill_set: string; level: string; n: number };

/** A child's paper, approved in the teacher's name: the engine makes and prints it (`w2_print/focus_paper.py`) —
 *  the home paper it proposes, or, with `areas`, the paper the teacher chose. A home paper already approved this
 *  week — a second click, or a colleague first — is not an error: null, and the page shows who did.
 *  Not a server action: it takes the approver's name, which only a signed-in action may supply from its session. */
export async function makePaper(childId: string, week: string, by: string, areas?: Area[]): Promise<string | null> {
  const res = areas
    ? await engineSend(`/child/${childId}/paper`, { week, by, areas })
    : await engineSend(`/child/${childId}/focus`, { week, by });
  if (res.status === 409 && !areas) return null;
  if (!res.ok) throw new EngineDown(`The engine refused that (${res.status}): ${await res.text()}. Nothing was printed.`);
  return ((await res.json()) as { qr: string }).qr;
}

/** "SUB.2D2D~Medium~6" → an area; anything else → null. The form and the address carry areas this way. */
export function readArea(s: string): Area | null {
  const [skill_set, level, n] = s.split("~");
  const count = Number(n);
  return skill_set && level && Number.isInteger(count) ? { skill_set, level, n: count } : null;
}

/** Where a paper is seen as it will print, before approval: the home paper, or the areas a teacher chose. */
export function seeHref(childId: string, week: string, areas: Area[] = []): string {
  const q = new URLSearchParams({ week });
  for (const a of areas) q.append("a", `${a.skill_set}~${a.level}~${a.n}`);
  return `/api/see/${childId}?${q}`;
}
