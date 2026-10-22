-- The school's word is "regroup" (goals/ux9b-regroup.yaml). Nimish, 2026-10-22: "carry", "carrying" and "borrow" become
-- "regroup" and "regrouping" wherever a person reads them for a column that passes ten. The seed carries the new words,
-- and the loader writes them over the old for every table but two, which this does:
--   skill_set: the loader never overwrites a skill (`on conflict do nothing`: its words are approved on the site), so
--     each level's words and each objective the seed changed are replaced here, and only where they are still the
--     seed's old words: a level an educator has reworded since is left as they wrote it. The trigger of B1 keeps
--     `skill_level` equal and files the old words as a version.
--   report_item: its title is part of its key, so a new title would be a second row beside the old; the old is renamed.
-- Mistake codes (M_…) and every other code stay as they are. Written to run twice.

update skill_set set difficulty = jsonb_set(difficulty, '{Hard,words}', to_jsonb('Regrouping and a 3-digit answer, a zero only in the answer, the largest regrouping: 56 × 3, 18 × 6, 48 × 5, 99 × 9. Each in a line, partitioned, in a grid, in expanded columns and in columns.'::text))
  where code = 'MUL.2D1D' and difficulty -> 'Hard' ->> 'words' = 'Regrouping and a 3-digit answer, a zero only in the answer, the largest carry: 56 × 3, 18 × 6, 48 × 5, 99 × 9. Each in a line, partitioned, in a grid, in expanded columns and in columns.';
update skill_set set difficulty = jsonb_set(difficulty, '{Easy,words}', to_jsonb('No regrouping, a zero in the middle that no regrouping reaches: 213 × 3, 434 × 2, 302 × 3. Each in a line, the 1-digit number first too, in expanded columns and in columns.'::text))
  where code = 'MUL.3D1D' and difficulty -> 'Easy' ->> 'words' = 'No regrouping, a zero in the middle that no carry reaches: 213 × 3, 434 × 2, 302 × 3. Each in a line, the 1-digit number first too, in expanded columns and in columns.';
update skill_set set difficulty = jsonb_set(difficulty, '{Hard,words}', to_jsonb('Regrouping in any column, a regrouping onto a zero, an answer full of zeros: 357 × 4, 194 × 6, 506 × 7, 125 × 8. Each in a line, the 1-digit number first too, in expanded columns and in columns.'::text))
  where code = 'MUL.3D1D' and difficulty -> 'Hard' ->> 'words' = 'Regrouping in any column, a carry onto a zero, an answer full of zeros: 357 × 4, 194 × 6, 506 × 7, 125 × 8. Each in a line, the 1-digit number first too, in expanded columns and in columns.';
update skill_set set difficulty = jsonb_set(difficulty, '{Advance,words}', to_jsonb('The hardest sums with a missing digit in the 3-digit number and a regrouping onto a zero found lost: 3□4 × 2 = 708, 506 × 7 = 3502 found wrong.'::text))
  where code = 'MUL.3D1D' and difficulty -> 'Advance' ->> 'words' = 'The hardest sums with a missing digit in the 3-digit number and a carry onto a zero found lost: 3□4 × 2 = 708, 506 × 7 = 3502 found wrong.';
update skill_set set difficulty = jsonb_set(difficulty, '{Hard,words}', to_jsonb('A row regrouping, and regrouping when adding the rows: 36 × 24, 47 × 23, 52 × 34, 19 × 14, 68 × 17. Each in a line, in a grid, by long multiplication and in a lattice.'::text))
  where code = 'MUL.2D2D' and difficulty -> 'Hard' ->> 'words' = 'A row regrouping, and adding the rows carrying: 36 × 24, 47 × 23, 52 × 34, 19 × 14, 68 × 17. Each in a line, in a grid, by long multiplication and in a lattice.';
update skill_set set difficulty = jsonb_set(difficulty, '{Easy,words}', to_jsonb('A 2-digit addition with a forgotten regrouping, a regrouping in the wrong column, or numbers lined up from the left.'::text))
  where code = 'REASON.FIND_MISTAKE' and difficulty -> 'Easy' ->> 'words' = 'A 2-digit addition with a forgotten carry, a carry in the wrong column, or numbers lined up from the left.';
update skill_set set difficulty = jsonb_set(difficulty, '{Hard,words}', to_jsonb('A 3-digit calculation: an exchange across a zero done wrong, an exchange from the wrong column, a regrouping of 1 where 2 is needed, the final regrouping dropped.'::text))
  where code = 'REASON.FIND_MISTAKE' and difficulty -> 'Hard' ->> 'words' = 'A 3-digit calculation: an exchange across a zero done wrong, an exchange from the wrong column, a carry of 1 where 2 is needed, the final carry dropped.';
update skill_set set learning_objective = 'Finds missing digits in an addition or subtraction by reasoning across the columns, including the regrouping or the exchange.'
  where code = 'MISSING.DIGIT' and learning_objective = 'Finds missing digits in an addition or subtraction by reasoning across the columns, including the carry or the exchange.';
update skill_set set difficulty = jsonb_set(difficulty, '{Easy,words}', to_jsonb('One missing digit where no regrouping or exchange reaches it: 2□ + 34 = 59, 5□ − 23 = 34.'::text))
  where code = 'MISSING.DIGIT' and difficulty -> 'Easy' ->> 'words' = 'One missing digit where no carry or exchange reaches it: 2□ + 34 = 59, 5□ − 23 = 34.';
update skill_set set difficulty = jsonb_set(difficulty, '{Medium,words}', to_jsonb('One missing digit across a regrouping or an exchange, in either number or in the answer: 4□ + 38 = 85, 64 − 2□ = 37, 37 + 46 = 8□.'::text))
  where code = 'MISSING.DIGIT' and difficulty -> 'Medium' ->> 'words' = 'One missing digit across a carry or an exchange, in either number or in the answer: 4□ + 38 = 85, 64 − 2□ = 37, 37 + 46 = 8□.';
update skill_set set difficulty = jsonb_set(difficulty, '{Easy,words}', to_jsonb('No regrouping, in columns and in a line, either number first, adding zero too: 43 + 5, 5 + 43, 45 + 0.'::text))
  where code = 'ADD.2D1D' and difficulty -> 'Easy' ->> 'words' = 'No carry, in columns and in a line, either number first, adding zero too: 43 + 5, 5 + 43, 45 + 0.';
update skill_set set difficulty = jsonb_set(difficulty, '{Medium,words}', to_jsonb('A regrouping into the tens, the answer stays 2 digits: 47 + 6.'::text))
  where code = 'ADD.2D1D' and difficulty -> 'Medium' ->> 'words' = 'A carry into the tens, the answer stays 2 digits: 47 + 6.';
update skill_set set difficulty = jsonb_set(difficulty, '{Hard,words}', to_jsonb('The regrouping makes a 3-digit answer: 96 + 8.'::text))
  where code = 'ADD.2D1D' and difficulty -> 'Hard' ->> 'words' = 'The carry makes a 3-digit answer: 96 + 8.';
update skill_set set learning_objective = 'Adds two 2-digit numbers in columns and in a line, regrouping exactly when a column needs it.'
  where code = 'ADD.2D2D' and learning_objective = 'Adds two 2-digit numbers in columns and in a line, carrying exactly when a column needs it.';
update skill_set set difficulty = jsonb_set(difficulty, '{Easy,words}', to_jsonb('No regrouping, in columns and in a line: 23 + 45.'::text))
  where code = 'ADD.2D2D' and difficulty -> 'Easy' ->> 'words' = 'No carry, in columns and in a line: 23 + 45.';
update skill_set set difficulty = jsonb_set(difficulty, '{Medium,words}', to_jsonb('A regrouping from the ones only: 27 + 36.'::text))
  where code = 'ADD.2D2D' and difficulty -> 'Medium' ->> 'words' = 'A carry from the ones only: 27 + 36.';
update skill_set set difficulty = jsonb_set(difficulty, '{Hard,words}', to_jsonb('A regrouping from the tens, or from both columns, so the answer passes 100: 61 + 42, 68 + 47.'::text))
  where code = 'ADD.2D2D' and difficulty -> 'Hard' ->> 'words' = 'A carry from the tens, or from both columns, so the answer passes 100: 61 + 42, 68 + 47.';
update skill_set set difficulty = jsonb_set(difficulty, '{Easy,words}', to_jsonb('No regrouping, either number first: 342 + 5, 5 + 342.'::text))
  where code = 'ADD.3D1D' and difficulty -> 'Easy' ->> 'words' = 'No carry, either number first: 342 + 5, 5 + 342.';
update skill_set set difficulty = jsonb_set(difficulty, '{Medium,words}', to_jsonb('A regrouping from the ones only: 347 + 6.'::text))
  where code = 'ADD.3D1D' and difficulty -> 'Medium' ->> 'words' = 'A carry from the ones only: 347 + 6.';
update skill_set set difficulty = jsonb_set(difficulty, '{Hard,words}', to_jsonb('The regrouping ripples one more place, or through the 9s to a new digit: 399 + 4, 999 + 7.'::text))
  where code = 'ADD.3D1D' and difficulty -> 'Hard' ->> 'words' = 'The carry ripples one more place, or through the 9s to a new digit: 399 + 4, 999 + 7.';
update skill_set set difficulty = jsonb_set(difficulty, '{Easy,words}', to_jsonb('No regrouping, either number first: 345 + 23, 23 + 345.'::text))
  where code = 'ADD.3D2D' and difficulty -> 'Easy' ->> 'words' = 'No carry, either number first: 345 + 23, 23 + 345.';
update skill_set set difficulty = jsonb_set(difficulty, '{Medium,words}', to_jsonb('One regrouping, from the ones or from the tens: 347 + 25, 372 + 64.'::text))
  where code = 'ADD.3D2D' and difficulty -> 'Medium' ->> 'words' = 'One carry, from the ones or from the tens: 347 + 25, 372 + 64.';
update skill_set set difficulty = jsonb_set(difficulty, '{Hard,words}', to_jsonb('Regrouping from both columns, or a 4-digit answer: 368 + 57, 965 + 78.'::text))
  where code = 'ADD.3D2D' and difficulty -> 'Hard' ->> 'words' = 'Carries from both columns, or a 4-digit answer: 368 + 57, 965 + 78.';
update skill_set set learning_objective = 'Adds two 3-digit numbers, regrouping from any column, including onto a zero.'
  where code = 'ADD.3D3D' and learning_objective = 'Adds two 3-digit numbers, carrying from any column, including onto a zero.';
update skill_set set difficulty = jsonb_set(difficulty, '{Easy,words}', to_jsonb('No regrouping, in columns and in a line: 243 + 514.'::text))
  where code = 'ADD.3D3D' and difficulty -> 'Easy' ->> 'words' = 'No carry, in columns and in a line: 243 + 514.';
update skill_set set difficulty = jsonb_set(difficulty, '{Medium,words}', to_jsonb('One regrouping — from the ones, the tens or the hundreds — or an inside zero: 247 + 315, 405 + 302.'::text))
  where code = 'ADD.3D3D' and difficulty -> 'Medium' ->> 'words' = 'One carry — from the ones, the tens or the hundreds — or an inside zero: 247 + 315, 405 + 302.';
update skill_set set difficulty = jsonb_set(difficulty, '{Hard,words}', to_jsonb('Two or three regroupings, a regrouping onto a zero, or zeros kept in the answer: 678 + 457, 395 + 205.'::text))
  where code = 'ADD.3D3D' and difficulty -> 'Hard' ->> 'words' = 'Two or three carries, a carry onto a zero, or zeros kept in the answer: 678 + 457, 395 + 205.';
update skill_set set learning_objective = 'Adds three or more numbers lined up by the ones, where a column can regroup 2 or more.'
  where code = 'ADD.MANY' and learning_objective = 'Adds three or more numbers lined up by the ones, where a column can carry 2 or more.';
update skill_set set difficulty = jsonb_set(difficulty, '{Easy,words}', to_jsonb('Three 2-digit numbers, no regrouping: 21 + 34 + 12.'::text))
  where code = 'ADD.MANY' and difficulty -> 'Easy' ->> 'words' = 'Three 2-digit numbers, no carry: 21 + 34 + 12.';
update skill_set set difficulty = jsonb_set(difficulty, '{Medium,words}', to_jsonb('Three numbers with a regrouping, or of different lengths: 8 + 7 + 9, 45 + 7 + 123.'::text))
  where code = 'ADD.MANY' and difficulty -> 'Medium' ->> 'words' = 'Three numbers with a carry, or of different lengths: 8 + 7 + 9, 45 + 7 + 123.';
update skill_set set difficulty = jsonb_set(difficulty, '{Hard,words}', to_jsonb('Three 3-digit or 4-digit numbers, four or more numbers, or a column that regroups 2: 256 + 348 + 179.'::text))
  where code = 'ADD.MANY' and difficulty -> 'Hard' ->> 'words' = 'Three 3-digit or 4-digit numbers, four or more numbers, or a column that carries 2: 256 + 348 + 179.';
update skill_set set learning_objective = 'Adds a 4-digit number and another, in columns and in a line, whatever the regrouping.'
  where code = 'ADD.4D' and learning_objective = 'Adds a 4-digit number and another, in columns and in a line, whatever the carries.';
update skill_set set difficulty = jsonb_set(difficulty, '{Hard,words}', to_jsonb('A regrouping that ripples through 9s, a 5-digit answer, or several zeros: 4999 + 6, 7865 + 4378.'::text))
  where code = 'ADD.4D' and difficulty -> 'Hard' ->> 'words' = 'A carry that ripples through 9s, a 5-digit answer, or several zeros: 4999 + 6, 7865 + 4378.';

update report_item r set title = 'Concept of 2 digits Addition with regrouping' where title = 'Concept of 2 digits Addition with carrying'
  and not exists (select 1 from report_item n where n.tenant_id = r.tenant_id and n.skill_code = r.skill_code and n.band = r.band and n.title = 'Concept of 2 digits Addition with regrouping');
delete from report_item where title = 'Concept of 2 digits Addition with carrying';
update report_item r set title = 'Concept of 2 digits Subtraction with regrouping' where title = 'Concept of 2 digits Subtraction with borrowing'
  and not exists (select 1 from report_item n where n.tenant_id = r.tenant_id and n.skill_code = r.skill_code and n.band = r.band and n.title = 'Concept of 2 digits Subtraction with regrouping');
delete from report_item where title = 'Concept of 2 digits Subtraction with borrowing';
update report_item r set title = 'Concept of 2 digits Subtraction without regrouping' where title = 'Concept of 2 digits Subtraction without borrowing'
  and not exists (select 1 from report_item n where n.tenant_id = r.tenant_id and n.skill_code = r.skill_code and n.band = r.band and n.title = 'Concept of 2 digits Subtraction without regrouping');
delete from report_item where title = 'Concept of 2 digits Subtraction without borrowing';
update report_item r set title = 'Concept of 3 digits addition with regrouping' where title = 'Concept of 3 digits addition with carrying'
  and not exists (select 1 from report_item n where n.tenant_id = r.tenant_id and n.skill_code = r.skill_code and n.band = r.band and n.title = 'Concept of 3 digits addition with regrouping');
delete from report_item where title = 'Concept of 3 digits addition with carrying';
