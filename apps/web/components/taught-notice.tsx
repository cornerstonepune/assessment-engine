import { Notice } from "./shell";
import { sql } from "@/lib/db";

// What was just said of a class, on the page it was said on (lib: app/(app)/topic-actions.ts sets `said`, `in` and `taught`):
// a topic or one skill of it, taught or not, in the person's name. Nothing when the address names no real one.
export async function TaughtNotice({ q }: { q: Record<string, string | undefined> }) {
  if (!q.said || !q.in || !/^[A-Z0-9_.]+$/.test(q.said)) return null;
  const [row] = await sql<{ name: string }[]>`
    select name from skill where code = ${q.said} union all select name from topic where code = ${q.said} limit 1`;
  if (!row) return null;
  return (
    <Notice tone="neem">
      {row.name} is {q.taught === "0" ? "not " : ""}taught in {q.in} now, in your name. No other class changed.
    </Notice>
  );
}
