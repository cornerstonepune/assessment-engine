import { notFound } from "next/navigation";
import Link from "@/components/link";
import { Body, Notice, PageHeader, Panel } from "@/components/shell";
import { deadline } from "@/lib/deadline";
import { DIFFICULTIES, skillSet } from "@/lib/queries";
import { saveWords } from "../actions";

type Props = { params: Promise<{ code: string }>; searchParams: Promise<Record<string, string | undefined>> };

// The words of one skill, and nothing else: what a teacher can change without knowing how the
// engine checks a question. Saving sends the skill back for approval.
export default async function EditSkillWords({ params, searchParams }: Props) {
  const [{ code }, q] = await Promise.all([params, searchParams]);
  const s = await deadline(skillSet(code));
  if (!s) notFound();

  return (
    <>
      <PageHeader
        stage={`Skill Map · ${s.name}`}
        title="Change the words"
        sub="What the child can do, and what each level asks of them, in the school's words. The rule every question is checked against stays as it is."
      />
      <Body>
        {q.error === "required" ? <Notice tone="terracotta">Every box needs words. Nothing was saved.</Notice> : null}
        <form action={saveWords} className="grid max-w-[760px] gap-[18px]">
          <input type="hidden" name="code" value={s.code} />
          <Panel title="The skill">
            <div className="grid gap-4">
              <label className="field">
                <span className="label">What the child can do</span>
                <textarea className="textarea" name="learning_objective" defaultValue={s.learning_objective} required />
                <span className="note">One sentence that starts with what the child does, such as &ldquo;Adds …&rdquo;.</span>
              </label>
              <label className="field">
                <span className="label">Short name</span>
                <input className="input" name="name" defaultValue={s.name} required />
              </label>
            </div>
          </Panel>
          <Panel title="Each level in a sentence">
            <div className="grid gap-4">
              {DIFFICULTIES.map((d) => (
                <label key={d} className="field">
                  <span className="label">{d}</span>
                  <textarea className="textarea" name={`words:${d}`} defaultValue={s.difficulty[d]?.words ?? ""} required />
                </label>
              ))}
            </div>
          </Panel>
          <div className="flex flex-wrap items-center gap-3">
            <button className="btn" type="submit">
              Save the words
            </button>
            <Link href={`/skill-sets/${s.code}`} className="chip">
              Cancel
            </Link>
            <span className="note">Saving sends the skill back for approval, so whoever approves it has read these words.</span>
          </div>
        </form>
      </Body>
    </>
  );
}
