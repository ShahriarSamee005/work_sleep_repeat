-- Phase 14b: add wants_next_pct to wsr_status
-- Run this in the Supabase SQL editor. Idempotent — safe to re-run.

-- 1. New column
alter table wsr_status add column if not exists wants_next_pct int;

-- 2. Update the function so it merges wants_next_pct from p_fields
--    (same coalesce pattern as the other int fields)
create or replace function wsr_update_status(p_user text, p_fields jsonb)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  update wsr_status set
    working        = coalesce((p_fields->>'working')::boolean, working),
    since          = case when p_fields ? 'since'
                          then (p_fields->>'since')::timestamptz else since end,
    today_seconds  = coalesce((p_fields->>'today_seconds')::int, today_seconds),
    today_date     = coalesce((p_fields->>'today_date')::date, today_date),
    wants_next     = coalesce((p_fields->>'wants_next')::boolean, wants_next),
    wants_next_at  = case when p_fields ? 'wants_next_at'
                          then (p_fields->>'wants_next_at')::timestamptz else wants_next_at end,
    wants_next_pct = coalesce((p_fields->>'wants_next_pct')::int, wants_next_pct),
    app_version    = coalesce(p_fields->>'app_version', app_version),
    last_heartbeat = now(),
    updated_at     = now()
  where user_id = p_user;
end
$$;

-- wsr_get_state already returns to_jsonb(s) for each row, so the new column
-- is included automatically — no change needed there.
