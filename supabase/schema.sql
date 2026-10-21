-- Work•Sleep•Repeat — Supabase schema (techspec §6)
--
-- Run this whole file once in the Supabase SQL editor of a fresh project.
-- Safe to re-run: every statement is "if not exists" or "create or replace",
-- and the seed rows use on conflict do nothing.
--
-- What this gives the app:
--   * one row per person in wsr_status
--   * two functions the anon key may call: wsr_update_status, wsr_get_state
--   * RLS on with no table policies, so the anon key cannot read or write the
--     table directly — only through those two security-definer functions.
--
-- The usage tables and wsr_report_usage / wsr_credit from techspec §6.1–6.2 are
-- deliberately NOT here: the usage feature was dropped on 2026-10-20 (tracker
-- Decisions), because the numbers only exist in Claude Code's terminal status
-- line, which never runs in VS Code or the desktop Code tab.

-- ---------------------------------------------------------------- table

create table if not exists wsr_status (
  user_id        text primary key,            -- 'rifat' | 'samee'
  display_name   text not null,
  working        boolean not null default false,
  since          timestamptz,                 -- current working session started
  today_seconds  integer not null default 0,
  today_date     date,                        -- Asia/Dhaka date today_seconds belongs to
  wants_next     boolean not null default false,   -- dibs (Phase 14)
  wants_next_at  timestamptz,
  wants_next_pct integer,                        -- "keep X% for me" (Phase 14b)
  last_heartbeat timestamptz,                 -- server time, set by wsr_update_status
  app_version    text,
  updated_at     timestamptz not null default now()
);

insert into wsr_status (user_id, display_name)
values ('rifat', 'Rifat'), ('samee', 'Samee')
on conflict (user_id) do nothing;

-- ------------------------------------------------------------ functions

-- Update my own status. The server stamps last_heartbeat/updated_at itself, so
-- the two PCs never disagree because of clock skew.
-- Only the keys present in p_fields change; everything else keeps its value.
-- Called with an empty object ('{}') it is a pure heartbeat.
create or replace function wsr_update_status(p_user text, p_fields jsonb)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  update wsr_status set
    working       = coalesce((p_fields->>'working')::boolean, working),
    since         = case when p_fields ? 'since'
                         then (p_fields->>'since')::timestamptz else since end,
    today_seconds = coalesce((p_fields->>'today_seconds')::int, today_seconds),
    today_date    = coalesce((p_fields->>'today_date')::date, today_date),
    wants_next    = coalesce((p_fields->>'wants_next')::boolean, wants_next),
    wants_next_at = case when p_fields ? 'wants_next_at'
                         then (p_fields->>'wants_next_at')::timestamptz else wants_next_at end,
    wants_next_pct = coalesce((p_fields->>'wants_next_pct')::int, wants_next_pct),
    app_version   = coalesce(p_fields->>'app_version', app_version),
    last_heartbeat = now(),
    updated_at     = now()
  where user_id = p_user;
end
$$;

-- One call returns everything the app needs: server time plus both rows.
-- server_now is what both PCs use to decide "is the other one online?", so the
-- answer does not depend on either laptop's clock.
create or replace function wsr_get_state()
returns jsonb
language sql
stable
security definer
set search_path = public
as $$
  select jsonb_build_object(
    'server_now', now(),
    'status', (select jsonb_agg(to_jsonb(s)) from wsr_status s)
  );
$$;

-- --------------------------------------------------------------- access

-- RLS on, and no policies for anon: direct selects/updates are refused.
alter table wsr_status enable row level security;

-- In case an earlier run of this file (or a dashboard click) left a policy
-- behind, drop the ones we might have made. Policies by other names are left
-- alone on purpose.
drop policy if exists wsr_status_anon_select on wsr_status;
drop policy if exists wsr_status_anon_all on wsr_status;

-- Take away the table-level grants PostgREST's roles get by default.
revoke all on table wsr_status from anon, authenticated;

-- The two functions are the whole API. security definer means they run as the
-- owner and so may touch the table past RLS.
revoke all on function wsr_update_status(text, jsonb) from public;
revoke all on function wsr_get_state() from public;
grant execute on function wsr_update_status(text, jsonb) to anon, authenticated;
grant execute on function wsr_get_state() to anon, authenticated;

-- ---------------------------------------------------------------- checks
--
-- After running the file, these should hold (see the Phase 11 checklist):
--   select * from wsr_status;                      -- works here (you are owner)
--   -- with the anon key over HTTP:
--   --   GET  /rest/v1/wsr_status        -> 401/permission denied
--   --   POST /rest/v1/rpc/wsr_get_state -> 200 with server_now + status
