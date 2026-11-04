import { notFound } from "next/navigation";
import Link from "@/components/link";
import { EmptyState } from "@/components/empty-state";
import { PageShell } from "@/components/page-shell";
import { requireStaff } from "@/lib/auth";
import { StatusChip } from "@/components/status-chip";
import { ICON_SIZE, Icon, type IconName, MARK_ICON } from "@/lib/icons";
import { daysLate, fromDraft, type Draft } from "@/lib/voice-check";
import { activitiesOf, draftOf } from "@/lib/voice";
import { herVoice, schoolToday } from "@/lib/voice-page";
import { classWords, SCHOOL_ZONE } from "@/lib/voice-types";
import { MARKS, W } from "@/lib/voice-words";
import { confirmNote } from "../../actions";
import { Board } from "../../board";
import { Rereads } from "./rereads";

// Confirm one note (task M1-04): what she said on the left, line by line beside its words; the class's children on the
// right, already marked from it; the red problems pinned on top. One note a screen, its own Confirm, never one over all.
const UUID = /^[0-9a-f-]{36}$/;

export default async function ConfirmNote({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!UUID.test(id)) notFound();
  const me = await requireStaff();
  const my = await herVoice(me);
  const draft = await draftOf(me, id);
  if (!draft) notFound();
  const queued = my.notes.find((n) => n.id === id);
  const c = my.classes.find((x) => x.id === queued?.class_id);
  const klass = c ? classWords(c) : "";
  const form = { href: c ? `/voice/form?class=${c.id}` : "/voice/form", label: W.fillForm };
  const heard = new Date(draft.received_at).toLocaleString("en-IN", { timeZone: SCHOOL_ZONE, day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hour12: false });
  return (
    <PageShell
      stage={W.back}
      title={W.confirm.title}
      purpose={W.confirm.purpose}
      action={
        <Link href={form.href} className="btn secondary inline-flex items-center gap-1.5">
          <Icon name="form" />
          {W.useForm}
        </Link>
      }
      next={{ href: "/today?open=notes", label: W.groups.notes }}
    >
      <div className="mb-4 flex flex-wrap items-center gap-3 text-[14px]" data-note-head>
        <span className="font-medium">{klass}</span>
        <span className="text-basalt/70">{heard}</span>
        <Late draft={draft} />
        {my.recording ? <audio controls preload="none" src={`/api/voice/${id}`} aria-label={W.confirm.play} className="h-9 max-w-full" /> : null}
      </div>
      <Body draft={draft} klass={klass} grade={c?.grade} form={form} />
    </PageShell>
  );
}

function Late({ draft }: { draft: Draft }) {
  const n = daysLate(draft.taught_on, draft.received_at, SCHOOL_ZONE);
  if (n < 1) return null;
  return <StatusChip state="late" round words={n === 1 ? W.facts.late : W.facts.lateDays(n)} />;
}

async function Body({ draft, klass, grade, form }: { draft: Draft; klass: string; grade?: string; form: { href: string; label: string } }) {
  if (draft.status === "confirmed") return <EmptyState next={{ href: "/today?open=notes", label: W.groups.notes }}>{W.confirm.done}.</EmptyState>;
  if (draft.status === "left_unconfirmed") return <EmptyState next={{ href: "/today", label: W.back }}>{W.confirm.expired}</EmptyState>;
  if (draft.status === "received")
    return (
      <section className="panel grid justify-items-start gap-2 p-4" data-reading>
        <StatusChip state="reading" round words={W.confirm.reading} />
        <p className="text-[14px] text-basalt/70">{W.confirm.readingMore}</p>
        <Rereads />
      </section>
    );
  if (draft.kind === "incident")
    return (
      <section className="panel grid justify-items-start gap-2 p-4" data-incident>
        <StatusChip state="late" round words={W.confirm.incident} />
        <Heard draft={draft} />
      </section>
    );
  const said = draft.lines.some((l) => l.section !== "sentence");
  if (!said || !grade)
    return (
      <section className="panel grid justify-items-start gap-3 p-4" data-could-not>
        <StatusChip state="fixThis" round words={draft.heard ? W.confirm.couldNot : W.record.nothing} />
        <Link href={form.href} className="btn w-fit gap-1.5" data-to-form>
          <Icon name="form" />
          {form.label}
        </Link>
      </section>
    );
  const today = schoolToday();
  const activities = await activitiesOf(grade);
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <section className="panel h-fit p-4" aria-label={W.confirm.heard}>
        <h2 className="mb-2 text-[16px]">{W.confirm.heard}</h2>
        <Heard draft={draft} />
      </section>
      <Board start={fromDraft(draft)} enrolled={draft.enrolled} klass={klass} activities={[...activities]} today={today} draft={draft} button={W.confirm.button} send={confirmNote.bind(null, draft.note_id)} />
    </div>
  );
}

/** One line per draft item beside the words it came from: its mark's icon, its name, her words; a line with trouble says so. */
function Heard({ draft }: { draft: Draft }) {
  return (
    <ol className="grid gap-2" data-heard>
      {draft.lines.map((l) => {
        const icon: IconName | null = (MARKS as readonly string[]).includes(l.section) ? MARK_ICON[l.section as (typeof MARKS)[number]] : l.section === "rest" ? "as-expected" : l.section === "activity" ? "activity" : l.section === "incident" ? "incident" : l.section === "sentence" ? "note" : null;
        return (
          <li key={l.section} className="grid grid-cols-[1.5rem_7rem_minmax(0,1fr)] items-start gap-2 border-b border-basalt/8 pb-2 text-[15px]" data-line={l.section}>
            <span className="pt-0.5">{icon ? <Icon name={icon} size={ICON_SIZE.table} /> : null}</span>
            <span className="font-medium">{W.marks[l.section as keyof typeof W.marks] ?? W.sections[l.section] ?? l.section}</span>
            <span className="min-w-0">
              “{l.words}”{l.problems.length ? <StatusChip state="fixThis" round compact note={undefined} /> : null}
              {l.notes.map((n) => (
                <span key={n} className="block text-[12.5px] text-basalt/62">
                  {n}
                </span>
              ))}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
