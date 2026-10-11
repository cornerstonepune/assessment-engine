import Link from "@/components/link";
import { Body, Notice, PageHeader, Panel, Pill } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { deadline } from "@/lib/deadline";
import { KIND } from "@/components/question";
import { chargesTable, GRADE_GROUPS, levelsOf, skillSets } from "@/lib/queries";
import { approveSkills } from "../[code]/actions";

// Every skill waiting for approval on one page, in full — what the child can do and each level in
// a sentence — grouped by grade, each approved on its own or all with one press, in the person's own name
// (goals/ui3-curriculum.yaml).
// The engine prepared the words; the person approves or opens one to change it first. A skill whose topic is not
// taught yet is here too, said so: it is approved before it is switched on (goals/ny1-needs-you.yaml).
export default async function ApproveSkills({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const me = await requireStaff();
  const q = await searchParams;
  const [sets, charges] = await deadline(Promise.all([skillSets({ untaught: true }), chargesTable()]));
  const waiting = sets.filter((s) => s.status !== "ratified");
  // the school's grades in order, and any grade a skill holds that the list does not name, under its own name: a
  // skill waiting is never left off the page
  const grades: [string, string][] = [...GRADE_GROUPS, ...[...new Set(waiting.map((x) => x.band))].filter((b) => !GRADE_GROUPS.some(([g]) => g === b)).map((b): [string, string] => [b, b])];

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
        {q.approved === "0" ? (
          <Notice tone="terracotta">Nothing was approved: it changed since this page was opened. Read it again, then approve.</Notice>
        ) : q.approved ? (
          <Notice tone="neem">
            Approved, in your name. {waiting.length} still {waiting.length === 1 ? "waits" : "wait"}.
          </Notice>
        ) : null}
        {waiting.length === 0 && !charges.waiting ? (
          <Notice tone="neem">Every skill is approved.</Notice>
        ) : (
          <form action={approveSkills} className="grid gap-[18px]">
            <input type="hidden" name="back" value="/" />
            {charges.waiting ? (
              <Panel title="What a wrong answer counts against">
                <input type="hidden" name="charges_table" value={JSON.stringify(charges.table)} />
                <p className="text-[15px] leading-snug">
                  A wrong answer counts against the part of the skill that broke. Most mistakes belong to the sum they happen in.
                  These are the ones that belong to something else on these kinds of question:
                </p>
                <ul className="mt-3 grid gap-1 text-[13px]">
                  {charges.rows.map((r) => (
                    <li key={`${r.kind}-${r.code}`}>
                      On a {KIND[r.kind] ?? r.kind}, <b>{r.mistake.toLowerCase()}</b> counts against <b>{r.skill}</b>.
                    </li>
                  ))}
                </ul>
              </Panel>
            ) : null}
            {grades.filter(([band]) => waiting.some((x) => x.band === band)).map(([band, words]) => (
              <section key={band} className="grid gap-[14px]">
                <h2 className="label">{words}</h2>
                {waiting.filter((x) => x.band === band).map((x) => (
                  <Panel key={x.code} title={x.name} label={x.name} aside={x.taught ? undefined : <Pill tone="monsoon">Not taught yet</Pill>}>
                    <input type="hidden" name="code" value={x.code} />
                    <input type="hidden" name="version" value={x.version} />
                    <p className="text-[15px] leading-snug">{x.learning_objective}</p>
                    <dl className="mt-3 grid gap-1 text-[13px] md:grid-cols-[90px_1fr]">
                      {levelsOf(x).map((d) => (
                        <div key={d} className="contents">
                          <dt className="label pt-[2px]">{d}</dt>
                          <dd className="text-basalt/80">{x.difficulty[d]?.words}</dd>
                        </div>
                      ))}
                    </dl>
                    <div className="mt-3 flex flex-wrap items-center gap-3">
                      {/* this skill alone: the same form, naming the one skill (the action approves only it) */}
                      <button className="btn secondary" type="submit" name="only" value={x.code}>
                        Approve this skill, as {me.name}
                      </button>
                      <Link href={`/skill-sets/${x.code}/edit`} className="text-[13px]">
                        Change these words first
                      </Link>
                    </div>
                  </Panel>
                ))}
              </section>
            ))}
            <div className="flex flex-wrap items-center gap-3">
              <button className="btn" type="submit">
                Approve {waiting.length ? `all ${waiting.length} skills` : ""}
                {waiting.length > 0 && charges.waiting ? " and " : ""}
                {charges.waiting ? "what a wrong answer counts against" : ""} as written, as {me.name}
              </button>
              <span className="note">Your name goes on each one. Changing a skill later sends it back here.</span>
            </div>
          </form>
        )}
      </Body>
    </>
  );
}
