# ADR 0042 — A photographed page is lined up by its own print, tile by tile

**Status:** accepted (built on Nimish's go-ahead of 2026-09-28, "yes re-read 24 sep and do the corner fix"; the corner
squares themselves were ruled out on the photographs, see Rejected)
Goal: goals/s23-a-curled-photo-lines-up.yaml

## What happened

Nimish asked why R31-H02 on the 24 Sep scan was barely read: "its in proper boxes and qr and all". Copies 01 and 02 had
been read as old papers, none of their 24 answers in their boxes. The box reader lined a photograph up with one
straight map (a homography) from ORB features, RANSAC at 0.74 mm, and refused any page with fewer than 60 matched
features. On those two photographs it matched 37 and 40.

Measured on the 46 photographed pages of 23 and 24 Sep, with the photographs as the engine reads them:

- A phone photograph of a page on a desk is seen at an angle and curls where the paper lifts. On 24 Sep copy 09, the
  best straight map left the bottom row of answers 5 to 6 mm off, and a run of boxes can be looked for only 3 mm
  around where a map puts it, because its boxes repeat every 8.4 mm. Searched further, a run locks one box off (7.9 mm
  on copy 01).
- The count of matched features does not say how well a page lines up. On 23 Sep page 14, 99 features matched and
  answers were left 7 mm off. On 24 Sep copy 02, 40 matched and every answer was within 3.2 mm.
- ORB and SIFT each failed on pages the other lined up. ORB's 37 matches on copy 01 left its lower half 3 to 7 mm off.
  SIFT's matches on 23 Sep's first pages collapsed onto a single point: many photographed features matched one
  printed feature.

## Decision

A page is lined up by its own print (`w3_read/lineup.py`, step N8), in three moves:

1. **A first map from features, two ways.** ORB at 2000 px and SIFT at 1000 px, each printed feature matched once
   both ways. Kept is whichever first map lets more of the printed page's print be found.
2. **A better straight map from the tiles.** The printed page is cut into 24 mm tiles, overlapping by half. Each tile
   holding print is looked for within 8 mm of where the first map puts it. A tile is found where it matches with a
   normalised correlation of at least 0.3, and at least 0.08 better than anywhere 2 mm or more away, so a tile of
   repeated boxes is not found. The found tiles give a better straight map.
3. **A smooth field for the curl.** What that map leaves is measured again at every tile. Tiles that the tiles
   around them do not bear out (by more than 3 mm) are dropped. A smooth field through the rest (Gaussian, 12 mm)
   carries the photograph the rest of the way. The photograph is drawn into the printed frame through both at once.
   The same map sends any point of the frame back to the photograph (`to_photo`), so the approval screen crops
   where the reading came from.

A page on which less than half of its tiles with print are found does not line up, and is read as an old paper as
before.

Each answer is then found around its own printed question (`lineup.settle`):

- first the run with 10 mm of the printed page around it, looked for within 6 mm. A crease moves one question on its
  own, and the words above the boxes say which run is this one, where boxes alone repeat;
- then its own boxes settle it, within 1 mm. Given 3 mm, the boxes alone wandered: a child's large digits outweigh a
  box's thin lines, and on a lifted test page they settled 3 mm off where the question's print had put them;
- where the question's print says nothing sure, the boxes alone are looked for within 3 mm, as before.

An answer found neither way (its boxes matching under 0.15; on the real pages, lined up, never under 0.21) is not
read at a guessed place. It goes to a person as the reader's existing `not_found`, and Marking shows the whole page.

## Measured

On the 46 photographed pages of 23 and 24 Sep:

- **Every page lines up and every answer is found: 324 of 324.** Before, 2 pages of 24 Sep were refused, and the 23 Sep
  pages that lined up left answers up to 7 mm off.
- **Placement.** After the field, the per-answer step moves a run by 0.1 mm at the median, 1.3 mm at the 99th
  percentile and 2.9 mm at most.
- **The layout each 23 Sep copy was printed in (ADR 0040)** is still the one chosen, by a clear margin.
- **On the test suite's synthetic bent pages, against the known bend,** the corner of a run lands a median 0.98 px from
  where it truly is (1.23 before) and at most 2.2 px (3.4 before).
- **Memory.** One line-up takes 234 MB more at its peak than before (33 MB), most of it SIFT, which works on a copy
  doubled in size. At 2000 px SIFT took 715 MB, so it runs at 1000. Without SIFT, one 23 Sep page does not line up.

## Rejected

- **The four printed corner squares.** Proposed on 28 Sep and ruled out on the photographs themselves: the phone's scan
  app cut the top two off both failing copies, as `boxes.py` had recorded for the whole 24 Sep file. Where all four
  survive, the tiles find them too.
- **A lower feature count.** Letting copies 01 and 02 through at 37 or 40 matches keeps the one straight map. That map
  leaves copy 01's lower half 3 to 7 mm off, and those answers would be read in the wrong place.
- **One straight map with a looser fit.** It spreads the error over the page, but a lifted page is not straight: its
  answers stay 3 to 4 mm off.
- **SIFT at the photograph's own size.** It adds 715 MB on a server of 1.9 GB whose engine the kernel has killed for
  memory before.

## Consequences

- **What a doubt of the real reader is held to.** `test_boxes`' real-reader test held a doubt's guess to be what was
  written. But the reader reads the same crop differently when it moves by under a pixel. On one bent test page it read
  "663" as "63" where the crop was cut, and as "663" at seven of the eight one-pixel shifts around it. On the 141
  answers of 24 Sep with a gold, this line-up moved 19 outcomes: 7 up, 5 down, 6 sideways, and one wrong answer
  (1747 read 174) is no longer stood behind. So a doubt is now held to what the pipeline decides: every digit written
  reached the reader, checked by a shape reader on the very crop it was handed. Nothing it stands behind may be wrong,
  as before.
- **A vote over one-pixel shifts, not adopted here.** Measured on 24 Sep's doubts, where an answer's reading does not
  fit its inked boxes: it put the right guess on 6 more and turned one right guess wrong (1747 → 174, where the ink
  count was short). It is the reader's policy, and step 3's to decide behind its gate.
- Reading a page takes about 1 to 2 s longer (measured here on 4 CPUs, median 1.3 s a page for the line-up and every
  answer's placement).
- `boxes.py` keeps what is in a box; `lineup.py` keeps where it is. `blank`, `PPM`, `SEEK` and `PRINTED` moved with it.
- The goal's live scenario closes on the re-read of the 24 Sep file.
