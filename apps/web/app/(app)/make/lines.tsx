"use client";

import { useState } from "react";
import type { LineLevel, LineTopic } from "@/lib/maker";

type Line = { topic: string; skill: string; level: string; n: string };

/** A skill's first level of the class's grade, the usual one (`level.usual`) where it has it; else its first. */
function firstLevel(levels: LineLevel[], usual: string): string {
  const own = levels.filter((l) => !l.above);
  return (own.find((l) => l.level === usual) ?? own[0] ?? levels[0])?.level ?? "";
}

/** A line from `skill~level~n`, under the topic its skill is in. */
function lineOf(topics: LineTopic[], v: string): Line {
  const [skill = "", level = "", n = ""] = v.split("~");
  const topic = topics.find((t) => t.skills.some((s) => s.code === skill))?.code ?? "";
  return { topic, skill: topic ? skill : "", level: topic ? level : "", n };
}

// The lines of a paper (goals/l7-a-line-is-topic-skill-level-number.yaml, ADR 0081): each one a topic, then one of
// that topic's skills, then its level, then how many questions, so one paper can take its lines from different topics.
// Each line reaches the form as the maker has always read it, `s` (skill~level) and `n`. With `fill`, a topic chosen
// above the lines fills them with that topic's skills at the class's grade (goals/ui2-assessments.yaml).
export function MakerLines({ topics, start, usual, fill = false, topic: chosen = "" }: {
  topics: LineTopic[]; start: string[]; usual: string; fill?: boolean; topic?: string;
}) {
  const [lines, setLines] = useState<Line[]>(() => start.map((v) => lineOf(topics, v)));
  const [topic, setTopic] = useState(chosen);
  const set = (i: number, change: Partial<Line>) => setLines((ls) => ls.map((l, j) => (j === i ? { ...l, ...change } : l)));
  const fillFrom = (code: string) => {
    setTopic(code);
    const filled = (topics.find((t) => t.code === code)?.fill ?? []).map((v) => lineOf(topics, v));
    if (code) setLines((ls) => ls.map((l, i) => filled[i] ?? { topic: i === 0 ? code : "", skill: "", level: "", n: i === 0 ? l.n : "" }));
  };
  return (
    <>
      {fill ? (
        <label className="field">
          <span className="label">Start from a topic</span>
          <select className="select" name="topic" value={topic} onChange={(e) => fillFrom(e.target.value)}>
            <option value="">Choose each line yourself</option>
            {topics.map((t) => (
              <option key={t.code} value={t.code}>{t.name}</option>
            ))}
          </select>
          <span className="note">A topic fills the lines with its skills at this class&rsquo;s grade; change any line before you see the papers.</span>
        </label>
      ) : null}
      {lines.map((l, i) => {
        const skills = topics.find((t) => t.code === l.topic)?.skills ?? [];
        const levels = skills.find((s) => s.code === l.skill)?.levels ?? [];
        return (
          <div key={i} role="group" aria-label={`Line ${i + 1}`} className="grid grid-cols-[minmax(0,1fr)_112px] gap-2 border-t border-basalt/10 pt-2">
            <input type="hidden" name="s" value={l.skill && l.level ? `${l.skill}~${l.level}` : ""} />
            <select className="select col-span-2" aria-label={`Topic ${i + 1}`} value={l.topic} onChange={(e) => set(i, { topic: e.target.value, skill: "", level: "" })}>
              <option value="">Topic</option>
              {topics.map((t) => (
                <option key={t.code} value={t.code}>{t.name}</option>
              ))}
            </select>
            <select
              className="select col-span-2"
              aria-label={`Skill ${i + 1}`}
              value={l.skill}
              disabled={!l.topic}
              onChange={(e) => set(i, { skill: e.target.value, level: firstLevel(skills.find((s) => s.code === e.target.value)?.levels ?? [], usual) })}
            >
              <option value="">{l.topic ? "Skill" : "Choose a topic first"}</option>
              {skills.map((s) => (
                <option key={s.code} value={s.code}>{s.note ? `${s.name} · ${s.note}` : s.name}</option>
              ))}
            </select>
            <select className="select" aria-label={`Level ${i + 1}`} value={l.level} disabled={!l.skill} onChange={(e) => set(i, { level: e.target.value })}>
              <option value="">Level</option>
              {levels.map((x) => (
                <option key={x.level} value={x.level}>{[x.level, x.above, `${x.n} questions`].filter(Boolean).join(" · ")}</option>
              ))}
            </select>
            <input className="input" name="n" type="number" min={1} max={40} value={l.n} onChange={(e) => set(i, { n: e.target.value })} aria-label={`Questions ${i + 1}`} placeholder="How many" />
          </div>
        );
      })}
    </>
  );
}
