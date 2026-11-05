import type { MenuItem } from "@/components/educator/shell-nav";
import { E } from "./words";

// The K2 educator's menu (D-075's order): Today, then the timetable (a day, this week, next week). Fortnight, month,
// activities, materials and children come with their screens.
export const EDUCATOR_MENU: MenuItem[] = [
  { key: "today", label: E.today.title, icon: "today", path: "/educator", also: ["/educator/period"] },
  {
    key: "week",
    label: E.nav.timetable,
    icon: "week",
    path: "/educator/week",
    sub: [
      { key: "day", label: E.nav.day, path: "/educator", extra: "tomorrow" },
      { key: "week", label: E.week.title, path: "/educator/week" },
      { key: "next", label: E.weekNav.next, path: "/educator/week", extra: "next" },
    ],
  },
];
