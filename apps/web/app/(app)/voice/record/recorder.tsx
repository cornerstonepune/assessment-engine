"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Icon } from "@/lib/icons";
import { W } from "@/lib/voice-words";
import { recordTicket } from "../actions";

// Record, Stop, Send (task M1-04). The phone's own recorder (MediaRecorder); the recording stays on the screen until the
// engine has it, and leaving before then asks first. Sent straight to the engine with a ticket the site signed.
type Stage = "idle" | "recording" | "recorded" | "sending";
const EXT: [RegExp, string][] = [[/webm/, ".webm"], [/mp4|aac/, ".m4a"], [/ogg/, ".ogg"], [/wav/, ".wav"]];
const MIN_BYTES = 1200; // shorter than this is silence: nothing to read

export function Recorder({ classId, say, form }: { classId: string; say: string; form: string }) {
  const router = useRouter();
  const [stage, setStage] = useState<Stage>("idle");
  const [clip, setClip] = useState<Blob | null>(null);
  const [said, setSaid] = useState<string | null>(null);
  const rec = useRef<MediaRecorder | null>(null);
  const url = clip ? URL.createObjectURL(clip) : null;
  useEffect(() => () => void (url && URL.revokeObjectURL(url)), [url]);
  useEffect(() => {
    if (!clip) return;
    const warn = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = W.record.leaving;
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [clip]);

  async function start() {
    setSaid(null);
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setSaid(W.record.noMic);
      return;
    }
    const chunks: Blob[] = [];
    const r = new MediaRecorder(stream);
    r.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    r.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      const blob = new Blob(chunks, { type: r.mimeType || "audio/webm" });
      if (blob.size < MIN_BYTES) {
        setSaid(W.record.nothing);
        setStage("idle");
        return;
      }
      setClip(blob);
      setStage("recorded");
    };
    rec.current = r;
    r.start();
    setStage("recording");
  }

  async function send() {
    if (!clip) return;
    setStage("sending");
    setSaid(null);
    const ticket = await recordTicket().catch(() => null);
    const ext = EXT.find(([re]) => re.test(clip.type))?.[1] ?? ".webm";
    const body = new FormData();
    body.append("file", clip, `note${ext}`);
    body.append("class_id", classId);
    const res = ticket ? await fetch(ticket.url, { method: "POST", headers: { "X-Upload-Token": ticket.token }, body }).catch(() => null) : null;
    const got = res?.ok ? ((await res.json().catch(() => null)) as { note_id?: string } | null) : null;
    if (!got?.note_id) {
      setSaid(W.record.notSent);
      setStage("recorded");
      return;
    }
    setClip(null);
    router.push(`/voice/notes/${got.note_id}`);
  }

  return (
    <section className="panel grid max-w-xl gap-4 p-5" aria-label={W.record.title} data-recorder={stage}>
      <p className="text-[15px] text-basalt/80">{say}</p>
      <div className="flex flex-wrap items-center gap-3">
        {stage === "recording" ? (
          <button type="button" className="btn min-h-14 gap-2 !px-6 text-[17px]" onClick={() => rec.current?.stop()} data-stop>
            <Icon name="stop" />
            {W.record.stop}
          </button>
        ) : stage === "idle" ? (
          <button type="button" className="btn min-h-14 gap-2 !px-6 text-[17px]" onClick={start} data-record>
            <Icon name="record" />
            {W.record.start}
          </button>
        ) : (
          <>
            <button type="button" className="btn min-h-14 gap-2 !px-6 text-[17px]" onClick={send} disabled={stage === "sending"} data-send>
              <Icon name="send" />
              {stage === "sending" ? W.record.sending : W.record.send}
            </button>
            <button type="button" className="btn secondary" onClick={() => (setClip(null), setStage("idle"))} disabled={stage === "sending"}>
              {W.record.again}
            </button>
          </>
        )}
        {stage === "recording" ? (
          <span className="inline-flex items-center gap-2 text-[14px] text-terracotta" role="status">
            <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-terracotta" />
            {W.record.recording}
          </span>
        ) : null}
      </div>
      {url ? <audio controls src={url} className="w-full" data-playback /> : null}
      {said ? (
        <p role="alert" className="grid gap-2 text-[15px] text-terracotta">
          {said}
          <Link href={form} className="btn secondary w-fit">
            {W.useForm}
          </Link>
        </p>
      ) : null}
    </section>
  );
}
