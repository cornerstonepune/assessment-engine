/**
 * Rows a browser test builds for itself — a class, a worksheet the engine enters, papers read — so it proves the same
 * thing on a database built from the repository (`bin/testdb fresh`, what CI runs) as on a copy of live: never
 * "whatever live holds", and never a skip because live held nothing (goals/p1-browser-tests-in-ci.yaml). The engine
 * tests' own are packages/engine/tests/rows.py.
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import type postgres from "postgres";

type Sql = postgres.Sql;

async function tenant(sql: Sql): Promise<string> {
  return (await sql<{ id: string }[]>`select id from tenant limit 1`)[0].id;
}

/** A class of the test's own, `band`, its children named in roll order — made once and kept: a child some test has
 *  signed a paper off for holds evidence, which is append-only. → {name: child id} */
export async function aClass(sql: Sql, section: string, band: string, names: string[]): Promise<Record<string, string>> {
  const t = await tenant(sql);
  const kids: Record<string, string> = {};
  for (const [i, name] of names.entries()) {
    const roll = String(i + 1);
    const [had] = await sql<{ id: string }[]>`select id from child where section = ${section} and roll_no = ${roll}`;
    if (had) {
      kids[name] = had.id;
      continue;
    }
    const [{ id }] = await sql<{ id: string }[]>`
      insert into child (tenant_id, roll_no, section, band) values (${t}, ${roll}, ${section}, ${band}) returning id`;
    await sql`insert into pii.child (tenant_id, child_id, first_name) values (${t}, ${id}, ${name})`;
    kids[name] = id;
  }
  return kids;
}

export type Worksheet = { code: string; title: string; date: string; band: string; week: string; items: object[] };

/** A worksheet entered by the engine exactly as a school's own paper is (`engine legacy paper`), once.
 *  → its template id and its questions' ids, in order. */
export async function aWorksheet(sql: Sql, w: Worksheet): Promise<{ template: string; items: string[] }> {
  const find = () => sql<{ id: string; item_ids: string[] }[]>`
    select id, item_ids from sheet_template where source = 'legacy' and batch_id = ${w.code}`;
  if (!(await find()).length) {
    const dir = mkdtempSync(path.join(tmpdir(), "rows-"));
    const file = path.join(dir, `${w.code}.json`);
    writeFileSync(file, JSON.stringify({ ...w, pages: [{ n: 1, mask: 0 }] }));
    execFileSync(path.resolve(__dirname, "../../../bin/engine"), ["legacy", "paper", file], { env: process.env });
    rmSync(dir, { recursive: true });
  }
  const [t] = await find();
  return { template: t.id, items: t.item_ids };
}

/** One answer as the reader left it: its status, what it read, and why it held it, if it did; `checkedBy`, the person
 *  who said what the child wrote. */
export type Read = { status: string; read?: string; why?: string; guess?: string; checkedBy?: string };

/** One child's copy of a worksheet, scanned and read, an answer per entry of `reads` in question order. A paper read
 *  before under the same code is superseded, as the reader supersedes a scan it reads again: its answers stay — one a
 *  test signed off holds evidence, and evidence is append-only, so deleting them failed the next run — and nothing
 *  that reads a paper reads them. A run starts from these rows. → its sheet (sheet_instance id), its capture and its
 *  answers' ids. */
export async function aReadPaper(
  sql: Sql,
  p: { qr: string; child: string; template: string; items: string[]; reads: Read[] },
): Promise<{ sheet: string; capture: string; results: string[] }> {
  // ADR 0029: a wrong or a blank stands once a person has said what the child wrote; the engine's word alone holds it
  // for them (`needs_teacher`). A paper with one the engine settled alone is a paper the engine cannot write.
  const alone = p.reads.filter((r) => (r.status === "wrong" || r.status === "blank") && !r.checkedBy);
  if (alone.length) throw new Error(`${p.qr}: a wrong or a blank needs checkedBy — the engine never settles one alone`);
  const t = await tenant(sql);
  const [had] = await sql<{ id: string }[]>`select id from sheet_instance where qr_code = ${p.qr} and child_id = ${p.child}`;
  const [{ id: sheet }] = had
    ? [had]
    : await sql<{ id: string }[]>`
        insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, print_status)
        values (${t}, ${p.qr}, ${p.template}, ${p.child}, 'returned') returning id`;
  const [{ id: capture }] = await sql<{ id: string }[]>`
    insert into capture (tenant_id, path, pages, status, sheet_instance_id)
    values (${t}, ${`${p.qr}.pdf`}, 1, 'processed', ${sheet}) returning id`;
  await sql`update capture set superseded_by = ${capture} where sheet_instance_id = ${sheet} and id <> ${capture}
            and superseded_by is null`;
  const results: string[] = [];
  for (const [i, r] of p.reads.entries()) {
    const raw = JSON.stringify({
      child_answer: r.read ?? "",
      answer_state: r.read ? "written" : "blank",
      confidence: 95,
      why: r.why ?? "",
      ...(r.guess ? { guess: r.guess } : {}),
    });
    const [{ id }] = await sql<{ id: string }[]>`
      insert into item_result (tenant_id, capture_id, item_id, rid, raw_read, status)
      values (${t}, ${capture}, ${p.items[i]}, 'a', ${raw}, ${r.status}) returning id`;
    if (r.checkedBy) {
      await sql`
        insert into read_correction (tenant_id, child_id, capture_id, item_result_id, model_read, human_read, by)
        values (${t}, ${p.child}, ${capture}, ${id}, ${r.read ?? ""}, ${r.read ?? ""}, ${r.checkedBy})`;
    }
    results.push(id);
  }
  return { sheet, capture, results };
}
