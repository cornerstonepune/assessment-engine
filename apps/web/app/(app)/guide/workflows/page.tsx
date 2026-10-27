import Link from "@/components/link";
import { PageShell } from "@/components/page-shell";
import { FlowDrawing, GuideNav, StepList } from "@/components/guide";
import { requireStaff } from "@/lib/auth";
import { guideFacts, nextAfter } from "@/lib/guide";

// The school's steps (goals/guide_for_educators.yaml): the twelve steps agreed with the school, in their four stages, drawn
// from workflows.json, each with who does it and what they see.
export default async function GuideWorkflows() {
  await requireStaff();
  const f = await guideFacts();
  return (
    <PageShell
      stage="Guide"
      title="The school's steps"
      purpose="The steps agreed with the school, in four stages: who does each one, and what they see."
      action={
        <Link href="/guide" className="btn">
          Start here
        </Link>
      }
      next={nextAfter("/guide/workflows")}
    >
      <GuideNav here="/guide/workflows" />
      <div className="grid gap-8">
        <FlowDrawing link={false} />
        <StepList f={f} />
      </div>
    </PageShell>
  );
}
