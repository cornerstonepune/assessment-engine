import Link from "@/components/link";
import { Body, Notice, PageHeader } from "@/components/shell";
import { deadline } from "@/lib/deadline";
import { curriculumRows } from "@/lib/queries-curriculum";
import { skillsWaiting, topics } from "@/lib/queries-people";
import { CurriculumTable } from "./curriculum-table";
import { Topics } from "./topics";
import { requireStaff } from "@/lib/auth";
import { gradesOf, ownClasses, scopeOf } from "@/lib/scope";
import { mayDecide } from "@/lib/decides";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

// Curriculum — the shared tree as one table (goals/t1-topics.yaml, u5-curriculum.yaml, u12-curriculum-table.yaml):
// grade → subject → topic → skill, each row with its questions, worksheets, questions at each level, children assessed
// and whether the person's classes have been taught it (goals/f1f-taught-per-class.yaml). A skill opens its page, where
// its levels, questions and worksheets are read, edited and approved; a skill waiting for approval says so on its row.
// An educator reads grade → topic → skill with what each level asks; the bank's counts, its worksheets by level and the
// other ways into the bank are behind "Question bank details", a link (goals/ux10-declutter.yaml).
export default async function CurriculumPage({ searchParams }: Props) {
  const me = await requireStaff();
  const q = await searchParams;
  // every skill waiting counts, taught or not: one is approved before its topic is switched on (goals/ny1-needs-you.yaml)
  const scope = scopeOf(me);
  const [{ rows, order }, waiting, all, mayApprove, maySay, mine] = await deadline(
    Promise.all([curriculumRows(scope), skillsWaiting(), topics(scope), mayDecide(me, "skills"), mayDecide(me, "topics"), gradesOf(ownClasses(me))]),
  );
  // said of a topic (every skill in it) or of one skill of it (goals/t1-topics-are-operations.yaml)
  const details = q.details === "1";
  const said = q.on ?? q.off;
  const whole = all.find((t) => t.code === said);
  const switched = whole?.name ?? all.flatMap((t) => t.classes.flatMap((c) => c.skills)).find((k) => k.code === said)?.name;
  const its = whole ? "its skills are" : "it is";

  return (
    <>
      <PageHeader
        stage="Curriculum"
        title="Curriculum"
        sub="Each grade's topics and skills, and what a child can do at each level."
      />
      <Body>
        {q.approved === "0" ? (
          <Notice tone="terracotta">Nothing was approved: it changed since this page was opened. Read it again, then approve.</Notice>
        ) : q.approved ? (
          <Notice tone="neem">Approved {q.approved} as written, in your name.</Notice>
        ) : null}
        {switched ? (
          <Notice tone="neem">
            {q.on
              ? `${switched} is taught in ${q.class} now: ${its} on the class's pages and can go on its children's papers`
              : `${switched} is not taught in ${q.class} now: ${its} out of the class's sight`}
            , in your name. No other class changed.
          </Notice>
        ) : null}
        {waiting ? (
          <Notice tone="terracotta">
            {/* approving is the coordinator's; anyone else is told whose it is (goals/ux1-who-sees-what.yaml) */}
            {waiting} {waiting === 1 ? "skill waits" : "skills wait"} for {mayApprove ? "approval" : "the coordinator’s approval"}.{" "}
            <Link href="/skill-sets/approve">{mayApprove ? "Read and approve →" : "Read them →"}</Link>
          </Notice>
        ) : null}
        <p className="mb-3 flex flex-wrap items-center gap-2 text-[12.5px]">
          <Link href={details ? "/" : "/?details=1"}>{details ? "Hide question bank details" : "Question bank details"}</Link>
          {details ? (
            <>
              <Link href="/library" className="chip">
                Every question in the bank
              </Link>
              <Link href="/worksheets/taxonomy" className="chip">
                Every case, with its worksheets
              </Link>
            </>
          ) : null}
        </p>
        <Topics topics={all} me={me.name} open={q.skills && q.in ? { topic: q.skills, section: q.in } : null} fold={q.taught === "1"} />
        <CurriculumTable rows={rows} levels={order} say={maySay} start={mine} details={details} />
      </Body>
    </>
  );
}
