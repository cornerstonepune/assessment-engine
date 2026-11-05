/**
 * M1-13c — the page part, drawn once (goals/m1-13c-page-part-component.yaml). Nimish's brief via the orchestrator: lift the
 * rendering of one part of an activity page (its words, who wrote them) out of /curriculum into one shared component that
 * takes its actions and its gate as props, so /curriculum/* and the educator's activity page draw it the same way, each with
 * its own actions. The behaviour of /curriculum stays what tests/m1-13-curriculum-fill.spec.ts holds.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";

const root = path.resolve(__dirname, "..");
const read = (f: string) => readFileSync(path.join(root, f), "utf8");

test("the component draws a part's words and origin and carries no gate, engine call or action of its own", () => {
  const part = read("components/page-part/part.tsx");
  expect(part).toMatch(/export (async )?function PartView\b/);
  expect(part).toMatch(/export function Words\b/);
  expect(part).toMatch(/export function Origin\b/);
  expect(part, "its actions are props").toMatch(/actions\??: React\.ReactNode/);
  expect(part, "its editor is a prop").toMatch(/editor\??: React\.ReactNode/);
  for (const forbidden of [/@\/lib\/auth/, /@\/lib\/engine/, /lib\/curriculum-screens/, /use server/, /requireStaff/, /from "next\/navigation"/]) expect(part, String(forbidden)).not.toMatch(forbidden);
});

test("the component and its styles use tokens only, and its icons come from the one Lucide lookup", () => {
  for (const f of ["components/page-part/part.tsx", "components/page-part/page-part.css", "lib/page-part.ts"]) {
    const text = read(f);
    expect(text, f).not.toMatch(/#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(/);
  }
  expect(read("components/page-part/part.tsx")).toContain('from "@/lib/icons"');
});

test("/curriculum draws its parts with the component and keeps no copy of it", () => {
  const parts = read("app/(app)/curriculum/parts.tsx");
  expect(parts).toContain('from "@/components/page-part/part"');
  expect(parts).not.toMatch(/export function (Words|Origin)\b/);
  expect(read("app/(app)/curriculum/screens.css")).not.toMatch(/\.cs-(steps|slip|origin)\b/);
});
