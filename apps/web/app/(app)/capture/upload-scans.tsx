"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { scanTicket } from "./actions";

// Scans put in on this page (goals/n8-upload-on-marking.yaml, ADR 0092): a PDF, or phone photos, chosen or dropped. Each
// PDF is sent on its own and every photo chosen together as one paper, its pages in the order the phone took them. The
// browser sends each straight to the engine with a token the site signed (a Vercel function takes at most 4.5 MB), shows
// how much has gone, and says what the engine said; one file refused does not stop the next. The engine checks the
// size and kind and starts the reading; what it found is the run under this, which the page refreshes while it reads.
type Sent = { name: string; done: number; size: number; said: string; ok: boolean | null };
const PHOTO = /\.(jpe?g|png|heic|heif)$/i;

function batches(files: File[]): File[][] {
  const photos = files.filter((f) => f.type.startsWith("image/") || PHOTO.test(f.name));
  return [...files.filter((f) => !photos.includes(f)).map((f) => [f]), ...(photos.length ? [photos] : [])];
}

function send(url: string, token: string, files: File[], progress: (done: number) => void): Promise<{ ok: boolean; said: string }> {
  return new Promise((resolve) => {
    const xhr = new XMLHttpRequest();
    const form = new FormData();
    for (const f of files) form.append("file", f, f.name);
    xhr.open("POST", url);
    xhr.setRequestHeader("X-Upload-Token", token);
    xhr.upload.onprogress = (e) => progress(e.loaded);
    xhr.onload = () => {
      let body: { detail?: string; pages?: number } = {};
      try {
        body = JSON.parse(xhr.responseText) as typeof body;
      } catch {}
      if (xhr.status === 200) resolve({ ok: true, said: `${body.pages ?? 0} pages found; reading them now` });
      else if ([502, 503, 504].includes(xhr.status)) resolve({ ok: false, said: "the engine is restarting; send it again in a minute" });
      else resolve({ ok: false, said: `the engine would not take it: ${body.detail ?? `refused (${xhr.status})`}` });
    };
    xhr.onerror = () => resolve({ ok: false, said: "the engine could not be reached; nothing was sent" });
    xhr.send(form);
  });
}

export function UploadScans({ reading }: { reading: boolean }) {
  const router = useRouter();
  const [sent, setSent] = useState<Sent[]>([]);
  const [over, setOver] = useState(false);
  const busy = sent.some((s) => s.ok === null);

  // while a file is sent or read, the runs below are refreshed: the reading takes a minute or two
  useEffect(() => {
    if (!busy && !reading) return;
    const t = setInterval(() => router.refresh(), 5000);
    return () => clearInterval(t);
  }, [busy, reading, router]);

  async function put(files: File[]) {
    const all = batches(files);
    const first = sent.length;
    const named = all.map((b) => ({
      name: b.length > 1 ? `${b.length} photos (${b[0].name} …)` : b[0].name,
      done: 0,
      size: b.reduce((n, f) => n + f.size, 0),
      said: "waiting to be sent",
      ok: null,
    }));
    setSent((s) => [...s, ...named]);
    const at = (i: number, change: Partial<Sent>) => setSent((s) => s.map((x, k) => (k === first + i ? { ...x, ...change } : x)));
    for (const [i, b] of all.entries()) {
      const ticket = await scanTicket().catch(() => null);
      if (!ticket) {
        at(i, { ok: false, said: "this site cannot reach the engine; nothing was sent" });
        continue;
      }
      at(i, { said: "sending" });
      const out = await send(ticket.url, ticket.token, b, (done) => at(i, { done }));
      at(i, { ...out, done: out.ok ? named[i].size : 0 });
      if (out.ok) router.refresh();
    }
  }

  return (
    <div className="mb-3">
      <label
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          void put([...e.dataTransfer.files]);
        }}
        className={`block cursor-pointer rounded border-2 border-dashed p-4 text-center text-[14px] ${over ? "border-bamboo bg-chalk" : "border-line"}`}
      >
        <span className="font-semibold">Choose scans or drop them here</span>
        <span className="block text-[13px] text-ink-soft">A PDF, or photos of one paper&apos;s pages (JPG, PNG or HEIC), taken in page order.</span>
        <input
          type="file"
          multiple
          accept="application/pdf,.pdf,image/jpeg,image/png,image/heic,image/heif,.heic,.heif"
          aria-label="Choose scans"
          className="sr-only"
          onChange={(e) => {
            void put([...(e.target.files ?? [])]);
            e.target.value = "";
          }}
        />
      </label>
      {sent.length ? (
        <ul aria-label="Scans sent" className="mt-2 grid gap-2 text-[13px]">
          {sent.map((s, i) => (
            <li key={i} className="min-w-0">
              <p>
                <strong>{s.name}</strong> · <span className={s.ok === false ? "text-terracotta" : ""}>{s.said}</span>
              </p>
              <progress
                aria-label={`Sending ${s.name}`}
                value={s.done}
                max={s.size || 1}
                className="h-2 w-full"
              />
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
