import { EngineDown, engineSend } from "./engine";

export type Area = { skill_set: string; level: string; n: number };

/** The paper an educator saw before approving it (goals/preview-before-print.yaml): which draw of it — "Different
 *  questions" asks for the next — and the engine's code for its questions (`w2_print/seen.py`). */
export type Shown = { draw: number; seen: string };

/** A draw as the address or a form carries it (`draw`); anything else is the first, 0. */
export function readDraw(v: string | null | undefined): number {
  const n = Number(v);
  return Number.isInteger(n) && n > 0 && n < 10000 ? n : 0;
}

/** A child's paper, approved in the teacher's name: the engine makes and prints it (`w2_print/focus_paper.py`) —
 *  the home paper it proposes, or, with `areas`, the paper the teacher chose — exactly as `shown`. `replaces` is the
 *  week's home paper the teacher saw, if any: one made since — a second click, or a colleague first — is not an error:
 *  `{}`, and the page shows who did. `changed`: the questions are no longer the ones shown (a paper was made for the
 *  child meanwhile), so nothing printed and the page shows them again. Not a server action: it takes the approver's
 *  name, which only a signed-in action may supply. */
export async function makePaper(
  childId: string, week: string, by: string, shown: Shown, areas?: Area[], replaces?: string,
): Promise<{ qr?: string; changed?: true }> {
  const res = areas
    ? await engineSend(`/child/${childId}/paper`, { week, by, areas, ...shown })
    : await engineSend(`/child/${childId}/focus`, { week, by, ...shown, ...(replaces ? { replaces } : {}) });
  if (res.status === 412) return { changed: true };
  if (res.status === 409 && !areas) return {};
  if (!res.ok) throw new EngineDown(`The engine refused that (${res.status}): ${await res.text()}. Nothing was printed.`);
  return { qr: ((await res.json()) as { qr: string }).qr };
}

/** "SUB.2D2D~Medium~6" → an area; anything else → null. The form and the address carry areas this way. */
export function readArea(s: string): Area | null {
  const [skill_set, level, n] = s.split("~");
  const count = Number(n);
  return skill_set && level && Number.isInteger(count) ? { skill_set, level, n: count } : null;
}

/** Where a paper is seen as it will print, before approval: the home paper, or the areas a teacher chose, in the
 *  draw shown. */
export function seeHref(childId: string, week: string, areas: Area[] = [], draw = 0): string {
  const q = new URLSearchParams({ week });
  for (const a of areas) q.append("a", `${a.skill_set}~${a.level}~${a.n}`);
  if (draw) q.set("draw", String(draw));
  return `/api/see/${childId}?${q}`;
}

/** The page where a teacher chooses one child's paper: these areas, in this draw. */
export function customHref(child: string, areas: Area[], draw = 0): string {
  const q = new URLSearchParams({ child });
  for (const a of areas) q.append("a", `${a.skill_set}~${a.level}~${a.n}`);
  if (draw) q.set("draw", String(draw));
  return `/make/custom?${q}`;
}
