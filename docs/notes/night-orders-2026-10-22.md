# Night orders, 22 Oct 2026 (Nimish, going to sleep)

Nimish's words, as sent on 22 Oct 2026 evening: "I'm going to sleep, but do not stop development. I think we have a
fair amount of development to do: the entire schema-based C1 to C6, the whole frontend normalization across all
screens. You have to look at every screen from a teacher educator's point of view, make all the necessary things, make
it easy to navigate, and ensure the entire design consistency. You have work for the night. Keep developing and make the
PRs ready in C runs [CI runs] for me to merge in the morning. Do not wait for my approval, but ensure that you are doing
all frontend tests. Operate the dashboard, not on the phone but on the desktop. You teachers are not going to majorly use
this on the phone. They are going to use it on the desktop, right? Open up desktop use and keep checking. Make sure that
the navigation and all the menu items are perfect, the backend is also very well set, and the English system is ready for
approval."

What this means for the work, in force until Nimish says otherwise:

- **Desktop first.** Educators use the website on a desktop. Screens are designed, tested and screenshotted at desktop
  width (1440 px). Phone layout is no longer a gate for any screen. It must not break (no error, no lost action), but no
  slice is held for it, and the phone checks in UX7/S1/S2 are not required of new work. The one exception stays: KG
  observation (S9) is done on a phone, by Nimish's earlier decision.
- **C1 to C6 are approved and ordered** by the locked scope of 22 Oct (BUILD-ORDER's top section). One schema slice at a
  time, each with its goal file first, each rehearsed on a copy of live, each its own draft PR stacked on the one before.
- **Frontend normalization** across all screens, in the educator's week order (docs/ux-rules.md), on the shared blocks
  from #279/#286: one page anatomy, one table, one chip, the same words, a menu that is complete and in the order of the
  educator's week. Each screen is looked at as an educator would use it.
- **Every PR is a draft with CI green** by the morning, with before/after desktop screenshots on an Artifact page and the
  output of `bin/engine done <goal>` pasted. Nobody merges, deploys or force-pushes; Nimish merges.
- **No waiting for approval overnight.** A question that is genuinely his goes in the PR body as "decision needed", and
  the work carries on with the safer default.
- **All frontend tests run** (the whole Playwright suite plus bin/check) before every push; the reason to stop is a red
  CI that cannot be fixed at its cause, reported in the PR.
- **English is ready for the educator's approval** (E0, PR #284), and Ayush can use it: the staff table of who teaches
  which class and subject is edited on a Staff page, not by commands.

## Added later the same evening: the look and feel every subject will inherit

Nimish's words: "for teachers, in most of the places, can we use tables instead of a lot of places where the tags of
subject names and all are never aligned, like on the curriculum page or on the assessments page? Can we use tables more
for easier viewing, and use icons or red, amber, green in places that make it easier for people to navigate? Use
filters wherever possible. Even on the page that we have made, at the top, the class and the subject buttons are too
small, and then there is this massive strip for just typing the student name. These are very simple hacks, simple things
that you need to be consistent with when you're designing the frontend. Make sure that all these elements are
incorporated and the frontend is really easy and nice for teachers to start operating. Because this is going to become
the basis for all the other subjects as well, right? Do it well."

What this means, in force until Nimish says otherwise:

- **A list is a table.** Rows and aligned columns (subject, class, grade, status and the like are columns, never tags
  floating in a line). Fixed, consistent column widths and alignment (text left, numbers right, status centred). The
  Curriculum and Assessments pages are the first to be rebuilt this way.
- **Status is an icon plus a word plus red, amber or green** (never colour alone), the same three everywhere, from one
  block (StatusChip). Red stays rare and means "needs you now".
- **Every table has a filter row** (class, subject, grade, status, week as fits, plus a compact search), built from one
  FilterBar block, in the same place on every page, with the active filters visible and a one-click clear.
- **The top bar**: the Class and Subject selectors are full-size controls (at least 40 px tall, 15 px text, clearly
  clickable, showing the current choice); the student search is a compact field (about 240 px, search icon, grows when
  focused), never a wide strip.
- **Subject-agnostic**: nothing in the shared blocks or the menu names Maths or English; every subject inherits them.
- **Enforced by the build**: the rules (target sizes, table instead of tag lists, filter row on a long list, status
  chip with icon) go into docs/ux-rules.md and the rule tests, like the existing ones, so a page that breaks them fails.
