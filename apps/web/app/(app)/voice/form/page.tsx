import Link from "@/components/link";
import { PageShell } from "@/components/page-shell";
import { requireStaff } from "@/lib/auth";
import { Icon } from "@/lib/icons";
import { blankWork } from "@/lib/voice-check";
import { activitiesOf } from "@/lib/voice";
import { chosenClass, herVoice, schoolToday } from "@/lib/voice-page";
import { enginePost } from "@/lib/engine";
import { W } from "@/lib/voice-words";
import { saveForm } from "../actions";
import { Board } from "../board";
import { ClassChoice } from "../class-choice";

// The form (task M1-04): what a voice note says, put in by tapping. Pick a mark, tap the children; nothing is ticked and
// the rest starts off; Save, under the count line, is her confirmation. Her class is her role grant's, never typed.
export default async function TheForm({ searchParams }: { searchParams: Promise<{ class?: string }> }) {
  const me = await requireStaff();
  const my = await herVoice(me);
  const q = await searchParams;
  const c = chosenClass(my, q.class);
  const today = schoolToday();
  const record = { href: c ? `/voice/record?class=${c.id}` : "/voice/record", label: W.form.recordInstead };
  return (
    <PageShell
      stage={W.back}
      title={c ? `${W.form.title} · ${c.words}` : W.form.title}
      purpose={W.form.purpose}
      action={
        my.recording ? (
          <Link href={record.href} className="btn secondary inline-flex items-center gap-1.5">
            <Icon name="record" />
            {record.label}
          </Link>
        ) : null
      }
      next={{ href: "/today", label: W.back }}
    >
      {c ? <FormBoard id={c.id} grade={c.grade} words={c.words} actor={me.email} today={today} /> : <ClassChoice my={my} href={(id) => `/voice/form?class=${id}`} />}
    </PageShell>
  );
}

async function FormBoard({ id, grade, words, actor, today }: { id: string; grade: string; words: string; actor: string; today: string }) {
  const [rolls, activities] = await Promise.all([enginePost("/voice/class", { actor, class_id: id, day: today }) as Promise<{ rolls: string[] }>, activitiesOf(grade)]);
  return <Board start={blankWork(today)} enrolled={rolls.rolls} klass={words} activities={[...activities]} today={today} button={W.form.save} send={saveForm.bind(null, id)} />;
}
