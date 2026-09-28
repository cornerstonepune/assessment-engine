"use client";

export function PrintButton() {
  return (
    <button
      type="button"
      className="chip cursor-pointer print:hidden"
      onClick={() => window.print()}
    >
      Print or save as PDF
    </button>
  );
}
