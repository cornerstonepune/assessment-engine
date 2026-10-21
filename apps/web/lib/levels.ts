import { cache } from "react";
import { sql } from "./db";

export type Levels = { order: string[]; usual: string };

/** The school's levels, easiest first, and the one a paper is at when nothing says otherwise: rows of `difficulty` and
 *  the config row `level.usual`, never names in code (goals/b0c-levels-from-the-table.yaml). Read once a request. */
export const levels = cache(async (): Promise<Levels> => {
  const [r] = await sql<Levels[]>`
    select coalesce((select array_agg(code order by ord) from difficulty), '{}') as "order",
           (select value #>> '{}' from config where key = 'level.usual') as usual`;
  return r;
});
