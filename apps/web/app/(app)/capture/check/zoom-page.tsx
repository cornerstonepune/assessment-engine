"use client";

import { useState } from "react";

// A whole page of a photographed paper, across the column and readable by a click: it opens at the picture's own size
// inside a frame to scroll about in, and a second click puts it back (goals/ck1-the-picture-is-the-question.yaml).
export function ZoomPage({ src, alt }: { src: string; alt: string }) {
  const [big, setBig] = useState(false);
  return (
    <div className={big ? "max-h-[75vh] overflow-auto border border-basalt/14 bg-chalk" : "border border-basalt/14 bg-chalk"}>
      <button
        type="button"
        aria-pressed={big}
        aria-label={big ? "Shrink the page to fit" : "Enlarge the page to its full size"}
        onClick={() => setBig(!big)}
        className={`block ${big ? "cursor-zoom-out" : "cursor-zoom-in"}`}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={src} alt={alt} className={big ? "block h-auto max-w-none" : "block h-auto w-full"} />
      </button>
    </div>
  );
}
