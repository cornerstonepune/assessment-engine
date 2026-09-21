import Link from "@/components/link";
import { Body, Notice, PageHeader, Panel } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { deadline } from "@/lib/deadline";
import { DIFFICULTIES, gradeWords, skillSets } from "@/lib/queries";
import { approveSkills } from "../[code]/actions";

// Every skill waiting for approval on one page, in full — what the child can do and each level in
// a sentence — so a person reads them once and approves them with one press, in their own name.
// The engine prepared the words; the person approves or opens one to change it first.
export default async function ApproveSkills() {
  const me = await requireStaff();
  const sets = await deadline(skillSets());
  const waiting = sets.filter((s) => s.status !== "ratified");

  return (
    <>
      <PageHeader
        stage="Skill Map"
        title="Approve the skills"
        sub="The engine has written each skill as what a child can do, and each level as a sentence. Read them, then approve them as written — or open one and change its words first."
      />
      <Body>
        <Link href="/" className="chip mb-[18px] inline-block">
          ← Skill Map
        </Link>
        {waiting.length === 0 ? (
          <Notice tone="neem">Every skill is approved.</Notice>
        ) : (
          <form action={approveSkills} className="grid gap-[18px]">
            <input type="hidden" name="back" value="/" />
            {waiting.map((s) => (
              <Panel key={s.code} title={`${gradeWords(s.band)} · ${s.name}`}>
                <input type="hidden" name="code" value={s.code} />
                <input type="hidden" name="version" value={s.version} />
                <p className="text-[15px] leading-snug">{s.learning_objective}</p>
                <dl className="mt-3 grid gap-1 text-[13px] md:grid-cols-[90px_1fr]">
                  {DIFFICULTIES.map((d) => (
                    <div key={d} className="contents">
                      <dt className="label pt-[2px]">{d}</dt>
                      <dd className="text-basalt/80">{s.difficulty[d]?.words}</dd>
                    </div>
                  ))}
                </dl>
                <Link href={`/skill-sets/${s.code}/edit`} className="mt-3 inline-block text-[13px]">
                  Change these words first
                </Link>
              </Panel>
            ))}
            <div className="flex flex-wrap items-center gap-3">
              <button className="btn" type="submit">
                Approve all {waiting.length} as written, as {me.name}
              </button>
              <span className="note">Your name goes on each one. Changing a skill later sends it back here.</span>
            </div>
          </form>
        )}
      </Body>
    </>
  );
}
