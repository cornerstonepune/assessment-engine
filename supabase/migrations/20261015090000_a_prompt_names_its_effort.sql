-- A prompt row may name how hard its model thinks before it answers (Anthropic's output_config.effort; goals/j5).
-- At its default, claude-sonnet-5 read 21 parent reports for over thirty minutes (engine eval, 2026-09-28). Null is
-- the model's own default; Haiku 4.5 takes no effort at all, and the seed's test keeps it from being given one.
alter table prompt add column effort text check (effort in ('low', 'medium', 'high', 'xhigh', 'max'));
