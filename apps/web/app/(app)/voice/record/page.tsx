import { notFound } from "next/navigation";
import Link from "@/components/link";
import { PageShell } from "@/components/page-shell";
import { requireStaff } from "@/lib/auth";
import { Icon } from "@/lib/icons";
import { chosenClass, herVoice } from "@/lib/voice-page";
import { W } from "@/lib/voice-words";
import { ClassChoice } from "../class-choice";
import { Recorder } from "./recorder";

// Record a note (task M1-04): Record, Stop, Send. She says the activity's number in the note (the reader reads it); with
// no timetable yet the page names no activity, but takes one (`activity`, the K2 team's number) for when a day's sessions
// can open it. The recording goes from the phone straight to the engine; the form is always one tap away.
export default async function RecordANote({ searchParams }: { searchParams: Promise<{ class?: string; activity?: string }> }) {
  const me = await requireStaff();
  const my = await herVoice(me);
  if (!my.recording) notFound(); // D-065: no recording until Nimish turns it on
  const q = await searchParams;
  const c = chosenClass(my, q.class);
  const activity = q.activity && /^[0-9]{1,4}$/.test(q.activity) ? q.activity : undefined;
  const form = c ? `/voice/form?class=${c.id}` : "/voice/form";
  return (
    <PageShell
      stage={W.back}
      title={c ? `${W.record.title} · ${c.words}` : W.record.title}
      purpose={W.record.purpose}
      action={
        <Link href={form} className="btn secondary inline-flex items-center gap-1.5" data-use-form>
          <Icon name="form" />
          {W.useForm}
        </Link>
      }
      next={{ href: "/today?open=notes", label: W.groups.notes }}
    >
      {c ? <Recorder classId={c.id} say={activity ? W.record.sayActivity(activity) : W.record.say} form={form} /> : <ClassChoice my={my} href={(id) => `/voice/record?class=${id}`} />}
    </PageShell>
  );
}
