import {
  ArrowBigDown,
  ArrowBigUp,
  ArrowRight,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Coffee,
  Lock,
  AudioLines,
  Bandage,
  Blocks,
  CalendarClock,
  CalendarDays,
  CalendarRange,
  CalendarX,
  Check,
  Circle,
  CircleCheck,
  ClipboardList,
  Clock,
  Ear,
  Equal,
  Eraser,
  Funnel,
  GraduationCap,
  Hand,
  Hourglass,
  House,
  Leaf,
  ListChecks,
  type LucideIcon,
  Mic,
  PenLine,
  Play,
  Puzzle,
  RefreshCw,
  Search,
  SendHorizontal,
  Sparkles,
  Sprout,
  Square,
  SquareDashed,
  StickyNote,
  Sun,
  Target,
  TreeDeciduous,
  TriangleAlert,
  Undo2,
  UserCog,
  UserRound,
  UserX,
  UsersRound,
  X,
} from "lucide-react";

// Every icon the site's K2 screens and its status chip draw, behind this one lookup (task M1-04). One open-source set,
// Lucide (lucide-react, ISC licence: apps/web/node_modules/lucide-react/LICENSE), chosen with the school's designer on
// 3 Nov 2026; one icon per concept, drawn in currentColor, and always shown with its colour and one word, never alone.
// Look-alikes differ in shape as well as colour: done is a round tick, confirm a plain tick, secure a tree; to confirm a
// clock, late an hourglass; absent a crossed person, not enough a dashed square, not willing a hand; fix this the one
// red triangle, an incident a bandage. Swapping the set is this file.
export const ICONS = {
  // a mark a note gives a child (below is never red; not seen is never red)
  above: ArrowBigUp,
  below: ArrowBigDown,
  "as-expected": Equal,
  "not-willing": Hand,
  absent: UserX,
  // the state of a piece of work
  done: CircleCheck,
  "to-confirm": Clock,
  "fix-this": TriangleAlert,
  "to-do": Circle,
  late: Hourglass,
  unplanned: CalendarX,
  // a child's growth on a skill (the class picture, M1-03)
  secure: TreeDeciduous,
  practising: Leaf,
  emerging: Sprout,
  "re-check": RefreshCw,
  "not-enough": SquareDashed,
  // actions
  record: Mic,
  stop: Square,
  send: SendHorizontal,
  play: Play,
  confirm: Check,
  correct: PenLine,
  search: Search,
  filter: Funnel,
  next: ArrowRight,
  clear: Eraser,
  form: ClipboardList,
  "send-back": Undo2,
  no: X,
  // where a piece of text came from
  "from-school": BookOpen,
  "from-draft": Sparkles,
  "from-person": PenLine,
  // things
  child: UserRound,
  class: UsersRound,
  activity: Blocks,
  skill: Puzzle,
  objective: Target,
  note: StickyNote,
  audio: AudioLines,
  heard: Ear,
  incident: Bandage,
  parent: House,
  educator: GraduationCap,
  coordinator: UserCog,
  today: Sun,
  week: CalendarDays,
  fortnight: CalendarRange,
  checklist: ListChecks,
  // the K2 educator's timetable (M1-09)
  "school-words": BookOpen,
  previous: ChevronLeft,
  following: ChevronRight,
  break: Coffee,
  frozen: Lock,
  time: CalendarClock,
} satisfies Record<string, LucideIcon>;
export type IconName = keyof typeof ICONS;

/** The sizes the design names: 16 in a table, 20 in a row or a button, 24 in a heading. */
export const ICON_SIZE = { table: 16, row: 20, heading: 24 } as const;

/** A child's mark (the engine's words for it) → its icon. */
export const MARK_ICON = { above: "above", below: "below", not_willing: "not-willing", absent: "absent", as_expected: "as-expected", clear: "clear" } as const satisfies Record<string, IconName>;

export function Icon({ name, size = ICON_SIZE.row, className }: { name: IconName; size?: number; className?: string }) {
  const Drawn = ICONS[name];
  return <Drawn size={size} strokeWidth={1.9} aria-hidden="true" data-icon={name} className={className} />;
}
