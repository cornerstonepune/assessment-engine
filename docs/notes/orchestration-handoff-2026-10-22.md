# Orchestration handoff, 22 Oct 2026 (end of the first orchestration session)

For the next orchestration session. Read this, then `CLAUDE.md`, the top section of `BUILD-ORDER.md` (the scope Nimish
locked on 22 Oct), and the flow map (Claude Doc https://claude.ai/artifact/3KjG5SbE5bLBQgcLCYDPu8, last sections:
"Decided, 22 Oct", "Scope to lock", "UX rules and the educator's week").

## Who and how
- Nimish: non-technical founder, decides scope and merges every PR. Plain English, short, no jargon, no file paths unless
  asked. His standing preferences: challenge him, do not just agree; flag uncertainty; never invent sources or numbers;
  explain simply. He is token-conscious: **no full answer dumps, no long messages, one clear ask at a time.**
- You orchestrate; children do the work. **Never merge, deploy, force-push or skip the commit hooks.** No secrets,
  children's names, scans or credentials in git, logs or chat. A password was once typed in chat: treat it as known,
  never use it.
- Start routine sessions on **Sonnet** (`model: claude-sonnet-5-5`); the biggest model only for the hard reader and
  database-core work, and say so when you do.
- Mechanics learned: you cannot message a running remote session (no tool; `SendMessage` finds only local agents). To
  change a session's instructions, **archive it and start a new one with a complete brief**. A GitHub comment on its PR
  may not reach it. A session refuses a claim of Nimish's approval from you; the approval must be in the repo
  (BUILD-ORDER's locked-scope section). Children stall silently asking a question: check `get_session`
  (`post_turn_summary`) and open PRs, not just notifications. Subscribe to PRs you create (`subscribe_pr_activity`).
- The flow map is node `3dd060ae-680b` in project `12cfb573-8473-4402-a5d3-68e35d610cd7` (edit with the docs tools).

## Where things stand (22 Oct, ~14:30 UTC)
Live on the site (https://cornerstone-assessment.vercel.app): upload scans on Assessments (box at the bottom today), the
top bar (Subject, Class, search), Today's five lines, the check screen showing a question's own part of the page (#276),
cleaner Children/Curriculum, red count only on Today (#278), the reader fix for phone photos (#267), a locked scope in
BUILD-ORDER (#269), E0 approval (#280), English Grades 3-4 content merged (#254, #272), Ayush's login created
(admin@cornerstoneschool.in, role educator, no classes yet).

Open PRs (CI green unless noted):
| # | What | Advice to Nimish |
|---|---|---|
| 281 | CK2: each photograph is matched to the printed page it is (pages photographed second-page-first), "Read again" for uploaded files | merge; then press Read again on the 22 Oct Grade 1 file |
| 273 | B4: the rung folded into the skill; rehearsed on a copy of live, evidence checksums identical | merge (migration runs on merge) |
| 275 | S7: coordinator's page across classes | optional, new page, no screenshots yet |
| 274 | S2: assessment card, Made to Results | **hold**: predates the clutter rules; S2b builds on it and replaces it |
| 270 | R2: a page that cannot be lined up goes whole to a person | hold (CK2 may cover it; check) |
| 279 | UXF: shared page blocks + UX rules that fail the build | draft, 2 checks failing, its session is on it |
| 265 | A1: Sign in with Google (removes password login) | **DO NOT MERGE** until Google Cloud is on for cornerstoneschool.in and the OAuth client + Vercel env vars exist; it would lock everyone out |

Running child sessions (check each with `get_session`):
- Core track (Opus) `session_01X7ZrN3DhFF51DmUbxQLbD6`: B4 (#273) then C1-C6, one slice at a time.
- Screens (Opus) `session_01CbaWQmmpwxtTHPCcZfhgTX`: S1 merged, S2 #274, S7 #275; idle.
- S2b (Sonnet) `session_01WnvHYCYchdUSSrMQuPgLqy`: declutter Assessments (upload on top, one count per assessment, filters collapsed), on branch claude/s2b-assessments-declutter.
- UXF (Sonnet) `session_01WGtwctGJockEJ6G6XTNHev`: shared blocks + build-failing UX rules; proof page = Check answers.
- CK2 (Sonnet) `session_011vdmSbvLhLTtCmHsiXnYG7`: #281.
- E0 (Sonnet) `session_01HjU7TKhbqGTc81NcJ1jLHA`: English Grades 3-4 loaded as drafts + Approve/Send back on the Curriculum page, saved under the educator's name. Started 14:30.
- R2 (Opus) `session_01FY3vwSsrCN3xsHuPxGGwcG`: #270. A1 (Opus) `session_01QQ6gpajYQFCSVs3m6WXgdV`: #265, idle.
- Not ours: all `JIN-...` sessions and the Cornerstone website session are other projects.

## Nimish's decisions (22 Oct), all in force
Assessments at every stage from Junior KG, all internal. Full teacher dashboard (mobile ok), no WhatsApp yet. Everyone
edits the curriculum (versions kept; an edit takes effect next week). Validation by rules per subject and kind of
question: a new one shows a person every answer, then Learning, Trusted, Falls back; every number a row. Hindi: teachers
mark, engine only stores sheets. KG assessed by observation on a phone. The system proposes each child's paper; the
educator may change it. A page that cannot be lined up goes whole to a person (never read by its words). One school,
never sold. Bank target 250 per skill and level (class-size rule gives 216; margin). Approval is of a kind of question
(3 samples), code makes and verifies variants. Mixed-skill questions allowed (teacher picks skills + kind; AI drafts
code-checked samples; she edits in chat and approves). Observation engine (voice notes to evidence) is the next build
after this scope; C2 widens the child record to hold it. "Given on": educator presses it; an upload without it still
counts. No chasing/CRM. "Educator", "regroup", Easy/Medium/Hard/Advance. The second reader stays OFF.

## The locked scope and order (BUILD-ORDER top section)
R1 (done) > R1b (re-read the 22 Oct Grade 1 file; waits on #281) > R2 > B4 (#273) > C1 questions name their registry
skills > C2 one evidence record for written + observed + voice + project (past rows untouched) > C3 curriculum versions
stamped on results > C4 validation rules per subject x kind > C5 one approval list (second approval before
parent-facing) > C6 consent/data register > S1-S9 screens > co-author loop (teacher describes a kind by text/voice/photo,
code-checked samples, chat edits, code makes ~250 variants; amend ADR 0006) > English Grades 3-4. Out of scope: WhatsApp,
engine marking of Hindi, observation engine, a workflow engine (adopt Hatchet only when real timers/retries appear),
mastery models, selling to other schools. Schema slices one at a time; screens needing no new table may run beside.

## To do next
1. Tell Nimish to merge #281 then #273; after #281 is live he presses **Read again** on the 22 Oct file (one measure,
   ten lines: copies in order/swapped, answers found of 120, agreement on copies 3, 4, 7, 8).
   Person's key: Q1 8, Q2 18, Q3 6, Q4 12, Q5 12, Q6 6, Q7 4, Q8 10 | Q9 10, Q10 9, Q11 6, Q12 12. PDF page 1s at
   1,3,6,8,9,11,14,16,17,19 and page 2s at 2,4,5,7,10,12,13,15,18,20, so copies 3 (5-6), 4 (7-8), 7 (13-14), 8 (15-16)
   are second-page-first (a hypothesis, not confirmed). Exceptions: pages 7-8 nearly blank (p8 Q3 scribbles = wrong with
   working); p11-12 Q8 "55" wrong; p15-16 Q2 "8 8" wrong/unclear, Q4 "8" wrong, Q5/Q8 two digits in one box; p3-4 a
   curled 6 (a 6); p15 Q10 a 9 like a 7; p20 Q9 "10" with a flagged 1. Nimish is also checking by hand on /capture/check.
2. A staff table of who teaches which class and subject (Ayush: G2 and G3 English; Achal: Maths ...), edited on a Staff
   page, not by commands. Not yet given to any session: brief the core track right after B4. Meanwhile Nimish can run
   `~/cornerstone/assessment-engine/bin/engine staff classes admin@cornerstoneschool.in G2 G3`.
3. After UXF's blocks exist: move pages onto them in the educator's week order: Today, Taught this week, Papers to
   approve, Print and give, Upload papers, Check answers, Class results, A child; then Curriculum, Question bank, School.
   Open questions for Nimish/Achal: is "Taught this week" its own page; are "Papers to approve" and "Print and give"
   one page; is 10 rows the right table limit.
4. Remaining screens: S3 checking (blind spot checks, assistant settles "what is written", 48 h to coordinator), S4
   results + child profile (tab per subject; one-page parent summary approved before print), S5 question bank, S6
   curriculum page (everyone edits, versions), S8 substitute access, S9 KG observation. Plus the "build now" gaps:
   shared approval screen, curriculum snapshot on results, speech-to-text with class roster key terms + safeguarding
   path, interventions library, contested skills, consent register (DPDP; check with a lawyer).
5. Google sign-in: waiting on the school admin to turn on Google Cloud (admin.google.com > Apps > Additional Google
   services > Google Cloud Platform > ON), then OAuth client (Internal, redirect
   https://cornerstone-assessment.vercel.app/login/google/callback), GOOGLE_CLIENT_ID/SECRET in Vercel, and Nimish's own
   @cornerstoneschool.in address for the admin seed. Then merge #265.
6. English facts for the educator to confirm: Sinhagad, dabbawalas, olive ridley turtles, library labels.

## What I got wrong (do not repeat)
Said uploads were live before the deploy; parked five "unreadable" pages that were probably order swaps; let the E0
session stall two hours on a missing approval; sent long, many-part messages that confused Nimish; called a cluttered page
"done". Verify before claiming; one ask per message; show before-and-after screenshots before asking him to merge a screen.

## Costs and cadence
Weekly usage was near its warning line. At most three or four sessions at once, Sonnet by default, one measure not a
loop, summaries not dumps. Release state: check ci, migrate live, deploy engine, Vercel and the "live database" status
on main's newest commit; only the newest merge goes live.
