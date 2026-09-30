-- G3 roll 5 is a Grade 3 child (goals/s27-a-child-in-their-own-grade.yaml). Nimish, 2026-09-30: "G3 roll 5 should be
-- band G3, fix it". The class list put them in class G3 with band G4 (`engine week roster`, the only writer of a child's
-- band), so their parent report said "Grade 4" and their papers were drawn from Grade 4's levels. This moves that one
-- child, and only while they still say G4. The class list file, kept outside the repository because it holds names,
-- needs the same correction: loaded unchanged it puts G4 back, and the load now says so.
update child set band = 'G3', updated_at = now()
 where section = 'G3' and roll_no = '5' and band = 'G4';
