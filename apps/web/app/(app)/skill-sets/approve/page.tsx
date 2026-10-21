import Link from "@/components/link";
import { Body, Notice, PageHeader, Panel, Pill } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { scopeOf } from "@/lib/scope";
import { deadline } from "@/lib/deadline";
import { KIND } from "@/components/question";
import { grades as schoolGrades, levelsOf, skillSets, type SkillSet } from "@/lib/queries";
import { chargesTable } from "@/lib/queries-charges";
import { approveSkills } from "../[code]/actions";
import { mayDecide } from "@/lib/decides";

// Every skill waiting for approval as one table to work through (goals/ui6a-approve-filtered.yaml; Nimish, 2026-10-12:
// "this page needs to have proper filters and all; no page should have such laundary lists like stuff"): one row a
// skill, its levels folded until opened, approved on its own or with the rows shown, in the person's own name.
// The engine prepared the words; the person approves or opens one to change it first (goals/ui3-curriculum.yaml). A
// skill whose topic is not taught yet is here too, said so: it is approved before it is switched on (goals/ny1-needs-you.yaml).
// Approving is the coordinator's (people.decides): anyone else reads the same page with no approval offered, and may
// open a skill to change its words (goals/ux1-who-sees-what.yaml).

type Filter = { grade?: string; topic?: string; taught?: string };
const TAUGHT: [string, string][] = [["yes", "Taught"], ["no", "Not taught yet"]];

// An address for the page: every choice, a change laid over them.
function query(f: Filter, change: Partial<Filter> = {}) {
  const q = new URLSearchParams();
  for (const [k, value] of Object.entries({ ...f, ...change })) if (value) q.set(k, value);
  const s = q.toString();
  return s ? `/skill-sets/approve?${s}` : "/skill-sets/approve";
}

// a skill kept by every choice but `except`, so each choice counts what the others leave
function keeps(x: SkillSet, f: Filter, except?: keyof Filter) {
  return (
    (except === "grade" || !f.grade || x.band === f.grade) &&
    (except === "topic" || !f.topic || x.topic_code === f.topic) &&
    (except === "taught" || !f.taught || x.taught === (f.taught === "yes"))
  );
}

export default async function ApproveSkills({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const me = await requireStaff();
  const q = await searchParams;
  const [sets, charges, mayApprove, school] = await deadline(
    Promise.all([skillSets({ untaught: true, scope: scopeOf(me) }), chargesTable(), mayDecide(me, "skills"), schoolGrades()]),
  );
  const waiting = sets.filter((s) => s.status !== "ratified");
  // the school's grades in their order (`grade`): every grade a skill holds is one of them
  const grades = school.list.map((x): [string, string] => [x.code, x.name]);
  const topics = [...new Map(waiting.filter((x) => x.topic_code).map((x) => [x.topic_code!, x])).values()].sort(
    (a, b) => (a.topic_ord ?? 0) - (b.topic_ord ?? 0),
  );
  const f: Filter = {
    grade: grades.some(([g]) => g === q.grade) ? q.grade : undefined,
    topic: topics.some((t) => t.topic_code === q.topic) ? q.topic : undefined,
    taught: TAUGHT.some(([v]) => v === q.taught) ? q.taught : undefined,
  };
  const order = (x: SkillSet) => grades.findIndex(([g]) => g === x.band);
  const shown = waiting
    .filter((x) => keeps(x, f))
    .sort((a, b) => order(a) - order(b) || (a.topic_ord ?? 0) - (b.topic_ord ?? 0) || a.name.localeCompare(b.name));
  const count = (except: keyof Filter, test: (x: SkillSet) => boolean) => waiting.filter((x) => keeps(x, f, except) && test(x)).length;
  const narrowed = Boolean(f.grade || f.topic || f.taught);

  return (
    <>
      <PageHeader
        stage="Curriculum"
        title="Approve the skills"
        sub="The engine has written each skill as what a child can do, and each level as a sentence. Read them, then approve them as written — or open one and change its words first."
      />
      <Body>
        <Link href="/" className="chip mb-[18px] inline-block">
          ← Curriculum
        </Link>
        {mayApprove ? null : (
          <p role="status" className="note mb-[18px]">
            The coordinator approves the skills. Read them here; open one to change its words, and the change waits for the
            coordinator&rsquo;s approval.
          </p>
        )}
        {q.approved === "0" ? (
          <Notice tone="terracotta">Nothing was approved: it changed since this page was opened. Read it again, then approve.</Notice>
        ) : q.approved ? (
          <Notice tone="neem">
            Approved, in your name. {waiting.length ? `${waiting.length} still ${waiting.length === 1 ? "waits" : "wait"}.` : "Every skill is approved."}
          </Notice>
        ) : null}
        {q.table === "0" ? (
          <Notice tone="terracotta">The table was not approved: it changed since this page was opened. Read it again, then approve.</Notice>
        ) : q.table ? (
          <Notice tone="neem">What a wrong answer counts against is approved, in your name.</Notice>
        ) : null}
        {waiting.length === 0 && !charges.waiting && !q.approved ? <Notice tone="neem">Every skill is approved.</Notice> : null}

        {charges.waiting ? (
          // approved on its own: a press meant for some skills never approves it
          <form action={approveSkills} className="mb-[18px]">
            <input type="hidden" name="back" value={query(f)} />
            <input type="hidden" name="charges_table" value={JSON.stringify(charges.table)} />
            <Panel title="What a wrong answer counts against">
              <p className="text-[15px] leading-snug">
                A wrong answer counts against the part of the skill that broke. Most mistakes belong to the sum they happen in;
                in a question with two operations, to the one they happen in (a times-table slip while checking a division by
                multiplying is multiplication&apos;s). {charges.rows.length} belong to something else on their kind of question.
              </p>
              <details className="mt-2">
                <summary className="cursor-pointer text-[13px]">Read the {charges.rows.length}</summary>
                <ul className="mt-2 grid gap-1 text-[13px]">
                  {charges.rows.map((r) => (
                    <li key={`${r.kind}-${r.code}`}>
                      On a {KIND[r.kind] ?? r.kind}, <b>{r.mistake.toLowerCase()}</b> counts against <b>{r.skill}</b>.
                    </li>
                  ))}
                </ul>
              </details>
              {mayApprove ? (
                <button className="btn secondary mt-3" type="submit">
                  Approve this table as written, as {me.name}
                </button>
              ) : null}
            </Panel>
          </form>
        ) : null}

        {waiting.length ? (
          <>
            <nav aria-label="Grade" className="mb-3 flex flex-wrap gap-2">
              <Link href={query(f, { grade: undefined })} className={`chip ${!f.grade ? "on" : ""}`} aria-current={!f.grade ? "page" : undefined}>
                Every grade <span className="fact ml-1 opacity-70">{count("grade", () => true)}</span>
              </Link>
              {grades.filter(([g]) => waiting.some((x) => x.band === g)).map(([g, words]) => (
                <Link key={g} href={query(f, { grade: g })} className={`chip ${f.grade === g ? "on" : ""}`} aria-current={f.grade === g ? "page" : undefined}>
                  {words} <span className="fact ml-1 opacity-70">{count("grade", (x) => x.band === g)}</span>
                </Link>
              ))}
            </nav>
            <form action="/skill-sets/approve" className="panel mb-[18px] flex flex-wrap items-end gap-3 p-4">
              {f.grade ? <input type="hidden" name="grade" value={f.grade} /> : null}
              <label className="field min-w-[14rem]">
                <span className="label">Topic</span>
                <select className="select" name="topic" defaultValue={f.topic ?? ""}>
                  <option value="">Every topic</option>
                  {topics.map((t) => (
                    <option key={t.topic_code} value={t.topic_code!}>
                      {t.topic_name} ({count("topic", (x) => x.topic_code === t.topic_code)})
                    </option>
                  ))}
                </select>
              </label>
              <label className="field min-w-[11rem]">
                <span className="label">Taught</span>
                <select className="select" name="taught" defaultValue={f.taught ?? ""}>
                  <option value="">Taught or not</option>
                  {TAUGHT.map(([v, words]) => (
                    <option key={v} value={v}>
                      {words} ({count("taught", (x) => x.taught === (v === "yes"))})
                    </option>
                  ))}
                </select>
              </label>
              <button type="submit" className="btn secondary">Show</button>
              {narrowed ? <Link href="/skill-sets/approve" className="text-[13px]">Clear</Link> : null}
            </form>

            <form action={approveSkills} className="grid gap-[18px]">
              <input type="hidden" name="back" value={query(f)} />
              <section className="panel" aria-label="Skills waiting">
                <div className="min-w-0 overflow-x-auto">
                  <table className="grid" aria-label="Skills waiting for approval">
                    <thead>
                      <tr>
                        <th>Skill</th>
                        <th>Grade</th>
                        <th>Topic</th>
                        <th>What a child can do</th>
                        <th>{mayApprove ? "Approve" : "Change"}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {shown.map((x) => (
                        <tr key={x.code} data-row={x.code}>
                          <th scope="row" className="min-w-[160px] text-left font-medium">{x.name}</th>
                          <td className="whitespace-nowrap">{school.name(x.band)}</td>
                          <td className="min-w-[140px]">
                            {x.topic_name ?? "—"}
                            {x.taught ? null : <span className="ml-1 inline-block"><Pill tone="monsoon">Not taught yet</Pill></span>}
                          </td>
                          <td className="min-w-[280px] max-w-[520px]">
                            <span className="text-[14px] leading-snug">{x.learning_objective}</span>
                            <details className="mt-1">
                              <summary className="cursor-pointer text-[13px]">Read the levels</summary>
                              <dl className="mt-2 grid gap-1 text-[13px] md:grid-cols-[80px_1fr]">
                                {levelsOf(x).map((d) => (
                                  <div key={d} className="contents">
                                    <dt className="label pt-[2px]">{d}</dt>
                                    <dd className="text-basalt/80">{x.difficulty[d]?.words}</dd>
                                  </div>
                                ))}
                              </dl>
                            </details>
                          </td>
                          <td className="min-w-[180px]">
                            <input type="hidden" name="code" value={x.code} />
                            <input type="hidden" name="version" value={x.version} />
                            {/* this skill alone: the same form, naming the one skill (the action approves only it) */}
                            {mayApprove ? (
                              <button className="btn secondary" type="submit" name="only" value={x.code}>
                                Approve, as {me.name}
                              </button>
                            ) : null}
                            <Link href={`/skill-sets/${x.code}/edit`} className="mt-1 block text-[13px]">
                              {mayApprove ? "Change the words first" : "Change the words"}
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {shown.length === 0 ? <p className="note p-4">Nothing waits under these choices.</p> : null}
              </section>
              {shown.length && mayApprove ? (
                <div className="flex flex-wrap items-center gap-3">
                  <button className="btn" type="submit">
                    Approve {narrowed ? "these" : "all"} {shown.length} {shown.length === 1 ? "skill" : "skills"} as written, as {me.name}
                  </button>
                  <span className="note">Your name goes on each one. Changing a skill later sends it back here.</span>
                </div>
              ) : null}
            </form>
          </>
        ) : null}
      </Body>
    </>
  );
}
