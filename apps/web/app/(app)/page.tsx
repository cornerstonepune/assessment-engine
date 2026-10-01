import Link from "@/components/link";
import { Body, Notice, PageHeader } from "@/components/shell";
import { deadline } from "@/lib/deadline";
import { curriculumRows } from "@/lib/queries-curriculum";
import { CurriculumTable } from "./curriculum-table";
import { requireStaff } from "@/lib/auth";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

// Curriculum — the shared tree as one table (goals/t1-topics.yaml, u5-curriculum.yaml, u12-curriculum-table.yaml):
// grade → subject → topic → skill, each row with its questions, worksheets, questions at each level, children assessed
// and whether it is taught. A skill opens its page, where its levels, questions and worksheets are read, edited and
// approved; a skill waiting for approval says so on its row.
export default async function CurriculumPage({ searchParams }: Props) {
  await requireStaff();
  const q = await searchParams;
  const { rows } = await deadline(curriculumRows());
  // a skill is a row under every grade one of its levels belongs to; it waits once (code review, 2026-09-30)
  const waiting = new Set(rows.filter((r) => r.draft).map((r) => r.href)).size;

  return (
    <>
      <PageHeader
        stage="Curriculum"
        title="Curriculum"
        sub="Every grade's skills, by subject and topic, each written as what a child can do, with its questions, worksheets and levels, how many children have been assessed on it, and whether it is taught. Open a grade, then a topic; a skill opens its page."
      />
      <Body>
        {q.approved ? <Notice tone="neem">Approved {q.approved} as written, in your name.</Notice> : null}
        {waiting ? (
          <Notice tone="terracotta">
            {waiting} {waiting === 1 ? "skill waits" : "skills wait"} for approval.{" "}
            <Link href="/skill-sets/approve">Read and approve →</Link>
          </Notice>
        ) : null}
        <p className="mb-4 flex flex-wrap gap-2">
          <Link href="/worksheets/taxonomy" className="chip">
            Read the same worksheets by the taxonomy
          </Link>
          <Link href="/library" className="chip">
            Every question in the bank
          </Link>
        </p>
        <CurriculumTable rows={rows} />
      </Body>
    </>
  );
}
