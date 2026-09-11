-- One-off migration: run this ONCE against the real Supabase project, after
-- applying the multi-tenancy tables in supabase_schema.sql and BEFORE locking
-- prompts.org_id to NOT NULL. Puts every existing user/prompt under a single
-- "TRUPerformance" organization (decision: migrate, not relaunch clean).
--
-- Safe to re-run: every statement is guarded so a second run is a no-op.

do $$
declare
    first_org_id uuid;
begin
    insert into organizations (name, slug)
    values ('TRUPerformance', 'truperformance')
    on conflict (slug) do nothing;

    select id into first_org_id from organizations where slug = 'truperformance';

    insert into organization_members (org_id, user_id, role)
    select first_org_id, u.id, 'owner'
    from users u
    where not exists (
        select 1 from organization_members m
        where m.org_id = first_org_id and m.user_id = u.id
    );

    update users
    set last_active_org_id = first_org_id
    where last_active_org_id is null;

    update prompts
    set org_id = first_org_id
    where org_id is null;
end $$;

-- Run this separately, only after confirming zero orphaned rows:
--   select count(*) from prompts where org_id is null;  -- must be 0
-- alter table prompts alter column org_id set not null;
