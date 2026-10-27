# res_results_by_topic: Results read by topic

Nimish, 24 Oct 2026 (his words are in `goals/res_results_by_topic.yaml`). Goal: `bin/engine done res_results_by_topic`.
W3 (the educator's site over the graph, N10); no gate moved. Website only: no migration, no engine change. Built on PR #342
(the one rule for who sees what, `staff_sees`), which was not on main when this started.

## What was built

- **Class results** (`/growth`): one class at a time, chosen in the page's own filter row (required: no "every class", no ×),
  opening on the educator's own class. Topics as rows, grouped by subject, folded; each counts the class's children as
  secure, practising, needs help, too few answers, not assessed yet (each a number in its row's words, beside a thin bar) and
  says when it was last assessed. `?topic=` opens a topic: its papers by kind (class assessment, home assessments and for how
  many children, practice) and its skills, each with how many children are at each level. `?skill=` opens a skill's children,
  ten a page (`kp=`), those who need the educator first: level, state, answers in three signals, last assessed, and "N answers
  waiting to be checked: results may change" linking to the child's own list. A class outside `reachOf` is refused in words.
- **A child's page** (`/growth/[id]`): "What their answers show" is now a table, a row per topic: level, last paper's answers
  (right of attempted; wrong, wrong with working, blank apart), state chip, "Weakest: … / Strongest: …" worked out by code
  (`topicNote`, lib/profile.ts) with the repeating mistake's name from `repeatedMistakes`. `?topic=` opens its skills (each
  still opening to the answers behind it, `SkillLine`) and its papers; "See the child’s page" opens the written pages in
  place (`/api/scan/[capture]/[page]`, the route Check answers and the child page already use). Other panels unchanged.
- **Numbers**: `lib/queries-results.ts`. States are `child_skill_state` (signed-off answers only); a group takes its weakest
  skill by `child_state.severity` (as `childTable` does); signals from `answer_placed` on readings not replaced, as `skillMap`
  counts them; a child's level is the level of the newest question they answered (`item.difficulty`, ordered by the
  `difficulty` rows). Topics and skills: `skill.topic_code`, taught per class (`skill_taught_in`), as `childSkills` reads them.
- **Who sees it**: classes by `reachOf`/`workScope`; a topic's subject by `staff_sees` (`seesClassIn`, new in lib/reach.ts, no
  rule of its own); papers and answers waiting by `seesSheet`.
- **Speed**: the child page built every mistake's name for every operation on each load (250–420 ms); it now names only the
  mistakes the child's own answers carry (`misconceptionNames(child)`).

## What each old thing became

| Old | Now |
|---|---|
| `/growth`: the classes side by side, the children who need you, Grade/Class/Status filters, sorting | kept whole at `/growth?view=children` ("Every child, one by one →" under the topics); an old address with `sort`, `status`, `grade`, `page` or `cpage` still opens it |
| `/growth?class=X` | the topics of class X |
| `/growth/class/[section]` (each child against each topic, checks that would place them) | unchanged; linked as "Each child against each topic →" |
| Child page "What their answers show", topic groups that unfold to skills | the same panel, a table row per topic; a topic opens to the same skill lines and its papers |
| Child page "N to check · N to sign off ↓" | "N answers waiting to be checked: results may change" to the same list |

## Chosen by default (nobody was asked)

- **Level** is the level of the newest question the child answered (ties: the harder), on a skill or in a topic; not the
  level the next paper proposes (`next_difficulty`).
- **A topic's state** for a child is their weakest skill's in it, as a skill set already took its weakest skill. "Too few
  answers" (grey) is its own count, beside "not assessed yet" (no checked answer at all).
- **"Waiting to be checked"** counts a child's answers not yet signed off on papers the person sees (both those for a person
  to read and those to sign off): the list on the child's page, which is where the link goes.
- **Weakest/strongest**: the weakest skill that needs work (most severe state, then least often right), with its repeating
  mistake where there is one; else the skill most often right of those with enough answers; else "Too few answers yet to say".
- The heat map (children as rows) is not built (later, by Nimish's word); the old children view stays until it is.
- gstack could not be installed (the permission layer refused the clone); pages were looked at through Playwright.

## Verified

(filled at the end of the session)

## Handoff

(filled at the end of the session)
