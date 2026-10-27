/**
 * The class the Results specs read (goals/res_results_by_topic.yaml): made from real papers, read and signed off as a
 * person signs them off (`confirm_results`), so every state on the page is the graph's own. Made once and kept: signed-off
 * answers are evidence, which is append-only.
 *
 * U71-A, Grade 2. On one class assessment of 2-digit + 2-digit (Medium): Asha has 2 right, 1 wrong, 1 wrong with working
 * and 1 blank; Bina 4 right and 1 wrong, and two home assessments on it besides; Chetan has no paper. Bina has one answer
 * still waiting for a person. U71-B is another class, with its own educator.
 */
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import type postgres from "postgres";
import { aClass, aReadPaper, type Read } from "./rows";

export const A = "U71-A";
export const B = "U71-B";
export const MINE = { email: "u71-mine@cornerstone.test", name: "U71 Mine", role: "educator", classes: [A] };
export const OTHER = { email: "u71-other@cornerstone.test", name: "U71 Other", role: "educator", classes: [B] };
export const SKILL = "ADD.2D2D";
export const TOPIC = "ADDSUB";
/** The one written page every paper of the class was read from: a real file the engine serves. */
export const SCAN = path.join(tmpdir(), "u71-scan.pdf");

const PAGE = `
import sys, pymupdf
doc = pymupdf.open(); page = doc.new_page(width=595, height=842)
page.insert_text((72, 120), "U71 written page", fontsize=28); doc.save(sys.argv[1])
`;

const R = (status: string, read: string): Read => ({ status, read, checkedBy: status === "correct" ? undefined : "e2e@cornerstone.test" });

export async function aResultsClass(sql: postgres.Sql) {
  if (!existsSync(SCAN)) {
    mkdirSync(path.dirname(SCAN), { recursive: true });
    execFileSync(path.resolve(__dirname, "../../../packages/engine/.venv/bin/python"), ["-c", PAGE, SCAN]);
  }
  const kids = await aClass(sql, A, "G2", ["Asha", "Bina", "Chetan"]);
  const others = await aClass(sql, B, "G2", ["Om"]);
  await sql`update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s
                                       where not (s ->> 'email' = any(${[MINE.email, OTHER.email]})))
            where key = 'app.staff'`;
  await sql`update config set value = value || ${sql.json([MINE, OTHER])} where key = 'app.staff'`;
  // the class assessment, and another worksheet of the same skill and level for the home assessments
  const [ws, home] = await sql<{ id: string; item_ids: string[] }[]>`
    select id, item_ids from sheet_template
    where source = 'library' and retired_at is null and skill_set_code = ${SKILL} and difficulty = 'Medium' order by code limit 2`;
  const paper = async (qr: string, child: string, kind: string, reads: Read[], working?: number) => {
    const [done] = await sql`select 1 from sheet_instance si join capture c on c.sheet_instance_id = si.id and c.superseded_by is null
                             join item_result r on r.capture_id = c.id and r.state = 'confirmed' where si.qr_code = ${qr} limit 1`;
    if (done) return;
    const w = kind === "assessment" ? ws : home;
    const p = await aReadPaper(sql, { qr, child, template: w.id, items: w.item_ids.slice(0, reads.length), reads, file: SCAN });
    await sql`update sheet_instance set kind = ${kind} where id = ${p.sheet}`;
    if (working != null) await sql`update item_result set working_shown = 'full' where id = ${p.results[working]}`;
    await sql`select confirm_results(${child}::uuid, 'e2e@cornerstone.test', ${p.capture}::uuid)`;
  };
  await paper("CSU71A01", kids.Asha, "assessment", [R("correct", "1"), R("correct", "1"), R("wrong", "7"), R("wrong", "9"), R("blank", "")], 3);
  await paper("CSU71B01", kids.Bina, "assessment", [R("correct", "1"), R("correct", "1"), R("correct", "1"), R("correct", "1"), R("wrong", "5")]);
  await paper("CSU71B02", kids.Bina, "focus", [R("correct", "1"), R("correct", "1"), R("correct", "1")]);
  await paper("CSU71B03", kids.Bina, "focus", [R("correct", "1"), R("correct", "1"), R("correct", "1")]);
  // one answer of Bina's still waiting for a person: a paper read, nothing of it signed off
  const [waits] = await sql`select 1 from sheet_instance where qr_code = 'CSU71B04'`;
  if (!waits) {
    const p = await aReadPaper(sql, { qr: "CSU71B04", child: kids.Bina, template: ws.id, items: ws.item_ids.slice(0, 1), reads: [{ status: "needs_teacher", read: "3" }], file: SCAN });
    await sql`update sheet_instance set kind = 'focus' where id = ${p.sheet}`;
  }
  return { kids, others };
}
