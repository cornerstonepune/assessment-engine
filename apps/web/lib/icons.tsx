import type { ReactNode } from "react";

// Every icon the K2 screens draw, and the status chip's, behind one lookup (task M1-04): a proper icon library is being
// drawn (teacher-os design/), and swapping to it is this one file. Each is the inside of a 16 × 16 stroke drawing; `Icon`
// draws it at a size. A mark on a child is an icon first (above a triangle up, below a triangle down, not willing a hand,
// absent a dashed ring), so it reads without its colour, and below is never red.
export const ICONS = {
  // the four tones of a state (components/status-chip.tsx): a tick, a clock, a triangle with a mark, a ring
  ok: <path d="M3.2 8.4l3 3 6.4-6.8" />,
  wait: (
    <>
      <circle cx="8" cy="8" r="5.6" />
      <path d="M8 4.8V8l2.2 1.4" />
    </>
  ),
  act: (
    <>
      <path d="M8 2.4l6 10.6H2z" />
      <path d="M8 6.6v3M8 11.4v.1" />
    </>
  ),
  quiet: <circle cx="8" cy="8" r="4.6" />,
  // the marks a note gives a child
  above: <path d="M8 3l5.5 9.5h-11z" />,
  below: <path d="M8 13l5.5-9.5h-11z" />,
  not_willing: <path d="M5 8.5V4.6a1 1 0 012 0V8M7 7.5V3.6a1 1 0 012 0V8M9 7.8V4.6a1 1 0 012 0v4.6c0 2.6-1.6 4.3-4 4.3-1.7 0-2.6-.8-3.5-2.2L2.4 9.4a1 1 0 011.6-1.1L5 9.5" />,
  absent: <circle cx="8" cy="8" r="5.4" strokeDasharray="2.2 2" />,
  as_expected: <circle cx="8" cy="8" r="2.2" fill="currentColor" />,
  clear: <path d="M4.5 4.5l7 7M11.5 4.5l-7 7" />,
  // recording
  mic: (
    <>
      <rect x="6" y="1.8" width="4" height="8" rx="2" />
      <path d="M3.6 7.6a4.4 4.4 0 008.8 0M8 12v2.4" />
    </>
  ),
  stop: <rect x="4" y="4" width="8" height="8" fill="currentColor" />,
  send: <path d="M2.5 8h9M8.5 4l4 4-4 4" />,
  play: <path d="M5 3.2l8 4.8-8 4.8z" fill="currentColor" />,
  form: <path d="M4 2.5h8v11H4zM6 5.5h4M6 8h4M6 10.5h2.5" />,
  search: (
    <>
      <circle cx="7" cy="7" r="4.2" />
      <path d="M10.2 10.2l3.3 3.3" />
    </>
  ),
} satisfies Record<string, ReactNode>;
export type IconName = keyof typeof ICONS;

export function Icon({ name, size = 14, className }: { name: IconName; size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" data-icon={name} className={className}>
      {ICONS[name]}
    </svg>
  );
}
