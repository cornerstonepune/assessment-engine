import Link from "@/components/link";
import { FilterBar } from "@/components/filter-bar";
import { PageShell } from "@/components/page-shell";
import { Notice } from "@/components/shell";
import { deadline } from "@/lib/deadline";
import { curriculumRows } from "@/lib/queries-curriculum";
import { skillsWaiting } from "@/lib/queries-people";
import { CurriculumCounts } from "@/components/curriculum-counts";
import { gradesOf, ownClasses } from "@/lib/scope";
import { CurriculumSkills } from "./curriculum-skills";
import {
  STATUS_WORDS,
  chosen,
  skillLines,
  statusOf,
} from "@/lib/curriculum-list";
import { requireStaff } from "@/lib/auth";
import { scopeOf } from "@/lib/scope";
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
  const [{ rows, order }, waiting, mayApprove, maySay, mine] =
    await deadline(
      Promise.all([
        curriculumRows(scope),
        skillsWaiting(),
        mayDecide(me, "skills"),
        mayDecide(me, "topics"),
        gradesOf(ownClasses(me)),
      ]),
    );
  const details = q.details === "1";
  const lines = skillLines(rows, order);
  const page = Math.max(1, Number(q.page) || 1);
  const href = (n: number) => {
    const p = new URLSearchParams(
      Object.entries(q).filter(
        ([k, v]) => v && !["page", "approved", "on", "off"].includes(k),
      ) as [string, string][],
    );
    if (n > 1) p.set("page", String(n));
    return p.size ? `/?${p}` : "/";
  };
  const count = (st: string) => lines.filter((l) => statusOf(l) === st).length;
  const grades = [
    ...new Map(lines.map((l) => [l.gradeCode, l.grade])).entries(),
  ] as [string, string][];
  const subjects = [...new Set(lines.map((l) => l.subject))];
  const topicOptions = [
    ...new Map(
      lines
        .filter((l) => !q.grade || l.gradeCode === q.grade)
        .filter((l) => !q.subject || l.subject === q.subject)
        .map((l) => [l.topicCode, l.topic]),
    ).entries(),
  ] as [string, string][];
  // a topic left in the address by another grade or subject is not one of this list's: it filters nothing
  const topic = topicOptions.some(([code]) => code === q.topic) ? q.topic : undefined;
  const shown = chosen(lines, { ...q, topic });

  return (
    <PageShell
      stage="Curriculum"
      title="Curriculum"
      purpose="Every skill of every grade, with its levels and where it stands. Open a skill to read what each level asks."
      action={
        <Link
          href={waiting ? "/skill-sets/approve" : "/library"}
          className="btn"
        >
          {waiting
            ? mayApprove
              ? `Skills to approve (${waiting})`
              : `Read the ${waiting} waiting`
            : "Open the question bank"}
        </Link>
      }
      next={{ href: "/taught", label: "Teaching" }}
      details={{
        href: details ? "/" : "/?details=1",
        label: details ? "Hide question bank details" : "Question bank details",
      }}
    >
      {q.approved === "0" ? (
        <Notice tone="terracotta">
          Nothing was approved: it changed since this page was opened. Read it
          again, then approve.
        </Notice>
      ) : q.approved ? (
        <Notice tone="neem">
          Approved {q.approved} as written, in your name.
        </Notice>
      ) : null}
      {waiting ? (
        <Notice tone="terracotta">
          {/* approving is the coordinator's; anyone else is told whose it is (goals/ux1-who-sees-what.yaml) */}
          {waiting} {waiting === 1 ? "skill waits" : "skills wait"} for{" "}
          {mayApprove ? "approval" : "the coordinator’s approval"}.{" "}
          <Link href="/skill-sets/approve">
            {mayApprove ? "Read and approve →" : "Read them →"}
          </Link>
        </Notice>
      ) : null}
      {details ? (
        <>
          <p className="mb-3 flex flex-wrap items-center gap-2 text-[12.5px]">
            <Link href="/library">Every question in the bank</Link>
            {" · "}
            <Link href="/worksheets/taxonomy">
              Every case, with its worksheets
            </Link>
          </p>
          <CurriculumCounts
            rows={rows}
            levels={order}
            say={maySay}
            start={mine}
            details
          />
        </>
      ) : (
        <>
          <FilterBar
            action="/"
            filters={[
              {
                name: "grade",
                label: "Grade",
                value: q.grade,
                all: "Every grade",
                options: grades,
              },
              {
                name: "subject",
                label: "Subject",
                value: q.subject,
                all: "Every subject",
                options: subjects.map((s) => [s, s] as const),
              },
              {
                name: "topic",
                label: "Topic",
                value: topic,
                all: "Every topic",
                options: topicOptions,
              },
              {
                name: "status",
                label: "Status",
                value: q.status,
                all: "Any status",
                options: STATUS_WORDS.map(
                  ([v, w]) => [v, `${w} (${count(v)})`] as const,
                ),
              },
            ]}
            search={{ name: "q", value: q.q, placeholder: "Find a skill" }}
          />
          <section aria-label="Skills">
            <CurriculumSkills
              lines={shown}
              say={maySay}
              page={page}
              pageHref={href}
            />
            {shown.length === 0 ? (
              <p className="note mt-2">No skill matches these filters.</p>
            ) : null}
          </section>
        </>
      )}
    </PageShell>
  );
}
