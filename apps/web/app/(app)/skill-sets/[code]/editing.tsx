import Link from "@/components/link";
import { Notice } from "@/components/shell";
import { engineGet } from "@/lib/engine";
import type { Difficulty, SkillSet } from "@/lib/queries";
import { type SampleRow, sampleChoices, sampleCount, type WaysRow } from "@/lib/queries-skills";
import { LevelApproval } from "./level-approval";
import { LevelKinds } from "./level-kinds";
import { type Editing, LevelSamples } from "./samples";
import type { SampleInitial } from "./sample-shape";
import { LevelWays } from "./ways";

// The parts of the skill page that change a skill (goals/edt_edit_samples_and_kinds.yaml): an English level with its
// kinds, samples and approval; the form a link opened; how the page says a change was saved; and, for a skill whose questions code makes,
// why its questions are not changed here. Nimish, 2026-10-24: "What happens if he wants to make any changes there?"

type Editor = Awaited<ReturnType<typeof editingOf>> | null;

/** One English level: its kinds (changed here by whoever may change the skill), its samples, then its approval. */
export function EnglishLevel(p: {
  s: SkillSet;
  level: Difficulty;
  ways: WaysRow[];
  samples: SampleRow[];
  editing: Editor;
  mayApprove: boolean;
  opened: string;
}) {
  const { s, level, editing } = p;
  return (
    <>
      {editing ? (
        <LevelKinds code={s.code} level={level} ways={p.ways} choices={editing.choices} adding={editing.adding?.level === level ? editing.adding : null} />
      ) : (
        <LevelWays ways={p.ways} level={level} />
      )}
      <LevelSamples samples={p.samples} level={level} editing={editing} />
      <LevelApproval s={s} d={level} mayApprove={p.mayApprove} opened={p.opened} />
    </>
  );
}

/** A level's sentence, changed on the words page at that level. */
export function SentenceLink({ code, level }: { code: string; level: string }) {
  return (
    <Link href={`/skill-sets/${code}/edit#words-${level}`} className="text-[12.5px]">
      Change this level&rsquo;s sentence
    </Link>
  );
}

export function MadeByCode() {
  return (
    <p className="note mt-[14px]">
      This skill&rsquo;s questions are made by code from each level&rsquo;s rule, so they are not edited here; its
      description and each level&rsquo;s sentence are.
    </p>
  );
}

/** What the page says after a change (`?changed=`, `?at=`), or why one was refused (`?refused=`). */
export function Changed({ q }: { q: Record<string, string | undefined> }) {
  return (
    <>
      {q.changed ? (
        <Notice tone="neem">
          {CHANGED_WORDS[q.changed] ?? "Saved."} {q.at ?? "That level"} waits for approval again, so whoever approves it reads
          it first; what it replaced is kept.
        </Notice>
      ) : null}
      {q.refused ? <Notice tone="terracotta">{q.refused} Nothing was changed.</Notice> : null}
    </>
  );
}

const CHANGED_WORDS: Record<string, string> = {
  sample: "The sample is saved.",
  added: "The sample is added.",
  removed: "The sample is taken off.",
  kind_added: "The kind is added with its samples.",
  kind_removed: "The kind is taken off.",
};

/** The sample form or kind form a link opened (`?edit=<level>~<kind>~<number or new>`, `?addkind=<level>~<kind>`), the
 *  sample as its form shows it (from the engine, which reads its words the same way back), and what the forms pick from. */
export async function editingOf(
  code: string,
  q: Record<string, string | undefined>,
): Promise<NonNullable<Editing> & { adding: { level: string; kind: string; need: number } | null }> {
  const [level, kind, ord] = (q.edit ?? "").split("~");
  const [addLevel, addKind] = (q.addkind ?? "").split("~");
  const form = async (): Promise<SampleInitial | null> => {
    if (!level || !kind || !/^\d+$/.test(ord ?? "")) return null;
    const res = await engineGet(
      `/skill/${code}/sample/form?level=${encodeURIComponent(level)}&kind=${encodeURIComponent(kind)}&ord=${ord}`,
    ).catch(() => null);
    return res?.ok ? ((await res.json()) as SampleInitial) : null;
  };
  const [choices, start, held] = await Promise.all([
    sampleChoices(code),
    form(),
    addLevel && addKind ? sampleCount(code, addLevel, addKind) : 0,
  ]);
  const adding =
    addLevel && addKind && choices.kinds.some((k) => k.code === addKind)
      ? { level: addLevel, kind: addKind, need: Math.max(0, choices.few - held) }
      : null;
  return { code, open: q.edit ?? null, start, choices, adding };
}

