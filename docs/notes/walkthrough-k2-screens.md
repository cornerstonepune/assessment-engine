# Walkthrough: the K2 educator and curriculum screens

For the head and the coordinator, who can open these screens on the live site before educators can. Every
address below starts with `https://cornerstone-assessment.vercel.app`. Sign in as usual first.

**How the preview works.** Educators cannot see any of this yet: their switch is off. You can, because your role is a
preview role. You hold no class, so where a screen needs a class it lets you **choose one**. You can choose any class
whose timetable is in force that day. In the preview **nothing you do on the timetable or materials screens is saved**.
Lists are worked out fresh each time you open them, and the buttons that would change a list are hidden. On the
curriculum screens, your answers (Keep, Edit, Send back, Yes, No) **are** saved: that review is how the pages get filled
before educators see them. If a screen is empty, it says why in one line. That line is the honest state, not a fault.

## The educator's day

| Address | What to do | What you should see |
|---|---|---|
| `/educator` | Choose a class at the top | **Today**: the class's day, period by period, with times. Use Previous day and Next day to move. A school holiday says "Holiday". A day the school has not decided yet shows only the timetable's fixed periods. |
| `/educator/week` | Same class | **This week** as a calendar. Tap any period to open it. Previous and Next week move by a week. |
| Tap a period | — | **One period**: what it is, the school's words for it, and the planner's lines for this subject this fortnight. If the planner names an activity, an **Open the activity** button appears. If not, it says no activity is named for this period. |

## An activity's page

`/educator/activity/<activity code>`, opened from a period or from the materials list.

- You see the activity as the school wrote it, its levels 0 to 3, and its materials.
- Each part is marked with whose words it is:
  - "The school's words": the school's own text.
  - "Drafted, check me": a draft waiting for a person.
  - "Kept by a person".
- On a drafted part, use **Keep**, **Edit** (type your own words; Save puts them in its place) or **Send back** (empties it).
- A part nobody has written says "Not written yet."
- **Expect many empty parts today.** Drafts appear only once drafts have been made for that activity.

## Materials

| Address | What you should see |
|---|---|
| `/educator/materials` | **Class list**: what the chosen class needs for a day, a week or a fortnight, built from the activities in the plan. In the preview it is for looking only: no quantity changes, removals or additions. "Nothing in the plan needs materials in these days" is a true empty. |
| `/educator/materials/school` | **School list**: every class's needs for the month, each item once, with the classes it comes from. In the preview it is worked out and not kept, so it is never sent to anyone. |
| `/educator/materials/review` | **Notes to read**: notes the system could not read for sure, oldest first. "No note is waiting" is normal until educators send notes. In the preview it may instead say "Notes are read by the coordinator." Notes cannot be acted on until the switch is on. |

## The curriculum (where you fill and check what educators will see)

| Address | What to do and see |
|---|---|
| `/curriculum/browse` | Every K2 activity by section, with how much of each page is filled. Open a section, or search by name or number. "No K2 activities are loaded yet" means the school's list has not been loaded. |
| `/curriculum/fill` | For each part of a page: how many activities hold the school's words, a draft waiting, a person's words, or nothing. Click an activity to see every part and who wrote it. |
| `/curriculum/fill/walk` | **Check the drafted parts**, one at a time, the most doubtful first. Keep, change or send each back, or Skip. "Nothing is waiting for a check" means no drafts exist yet. |
| `/curriculum/offers` | **Skills offered**: skills the system suggests linking to an activity. Yes adds the link; No closes the offer. "No skills are waiting for you" is normal until suggestions are made. |

## Children (K2), staff only

| Address | What you should see |
|---|---|
| `/k2` | A list of classes to open (you hold none, so every class with a timetable in force today). If none: "No K2 class is yours, and none has a timetable in force today." |
| `/k2/<class>` | The **class picture**: children by Sr. No. against the skills anyone was seen on. A dash means **not seen yet**, never "not secure". Until notes or forms are confirmed: "No child in this class has been seen on a skill yet." |
| `/k2/<class>/<Sr. No.>` | One child: where they are on each skill, what is ready next, and how they have moved over the months. |

## Timetable rules

`/timetable/rules` (in the menu as **Timetable rules**): period times, blocked days, fixed slots and subject limits.
Each rule is a row, with who changed it. Any staff member can change a rule, and changes here **are** saved. If no
timetable is loaded yet it says so.

## Not built or not on yet

- **Educators see none of these screens** until the switch is turned on (you decide when).
- **No reminders are sent** in the preview, and the school's materials list is never sent to the inventory person.
- **No parent screen** shows the K2 picture: it is staff only.
- **Activity pages fill as the curriculum review is done.** Until then most parts read "Not written yet."
