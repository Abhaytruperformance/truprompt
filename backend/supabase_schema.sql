-- Run this against your Supabase project (SQL Editor) before starting the backend.

create extension if not exists pgcrypto;

create table if not exists organizations (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    slug text unique not null,
    -- Set by an admin (PUT /api/orgs/me/workos-connection) once they connect
    -- their own Okta/Azure AD/Google Workspace via WorkOS -- see app/auth/workos.py.
    workos_connection_id text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists users (
    id uuid primary key default gen_random_uuid(),
    -- Nullable: a WorkOS-only user (see external_identities below) has no
    -- Microsoft identity. Multiple NULLs don't violate the unique constraint
    -- (SQL treats each NULL as distinct for uniqueness purposes).
    microsoft_oid text unique,
    name text not null,
    email text unique not null,
    role text not null default 'user',
    profile_image text not null default '404',
    last_active_org_id uuid references organizations(id),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
-- If `users` already existed from before multi-tenancy, `create table if not
-- exists` above is a no-op and won't add the new column -- this does, safely,
-- whether the table is brand new or pre-existing:
alter table users add column if not exists last_active_org_id uuid references organizations(id);
-- Same reasoning: if `users` pre-dates WorkOS support, this drops the NOT
-- NULL that create-table-if-not-exists above can't retroactively remove.
alter table users alter column microsoft_oid drop not null;

-- Membership is a join table (not a single org_id on users) so a person can
-- belong to more than one organization; last_active_org_id above just tracks
-- which membership is "current" for a session without an extra lookup.
create table if not exists organization_members (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    user_id uuid not null references users(id) on delete cascade,
    role text not null default 'member' check (role in ('owner', 'admin', 'editor', 'member')),
    created_at timestamptz not null default now(),
    unique (org_id, user_id)
);

create table if not exists invitations (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    email text not null,
    role text not null default 'member' check (role in ('owner', 'admin', 'editor', 'member')),
    token text unique not null,
    invited_by uuid not null references users(id),
    expires_at timestamptz not null,
    accepted_at timestamptz,
    created_at timestamptz not null default now()
);

create table if not exists prompts (
    id uuid primary key default gen_random_uuid(),
    org_id uuid references organizations(id) on delete cascade,
    user_id uuid not null references users(id) on delete cascade,
    category text not null,
    user_prompt text not null,
    prompt text not null,
    optimizer text,
    most_used_prompt_count integer not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
-- Same as above: needed if `prompts` already existed pre-multi-tenancy.
-- org_id is nullable here only so `migrate_to_first_org.sql` can backfill existing
-- rows before locking it down; run this immediately after that migration:
--   alter table prompts alter column org_id set not null;
alter table prompts add column if not exists org_id uuid references organizations(id) on delete cascade;

create table if not exists departments (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    name text not null,
    created_at timestamptz not null default now(),
    unique (org_id, name)
);

create table if not exists custom_field_defs (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    name text not null,
    field_type text not null default 'text' check (field_type in ('text', 'number', 'select', 'date')),
    options jsonb,  -- allowed values, only used when field_type = 'select'
    created_at timestamptz not null default now(),
    unique (org_id, name)
);

create table if not exists prompt_custom_field_values (
    id uuid primary key default gen_random_uuid(),
    -- Denormalized (also derivable via prompt_id -> prompts.org_id) so RLS on
    -- this table stays a flat equality check like every other org-scoped
    -- table, instead of a cross-table subquery policy.
    org_id uuid not null references organizations(id) on delete cascade,
    prompt_id uuid not null references prompts(id) on delete cascade,
    field_def_id uuid not null references custom_field_defs(id) on delete cascade,
    value text,
    unique (prompt_id, field_def_id)
);

alter table prompts add column if not exists department_id uuid references departments(id) on delete set null;

-- Block 2: multi-label tags (distinct from department -- many-per-prompt, used
-- for filtering/search, like GitHub labels).
create table if not exists tags (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    name text not null,
    created_at timestamptz not null default now(),
    unique (org_id, name)
);

create table if not exists prompt_tags (
    prompt_id uuid not null references prompts(id) on delete cascade,
    tag_id uuid not null references tags(id) on delete cascade,
    org_id uuid not null references organizations(id) on delete cascade,  -- denormalized, same reason as prompt_custom_field_values
    primary key (prompt_id, tag_id)
);

-- Block 3: versioning. `prompts` stays the single mutable "current" row;
-- this is purely a history log snapshotted before every edit/restore.
create table if not exists prompt_versions (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    prompt_id uuid not null references prompts(id) on delete cascade,
    version_number integer not null,
    category text not null,
    user_prompt text not null,
    prompt text not null,
    optimizer text,
    edited_by uuid not null references users(id),
    created_at timestamptz not null default now(),
    unique (prompt_id, version_number)
);

-- Block 4: public share links. Password hashing uses stdlib pbkdf2_hmac (no
-- new dependency) -- proportionate for a share-link password, not an account
-- credential. generation_limit/generation_count exist for a future public
-- regenerate action; not enforced yet (see README roadmap).
create table if not exists prompt_shares (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    prompt_id uuid not null references prompts(id) on delete cascade,
    token text unique not null,
    password_hash text,
    password_salt text,
    generation_limit integer,
    generation_count integer not null default 0,
    created_by uuid not null references users(id),
    created_at timestamptz not null default now(),
    revoked_at timestamptz
);

-- Block 5: public API keys. Only the sha256 hash is stored -- the plaintext
-- key is shown to the admin exactly once, at creation, and never again.
create table if not exists api_keys (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    name text not null,
    key_hash text not null unique,
    key_prefix text not null,
    created_by uuid not null references users(id),
    created_at timestamptz not null default now(),
    last_used_at timestamptz,
    revoked_at timestamptz
);

create index if not exists prompts_user_id_idx on prompts(user_id);
create index if not exists prompts_org_id_idx on prompts(org_id);
create index if not exists prompts_most_used_idx on prompts(most_used_prompt_count desc);
create index if not exists organization_members_user_id_idx on organization_members(user_id);
create index if not exists invitations_token_idx on invitations(token);
create index if not exists departments_org_id_idx on departments(org_id);
create index if not exists custom_field_defs_org_id_idx on custom_field_defs(org_id);
create index if not exists prompt_custom_field_values_prompt_id_idx on prompt_custom_field_values(prompt_id);
create index if not exists tags_org_id_idx on tags(org_id);
create index if not exists prompt_tags_prompt_id_idx on prompt_tags(prompt_id);
create index if not exists prompt_versions_prompt_id_idx on prompt_versions(prompt_id);
create index if not exists prompt_shares_token_idx on prompt_shares(token);
create index if not exists api_keys_key_hash_idx on api_keys(key_hash);

-- Approved prompt library: draft -> review -> approved -> archived. Existing
-- rows default to 'approved' so nothing already in production suddenly looks
-- unreviewed; new prompts are inserted as 'draft' explicitly by the app.
alter table prompts add column if not exists status text not null default 'approved'
    check (status in ('draft', 'review', 'approved', 'archived'));
alter table prompts add column if not exists approved_at timestamptz;
create index if not exists prompts_status_idx on prompts(status);

-- What grounded this prompt, if generated from an uploaded file/URL --
-- persisted with the prompt instead of the previous extract-then-discard
-- behavior (content only ever lived in frontend state, gone once that
-- generation result expired/the tab closed). Bounded the same as generation
-- itself (MAX_CONTEXT_CHARS), so this never stores more than one generation
-- call already saw.
alter table prompts add column if not exists source_type text check (source_type in ('file', 'url'));
alter table prompts add column if not exists source_name text;
alter table prompts add column if not exists source_context text;

-- Analytics: native usage + ratings, not a Langfuse integration (that needs a
-- real external account -- see README). One row per successful generation,
-- across all four surfaces (web/api/mcp/share); ratings are one-per-user-per-prompt.
create table if not exists generation_events (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    user_id uuid references users(id) on delete set null,
    prompt_id uuid references prompts(id) on delete set null,
    source text not null check (source in ('web', 'api', 'mcp', 'share')),
    model text,
    created_at timestamptz not null default now()
);
-- 'share' added after the table already existed in some environments --
-- idempotent re-apply for those (fresh installs already get it from the
-- inline check above).
alter table generation_events drop constraint if exists generation_events_source_check;
alter table generation_events add constraint generation_events_source_check
    check (source in ('web', 'api', 'mcp', 'share'));
create index if not exists generation_events_org_created_idx on generation_events(org_id, created_at desc);
create index if not exists generation_events_org_prompt_idx on generation_events(org_id, prompt_id, created_at desc);

create table if not exists prompt_ratings (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    prompt_id uuid not null references prompts(id) on delete cascade,
    user_id uuid not null references users(id) on delete cascade,
    rating integer not null check (rating between 1 and 5),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (prompt_id, user_id)
);
create index if not exists prompt_ratings_prompt_id_idx on prompt_ratings(prompt_id);

-- WorkOS SSO: a user can hold more than one linked identity (their own
-- Microsoft SSO plus a customer's WorkOS identity), so this is a separate
-- mapping table rather than reusing/extending users.microsoft_oid directly.
-- No RLS -- not org-scoped, accessed only via the service-role client during
-- login before any org context exists, same precedent as `users` itself.
create table if not exists external_identities (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    provider text not null check (provider in ('workos')),
    subject text not null,
    created_at timestamptz not null default now(),
    unique (provider, subject)
);
create index if not exists external_identities_user_id_idx on external_identities(user_id);

-- One WorkOS connection can't accidentally be claimed by two orgs.
create unique index if not exists organizations_workos_connection_id_idx
    on organizations(workos_connection_id) where workos_connection_id is not null;

-- Governance: who approved a prompt, not just when. approved_at already
-- existed; this is the other half, set alongside it in update_prompt_status.
alter table prompts add column if not exists approved_by uuid references users(id);

-- Credential lifecycle: nullable, no expiry by default (backward compatible
-- with every key created before this column existed).
alter table api_keys add column if not exists expires_at timestamptz;

-- Ties a generation event to which numbered version of the prompt was live
-- at generation time (only meaningful when prompt_id is set -- New Chat/
-- Playground generations with no saved prompt stay null, same as prompt_id
-- itself does today). A plain integer, not a FK into prompt_versions --
-- that table only holds *pre-edit* snapshots, so "the current live state"
-- never has a row there to reference; this is computed the same way
-- version_service.snapshot_version computes "next version number."
alter table generation_events add column if not exists prompt_version_number integer;

-- Audit log for admin/governance actions -- who did what, to what, when.
-- Separate from generation_events (that's usage, this is administration).
-- Best-effort logging (see audit_service.log_audit_event) -- a logging
-- failure must never break the action it's logging, same precedent as
-- log_generation_event.
create table if not exists audit_events (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    actor_user_id uuid references users(id) on delete set null,
    action text not null,
    resource_type text not null,
    resource_id uuid,
    metadata jsonb,
    created_at timestamptz not null default now()
);
create index if not exists audit_events_org_created_idx on audit_events(org_id, created_at desc);
-- RLS: see scripts/setup_rls.sql, same isolation pattern as every other
-- org-scoped table.

-- Least-privilege API keys: nullable, NULL = legacy/unrestricted (every key
-- created before this column existed keeps working exactly as it does
-- today). Every key created from this point on always gets an explicit
-- array (see api_key_service.create_api_key) -- NULL is a closed set, never
-- written by any code path going forward, only grandfathered for rows that
-- already existed. See app/auth/api_key.py for the enforcement + the
-- migration note on eventually eliminating NULL entirely.
alter table api_keys add column if not exists scopes text[];
