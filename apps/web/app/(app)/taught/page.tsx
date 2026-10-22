import Link from "@/components/link";
import { Notice } from "@/components/shell";
import { PageShell } from "@/components/page-shell";
import { requireStaff } from "@/lib/auth";
import { deadline } from "@/lib/deadline";
import { skillsWaiting, topics } from "@/lib/queries-people";
import { scopeOf } from "@/lib/scope";
import { mayDecide } from "@/lib/decides";
import { Topics } from "../topics";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

// Taught this week (goals/uxn2-taught-this-week.yaml): Wednesday's step. The educator says which topics each class has
// been taught; until then a topic's skills are on none of that class's papers (goals/f1f-taught-per-class.yaml). It was
// the top of the Curriculum page, where nothing said it was the week's first job. The words, the switches and who may say
// them are unchanged; only the page is its own, with the week's next step under it.
export default async function TaughtPage({ searchParams }: Props) {
  const me = await requireStaff();
  const q = await searchParams;
  const scope = scopeOf(me);
  const [waiting, all, mayApprove] = await deadline(Promise.all([skillsWaiting(), topics(scope), mayDecide(me, "skills")]));
  // said of a topic (every skill in it) or of one skill of it (goals/t1-topics-are-operations.yaml)
  const said = q.on ?? q.off;
  const whole = all.find((t) => t.code === said);
  const switched = whole?.name ?? all.flatMap((t) => t.classes.flatMap((c) => c.skills)).find((k) => k.code === said)?.name;
  const its = whole ? "its skills are" : "it is";
  return (
    <PageShell
      stage="Taught this week"
      title="Taught this week"
      purpose="Say which topics each class has been taught. Until you do, a topic's skills stay off that class's papers."
      action={
        <Link href="#not-taught" className="btn">
          Say what was taught
        </Link>
      }
      next={{ href: "/papers/approve", label: "Papers to approve" }}
      details={{ href: "/", label: "The whole curriculum" }}
    >
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
      <Topics topics={all} me={me.name} open={q.skills && q.in ? { topic: q.skills, section: q.in } : null} fold />
    </PageShell>
  );
}
