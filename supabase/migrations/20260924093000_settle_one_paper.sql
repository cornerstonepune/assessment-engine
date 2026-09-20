-- Settling one answer must not sign off papers nobody has looked at.
--
-- `resolve_result` finishes by calling `confirm_results(child, by)`, which until the migration
-- before this one had no choice but to confirm every candidate answer the child had. Now that a
-- confirm can be scoped to one paper, this one scopes it: a person who settles an answer on the
-- paper in front of them has read that paper, and nothing else.
create or replace function public.resolve_result(p_result_id uuid, p_status text, p_codes text[], p_by text)
returns void language plpgsql security definer set search_path = public as $$
declare child uuid; cap uuid;
begin
  if p_status not in ('correct', 'wrong', 'blank') then
    raise exception 'resolve_result: status must be correct, wrong or blank, not %', p_status;
  end if;
  update item_result set status = p_status, misconception_codes = coalesce(p_codes, '{}')
   where id = p_result_id and state = 'candidate';
  select si.child_id, c.id into child, cap from item_result r
    join capture c on c.id = r.capture_id join sheet_instance si on si.id = c.sheet_instance_id
   where r.id = p_result_id;
  if child is null then raise exception 'resolve_result: no candidate result %', p_result_id; end if;
  perform confirm_results(child, p_by, cap);
end $$;
