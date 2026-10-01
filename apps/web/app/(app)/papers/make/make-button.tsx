"use client";

import { useEffect, useState } from "react";

// The papers made are the papers shown. A choice changed after seeing them — another kind, a child ticked, a change
// for one child — was made as the papers shown, and the change silently dropped (code review, 2026-09-30). So any
// change to the choice stops the button until the papers are seen again; the button names the kind it makes.
export function MakeButton({ n, kind, ready }: { n: number; kind: string; ready: boolean }) {
  const [changed, setChanged] = useState(false);
  useEffect(() => {
    // a child's change sits in the table, outside the form, tied to it by `form="choose"`: `.form` follows that
    const seen = (e: Event) => {
      if ((e.target as HTMLInputElement | HTMLSelectElement | null)?.form?.id === "choose") setChanged(true);
    };
    document.addEventListener("input", seen);
    document.addEventListener("change", seen);
    return () => {
      document.removeEventListener("input", seen);
      document.removeEventListener("change", seen);
    };
  }, []);
  return (
    <>
      <button className="btn" type="submit" disabled={!ready || changed}>
        Make and approve {n} {kind} {n === 1 ? "paper" : "papers"}
      </button>
      <p className="note mt-2" role="status">
        {changed
          ? "You changed what to make. See the papers again before they are made."
          : ready
            ? "They print in your name, each with its own code, and land in Papers."
            : "Untick the children whose paper cannot be made, or change what they are given, and see the papers again."}
      </p>
    </>
  );
}
