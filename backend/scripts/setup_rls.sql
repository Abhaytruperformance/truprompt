-- Sets up real Row Level Security enforcement for org-scoped tables. Run once
-- per Supabase project, via a direct Postgres connection (the SQL Editor's
-- underlying connection is fine too) -- NOT via the REST API/service_role key,
-- which can't create roles anyway.
--
-- Replace <GENERATE_A_PASSWORD> below with a fresh secret, e.g.:
--   python -c "import secrets; print(secrets.token_urlsafe(32))"
-- and put the same value in .env as APP_DB_PASSWORD.

do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'tru_app') then
        create role tru_app with login password '<GENERATE_A_PASSWORD>' nobypassrls;
    else
        alter role tru_app with password '<GENERATE_A_PASSWORD>' nobypassrls;
    end if;
end $$;

grant usage on schema public to tru_app;
grant select, insert, update, delete on organizations, organization_members, invitations, prompts to tru_app;
grant select, insert, update, delete on departments, custom_field_defs, prompt_custom_field_values to tru_app;
grant select, insert, update, delete on tags, prompt_tags, prompt_versions, prompt_shares, api_keys to tru_app;
grant select, insert, update, delete on generation_events, prompt_ratings to tru_app;
grant select, insert, update, delete on audit_events to tru_app;

alter table organizations enable row level security;
alter table organization_members enable row level security;
alter table invitations enable row level security;
alter table prompts enable row level security;
alter table departments enable row level security;
alter table custom_field_defs enable row level security;
alter table prompt_custom_field_values enable row level security;
alter table tags enable row level security;
alter table prompt_tags enable row level security;
alter table prompt_versions enable row level security;
alter table prompt_shares enable row level security;
alter table api_keys enable row level security;
alter table generation_events enable row level security;
alter table prompt_ratings enable row level security;
alter table audit_events enable row level security;

-- organizations: creating a new org isn't gated (nothing to isolate against
-- yet, and app_service/org_service.py sets app.org_id to the client-generated
-- id *before* the insert); reading/updating an existing one is.
drop policy if exists organizations_select on organizations;
drop policy if exists organizations_update on organizations;
drop policy if exists organizations_insert on organizations;
create policy organizations_select on organizations for select using (id = current_setting('app.org_id', true)::uuid);
create policy organizations_update on organizations for update using (id = current_setting('app.org_id', true)::uuid);
create policy organizations_insert on organizations for insert with check (true);

drop policy if exists members_isolation on organization_members;
create policy members_isolation on organization_members for all
  using (org_id = current_setting('app.org_id', true)::uuid)
  with check (org_id = current_setting('app.org_id', true)::uuid);

drop policy if exists invitations_isolation on invitations;
create policy invitations_isolation on invitations for all
  using (org_id = current_setting('app.org_id', true)::uuid)
  with check (org_id = current_setting('app.org_id', true)::uuid);

drop policy if exists prompts_isolation on prompts;
create policy prompts_isolation on prompts for all
  using (org_id = current_setting('app.org_id', true)::uuid)
  with check (org_id = current_setting('app.org_id', true)::uuid);

drop policy if exists departments_isolation on departments;
create policy departments_isolation on departments for all
  using (org_id = current_setting('app.org_id', true)::uuid)
  with check (org_id = current_setting('app.org_id', true)::uuid);

drop policy if exists custom_field_defs_isolation on custom_field_defs;
create policy custom_field_defs_isolation on custom_field_defs for all
  using (org_id = current_setting('app.org_id', true)::uuid)
  with check (org_id = current_setting('app.org_id', true)::uuid);

drop policy if exists prompt_custom_field_values_isolation on prompt_custom_field_values;
create policy prompt_custom_field_values_isolation on prompt_custom_field_values for all
  using (org_id = current_setting('app.org_id', true)::uuid)
  with check (org_id = current_setting('app.org_id', true)::uuid);

drop policy if exists tags_isolation on tags;
create policy tags_isolation on tags for all
  using (org_id = current_setting('app.org_id', true)::uuid)
  with check (org_id = current_setting('app.org_id', true)::uuid);

drop policy if exists prompt_tags_isolation on prompt_tags;
create policy prompt_tags_isolation on prompt_tags for all
  using (org_id = current_setting('app.org_id', true)::uuid)
  with check (org_id = current_setting('app.org_id', true)::uuid);

drop policy if exists prompt_versions_isolation on prompt_versions;
create policy prompt_versions_isolation on prompt_versions for all
  using (org_id = current_setting('app.org_id', true)::uuid)
  with check (org_id = current_setting('app.org_id', true)::uuid);

-- prompt_shares/api_keys: the *authenticated* (admin-side) create/list/revoke
-- operations go through tru_app + this policy like everything else. The
-- *public*, unauthenticated lookups (GET /api/public/shares/{token}, the API
-- key hash lookup in app/auth/api_key.py) intentionally bypass this entirely
-- via the service-role client -- see those modules' docstrings for why
-- (same precedent as org_service.accept_invitation's token lookup).
drop policy if exists prompt_shares_isolation on prompt_shares;
create policy prompt_shares_isolation on prompt_shares for all
  using (org_id = current_setting('app.org_id', true)::uuid)
  with check (org_id = current_setting('app.org_id', true)::uuid);

drop policy if exists api_keys_isolation on api_keys;
create policy api_keys_isolation on api_keys for all
  using (org_id = current_setting('app.org_id', true)::uuid)
  with check (org_id = current_setting('app.org_id', true)::uuid);

drop policy if exists generation_events_isolation on generation_events;
create policy generation_events_isolation on generation_events for all
  using (org_id = current_setting('app.org_id', true)::uuid)
  with check (org_id = current_setting('app.org_id', true)::uuid);

drop policy if exists prompt_ratings_isolation on prompt_ratings;
create policy prompt_ratings_isolation on prompt_ratings for all
  using (org_id = current_setting('app.org_id', true)::uuid)
  with check (org_id = current_setting('app.org_id', true)::uuid);

drop policy if exists audit_events_isolation on audit_events;
create policy audit_events_isolation on audit_events for all
  using (org_id = current_setting('app.org_id', true)::uuid)
  with check (org_id = current_setting('app.org_id', true)::uuid);

-- Verify:
--   select rolname, rolbypassrls, rolcanlogin from pg_roles where rolname = 'tru_app';
--   select relname, relrowsecurity from pg_class where relname in ('organizations','organization_members','invitations','prompts','departments','custom_field_defs','prompt_custom_field_values','tags','prompt_tags','prompt_versions','prompt_shares','api_keys');
--   select tablename, policyname, cmd from pg_policies where tablename in ('organizations','organization_members','invitations','prompts','departments','custom_field_defs','prompt_custom_field_values','tags','prompt_tags','prompt_versions','prompt_shares','api_keys');
