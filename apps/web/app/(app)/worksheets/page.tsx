import { redirect } from "next/navigation";
import { Body, PageHeader } from "@/components/shell";
import { Library } from "./library";
import { requireStaff } from "@/lib/auth";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

// Worksheets (goals/ui3-curriculum.yaml): the library, every question in the bank on a numbered worksheet, by skill and
// level. A class's week of papers is approved under Assessments (/papers/approve); its old address here opens it there.
export default async function WorksheetsPage({ searchParams }: Props) {
  await requireStaff();
  const q = await searchParams;
  if (q.section) {
    const kept = Object.entries(q).filter((e): e is [string, string] => typeof e[1] === "string");
    redirect(`/papers/approve?${new URLSearchParams(kept).toString()}`);
  }
  return (
    <>
      <PageHeader
        stage="Curriculum · Worksheets"
        title="Worksheets"
        sub="Every question in the bank on a numbered worksheet, by skill and level. A class's papers for a week are approved under Assessments."
      />
      <Body>
        <Library q={q} />
      </Body>
    </>
  );
}
