import type { MenuItem } from "@/components/educator/shell-nav";
import { EDUCATOR_MENU } from "./educator/menu";

// The menu of the K2 pictures (M1-17) in the school's shell: the educator's own menu, with the children's pictures first.
// Added here, not to lib/educator/menu.ts, which is the timetable's.
export const K2_MENU: MenuItem[] = [{ key: "children", label: "Children", icon: "class", path: "/k2", also: ["/k2/"] }, ...EDUCATOR_MENU];
