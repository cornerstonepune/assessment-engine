-- The topic is no longer the switch (goals/t1-topics-are-operations.yaml, ADR 0076). Migration 20261113090000 moved
-- every word "taught" onto the skills — the school's onto `skill_set.taught`, each class's into `class_skill` — and
-- left the old places standing only for the website still live until its own commit was. That website is gone, and
-- nothing reads or writes them now: the topic's own switch, each class's word on a topic, and the one-time move.
-- They go, so no code can read a word nothing writes any more.
--
-- Written to run twice.

drop function if exists internal.topic_words_to_skills();
drop table if exists class_topic;
alter table topic drop constraint if exists topic_taught_by_a_person;
alter table topic drop column if exists taught;
alter table topic drop column if exists taught_by;
alter table topic drop column if exists taught_at;

select internal.apply_conventions();
