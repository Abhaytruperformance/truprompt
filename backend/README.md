# tru-prompt-backend

FastAPI + Supabase (Postgres) backend for [tru-prompt-frontend](https://github.com/dev-truperformance/tru-prompt-frontend). Multi-tenant: every user and prompt belongs to an organization, with role-based access (owner/admin/editor/member). Implements Microsoft SSO, prompt CRUD, server-side AI prompt generation (the OpenAI call no longer runs in the browser), and org/team management.

## Setup

1. **Supabase**: create a project, then run `supabase_schema.sql` in the SQL Editor. Copy the Project URL and the `service_role` key (Project Settings -> API) into `.env`. If you already had this schema from before multi-tenancy existed, also run `scripts/migrate_to_first_org.sql` once (see "Multi-tenancy" below).
2. **RLS setup**: run `scripts/setup_rls.sql` (generate a password first, see the comment at the top of that file) via a direct Postgres connection — the SQL Editor works, or `psql`/`psycopg2` against the pooler host (Project Settings -> Database -> Connection pooling; use that host, not the plain `db.<ref>.supabase.co` one — see "Isolation" below for why). Put the same password in `.env` as `APP_DB_PASSWORD`, along with `APP_DB_HOST`/`APP_DB_USER` (must be `tru_app.<project-ref>`).
3. **Azure AD app registration**: under Authentication, add a Web platform redirect URI that exactly matches `MS_REDIRECT_URI` below (e.g. `http://localhost:8000/api/users/auth/microsoft`). Under API permissions, ensure delegated `User.Read` (Microsoft Graph) is granted. Copy the client ID, a client secret, and the tenant ID into `.env`.
4. Copy `.env.example` to `.env` and fill in every value (Supabase, Azure AD, `JWT_SECRET`, `OPENAI_API_KEY`).
5. `pip install -r requirements.txt`
6. `uvicorn app.main:app --reload --port 8000`
7. Point the frontend at this backend: in `tru-prompt-frontend/.env`, set `REACT_APP_BACKEND_URL=http://localhost:8000`.

## How Microsoft login works

`GET /api/users/auth/microsoft` is one route that behaves differently depending on how it's called, to match the frontend exactly with no frontend auth changes:

1. Has `?code=...` (Microsoft's OAuth callback) -> exchanges the code, upserts the user, sets an httpOnly `token` cookie, redirects to the frontend.
2. No code, valid `token` cookie -> returns `{"user": {...}}` (session bootstrap on page load).
3. No code, no cookie, browser navigation (`Accept: text/html`, i.e. the login button was clicked) -> redirects to Microsoft's consent screen.
4. No code, no cookie, background fetch -> `401` so the frontend shows the login screen.

Auth for every other endpoint is via that same `token` cookie (read server-side from the request, not from any header) — the frontend's `Authorization: Bearer` header is dead code (it can't read an httpOnly cookie) and is ignored.

### Dev bypass (no Azure AD needed)

While `DEBUG=true`, `GET /api/users/auth/dev-login` logs you in as a fixed test user (`dev@local.test`) without any Azure AD round-trip — visit `http://localhost:8000/api/users/auth/dev-login` directly in a browser and it sets the same cookie and redirects to the frontend, exactly like a real login would. It still needs a real Supabase project (prompts/users are stored there regardless of how you logged in). The route 404s whenever `DEBUG` is false, so it can't be reachable in production.

## Multi-tenancy

Every user belongs to at least one organization (`organizations` / `organization_members`, a many-to-many join so a person can be in more than one org); every prompt belongs to exactly one org. Roles are `owner` > `admin` > `editor` > `member`, enforced via the `require_role(...)` FastAPI dependency in `app/auth/dependencies.py` — member+ can read the org's prompts, editor+ can create/edit them, admin+ can manage members and invitations.

**First login auto-provisions an org.** There's no signup form yet — when someone logs in (real SSO or `dev-login`) with zero existing org memberships, `app/services/org_service.py` creates a personal org for them on the spot (`"{name}'s Organization"`, role `owner`). Teammates join an *existing* org through the invitations flow instead: `POST /api/orgs/invitations` (admin+) creates a token and emails it via Resend (`app/services/email_service.py`), `POST /api/orgs/invitations/accept` (any logged-in user) redeems it. Note: there's no `/accept-invite` frontend page yet — the emailed link points at one, but building it is separate frontend work. Also note: Resend's shared `onboarding@resend.dev` sender can only deliver to Resend's own test address or the account's verified email until a custom sending domain is verified in the Resend dashboard — real invitee addresses will 422 until then.

**Migrating a pre-multi-tenancy database**: `scripts/migrate_to_first_org.sql` creates a single `TRUPerformance` org and attaches every existing user/prompt to it — run it once, confirm `select count(*) from prompts where org_id is null` returns 0, then run the `alter table prompts alter column org_id set not null` at the bottom of that file.

**Isolation is enforced by real Postgres Row Level Security, not just application code.** `organizations`, `organization_members`, `invitations`, and `prompts` all have RLS enabled with policies keyed on `current_setting('app.org_id', true)`. This only works because org-scoped queries go through a *separate* Postgres connection ([app/db/pg.py](app/db/pg.py)) authenticated as a dedicated `tru_app` role with `NOBYPASSRLS` — critically **not** `SUPABASE_SERVICE_ROLE_KEY` or the Postgres superuser, both of which bypass RLS unconditionally regardless of how you connect (REST API or direct). Every request sets `app.org_id` (and `app.user_id`) via `SET LOCAL` inside a transaction before querying; a connection that skips this fails **closed** — zero rows, not all rows — since `current_setting(..., true)` returns `NULL` when unset and `col = NULL` is never true in SQL.

Getting a *working* direct connection took two detours worth knowing about if you ever need to recreate this: the plain `db.<ref>.supabase.co` host is IPv6-only and often unreachable — use the pooler host instead (Project Settings -> Database -> Connection pooling), and its username must be `<role>.<project-ref>` (e.g. `tru_app.abcdefgh`), not a bare role name, or Supavisor rejects it with "no tenant identifier provided."

`users` deliberately stays on the old `supabase-py`/service-role path, unscoped by RLS — it isn't keyed by a single `org_id` (a person can belong to multiple orgs) and every read is already either the caller's own row or an already-filtered id list. Verified end-to-end: connecting as `tru_app` without setting `app.org_id` returns zero rows on tables with real data in them, and two independently-provisioned orgs each get a clean 404 trying to read the other's prompts.

**WorkOS (per-org SSO) has real credentials but isn't wired into login yet.** `app/auth/workos.py` builds a real AuthKit authorization URL and can exchange a callback code for a WorkOS `Profile` (verified against the installed `workos` v10 SDK — it uses a `WorkOSClient` instance, not the module-level globals older docs/examples show). It's intentionally not called from any route yet — see that file's docstring for why (short version: `users.microsoft_oid` is Microsoft-specific, and reusing it for a different identity provider needs a real schema decision first, not a silent hack). Also still needed before it's usable end-to-end: a WorkOS connection configured per customer org (`organizations.workos_connection_id`), which requires a WorkOS dashboard setup this project doesn't have yet.

## Departments, custom fields, and prompt management

Two new org-scoped, admin-managed resources sit alongside the fixed AI-generation `category`:

- **Departments** (`departments`, `prompts.department_id`) — a freeform, per-org list (e.g. Marketing/Sales/Engineering), managed via `GET/POST/DELETE /api/departments/` (admin+ for write). Independent of `category`: a prompt can be tagged `SEO` *and* assigned to the `Marketing` department. "My Saved Prompts" in the sidebar groups by department; unassigned prompts land in an "Unassigned" bucket.
- **Custom fields** (`custom_field_defs`, `prompt_custom_field_values`) — structured, Notion-property-style fields (`text`/`number`/`select`/`date`, with an `options` list for `select`) for whenever a prompt doesn't fit the fixed category taxonomy. Managed via `GET/POST/DELETE /api/custom-fields/`; values are read/written per-prompt via the `customFields` object on every prompt response and `PUT /api/prompts/{id}/custom-fields`.
- **Prompt management** — the **Manage** sidebar tab (admin+ only) lists every org prompt with inline department assignment, custom field editing, and delete (`DELETE /api/prompts/{id}`, previously missing entirely). The **Team** tab also gained a cancel button on pending invitations (`DELETE /api/orgs/invitations/{id}`) for the same reason — there was no way to remove a stale/duplicate one before.

All three new tables have real RLS (same `tru_app`/`SET LOCAL app.org_id` mechanism as everything else — see "Isolation" above); `prompt_custom_field_values` denormalizes `org_id` onto itself so its policy stays a flat equality check instead of a cross-table subquery.

## AI generation

`app/services/openai_service.py` calls whichever provider is configured. If `OPENROUTER_API_KEY` is set to a real key, it routes through [OpenRouter](https://openrouter.ai) (`OPENROUTER_MODEL`, default a free-tier model) instead of OpenAI — useful for testing without paying, since OpenRouter's free models cost nothing. Clear `OPENROUTER_API_KEY` (or leave it as the placeholder) to fall back to real `OPENAI_API_KEY` + `gpt-4o-mini`, no code change needed.

The model is asked to respond with a single JSON object (`{"optimizer": "...", "prompt": "..."}`) rather than a custom `Optimizer: ... | Prompt: ...` text format — JSON is followed far more reliably, especially by smaller/free models. Parsing (`_parse_completion`) still falls back to the old `|`-split format, and finally to "whole response as the prompt," for any model that ignores both.

Note: OpenRouter's free-model catalog changes over time — if `OPENROUTER_MODEL` ever 404s as "unavailable for free," check https://openrouter.ai/models?max_price=0 for a current one.

## Deploying (promptgen.tp-devserver.com)

The Azure AD app registration's redirect URI is registered only for `https://promptgen.tp-devserver.com/api/users/auth/microsoft` — real Microsoft login cannot complete against `localhost` no matter what `MS_REDIRECT_URI` is set to locally, since Azure AD checks for an exact match against what's registered. Local dev therefore always uses `.env` (localhost) + the `dev-login` bypass; real SSO only works once actually deployed at that domain.

`.env.production` holds the real values for that deployment (gitignored, same as `.env`) — copy it to `.env` on the actual server rather than editing it in place. Two assumptions baked into it that are worth confirming before deploying:
- `MS_REDIRECT_URI`/`FRONTEND_URL`/`BACKEND_URL` assume `https://` — Azure AD requires TLS for any non-localhost redirect URI, but confirm the scheme matches exactly what's registered.
- `FRONTEND_URL` and `BACKEND_URL` are assumed to be the same domain (i.e. a reverse proxy routes `/api/*` to this backend and everything else to the frontend build) — adjust if the API actually lives on its own subdomain.

`OPENAI_API_KEY` in `.env.production` is still a placeholder — fill in a real key before deploying, or AI generation will fail in production the same way it does locally right now.

## Phase 1 (complete): tags/search, versioning, sharing, public API

Everything below closes out Phase 1's remaining blocks (Block 1, multi-tenancy, shipped earlier; Block 2 was partially covered by Departments/Custom Fields before this).

- **Tags** (`tags`, `prompt_tags`) — multi-label, many-per-prompt (unlike Departments, which is one-per-prompt), for filtering/search. `GET/POST/DELETE /api/tags/` (admin+ for write), `PUT /api/prompts/{id}/tags`. `GET /api/prompts/` and `GET /api/prompts/auth/verifiedUserPrompts/` both take optional `?search=`, `?departmentId=`, `?tagId=` query params.
- **Versioning** (`prompt_versions`) — `prompts` stays the single mutable "current" row; every content edit (`category`/`userPrompt`/`prompt`/`optimizer`) snapshots the pre-edit state into `prompt_versions` first, inside the same transaction as the update. `GET /api/prompts/{id}/versions` lists history; `POST /api/prompts/{id}/versions/{versionId}/restore` copies an old version's content forward — restoring itself snapshots the pre-restore state first, so nothing is ever lost.
- **Sharing** (`prompt_shares`) — `POST /api/prompts/{id}/share` (editor+, optional password) creates a public link; `GET /api/public/shares/{token}` is genuinely unauthenticated (no cookie needed) and returns the prompt read-only, gated by password if one was set (stdlib `hashlib.pbkdf2_hmac`, no new dependency). `DELETE /api/prompts/{id}/share/{shareId}` revokes. The public read uses the service-role client rather than `org_scoped_cursor`, same precedent as `accept_invitation`'s token lookup — possessing the unguessable token is itself the authorization.
- **Public API + keys** (`api_keys`) — `POST /api/api-keys/` (admin+) generates a key and returns the plaintext exactly once (only the SHA-256 hash is ever stored); `GET/DELETE` list/revoke. `POST /v1/prompts/{id}/generate` (a separate `/v1` surface, not `/api`) authenticates via `Authorization: Bearer <key>` instead of the cookie and re-runs generation for one of the org's existing saved prompts — read-only, same semantics as the app's own "regenerate" button, does not overwrite the stored prompt.

All five new tables have real RLS (same `tru_app`/`SET LOCAL app.org_id` mechanism as everything else); `prompt_shares`/`api_keys` are the only tables where an *unauthenticated* lookup path also exists (the public share fetch, the API key hash lookup) — those two specific reads intentionally bypass RLS via the service-role client, documented in `app/services/share_service.py` and `app/auth/api_key.py`.

### MCP / Claude custom connector (Phase 2, item 4)

`app/mcp_server.py` mounts a Model Context Protocol server at `/mcp` (Streamable HTTP), exposing an org's TruPrompt data as 5 read/regenerate-only tools: `list_prompts` (same `search`/`department_id`/`tag_id` filters as the REST list endpoints), `get_prompt`, `generate_prompt` (same semantics as `POST /v1/prompts/{id}/generate` — read-only, doesn't overwrite the stored prompt), `list_tags`, `list_departments`. No write tools in v1.

**Auth**: identical model to the public REST API — `Authorization: Bearer <api_key>` (same keys created via `POST /api/api-keys/`). `app/auth/api_key.py`'s `resolve_api_key_org()` is shared by both the REST dependency and the MCP server's auth middleware, so there's one auth implementation, not two. Errors surface as MCP tool errors (`unauthorized: ...`, `not_found`, `rate_limited`, `upstream_error`, `internal_error`) rather than HTTP status codes, since MCP has no HTTP-status concept of its own.

**Important limitation**: this is API-key-header auth, not OAuth. It works with Claude Code, Claude Desktop (via a project/user `.mcp.json` with a custom header), Cursor, Windsurf, VS Code, and any other MCP client that supports custom headers — but it will **not** show up as a one-click "Add connector" inside claude.ai's own consumer UI, which specifically requires a real OAuth 2.1 authorization server. That's a separate, materially bigger subsystem (client registration, consent screen, token issuance/refresh) and is not built here — see Roadmap below.

## Roadmap (not built yet)

- **Phase 2**: multi-model via OpenRouter + playground, content input (doc/URL upload as context), analytics (Langfuse candidate). The MCP/Claude connector itself now has a v1 (API-key auth, above) — a full OAuth 2.1 layer for one-click claude.ai connector support is the natural next step if that specific UX is ever needed.
- **Phase 3 ("Total Coverage", manager-approved)**: AI Assistants, Flows, Tools, prompt A/B testing/evals, a prompt marketplace, white-label shares, fine-tuned/private model connections, native deep observability, Make.com/Sheets integrations, SOC2/SCIM enterprise hardening. Full detail in `PROJECT-PLAN.md` at the repo root.
- **Multi-tenancy follow-ups**: WorkOS wired live into login (currently scaffolded only, see above), RLS on `users` too (needs a "shared org membership" subquery policy, not just a single `org_id` column), rate limiting, structured request logging.
- **Product backlog surfaced during review**: audit logs (prompt created/edited/deleted/shared, API key created, invitation sent, role changed), a draft→review→approved→archived prompt approval workflow, `{{variable}}` templating in prompts, PR-style comments on prompts, import/export (Markdown/JSON/CSV/ZIP), per-org default settings (model/temperature/token limits/branding), webhooks on prompt events, cost/spend budgets and alerts for multi-model usage.
- **Departments/custom fields follow-ups**: department hierarchy/nesting or color-coding (currently a flat named list), custom field types beyond text/number/select/date (no relations/formulas/rollups), editing a custom field's type/options after creation (currently delete-and-recreate only), bulk multi-select actions or CSV export in the Manage panel, pagination on the All Prompts table.
- **Sharing/public API follow-ups**: no live "regenerate" action or embeddable widget on the public share page (read-only view only, for now — the original plan calls the widget a "fast-follow"); `generation_limit`/`generation_count` columns exist on `prompt_shares` but aren't enforced yet (no public-facing generation action to count against); no enforced per-key rate limiting on the public API (`last_used_at` is tracked so a future limiter has something to build on).

## Security notes

- The old client-side OpenAI key (`REACT_APP_OPENAI_API`) and the hardcoded Groq key in the frontend's `apiSlice.js` were both committed to git history — rotate/revoke both, even though the code referencing them has been removed.
- `SUPABASE_SERVICE_ROLE_KEY` and `MS_CLIENT_SECRET` bypass Row Level Security / act as a confidential client — never expose them to the frontend or commit `.env`.
