# TruPrompt — Technical Reference

How `tru-prompt-frontend` and `tru-prompt-backend` fit together: architecture, auth flow, API contract, data model, and environment variables.

## Architecture

```
Browser
  │
  ▼
tru-prompt-frontend (React 18 + Redux Toolkit / RTK Query, Bootstrap)
  │  fetch/axios calls, always with credentials: 'include'
  ▼
tru-prompt-backend (FastAPI)
  │
  ├──▶ Supabase (Postgres) — users, prompts
  ├──▶ Microsoft Graph / Entra ID (MSAL) — SSO login
  └──▶ OpenAI (gpt-4o-mini) — prompt generation
```

The frontend never talks to Supabase, Microsoft, or OpenAI directly — every secret (Supabase service-role key, Azure AD client secret, OpenAI key) lives only in the backend's `.env`.

## Auth

Every authenticated request relies on a single `token` cookie: an **httpOnly** JWT (`{sub: user_id, exp: ...}`) set by the backend. The frontend cannot read this cookie in JavaScript — it's sent automatically on every request because RTK Query is configured with `credentials: 'include'`. (The frontend also sends an `Authorization: Bearer <cookie-value>` header via `js-cookie`, but since `js-cookie` can't read an httpOnly cookie, that header is always `Bearer undefined` — dead code the backend ignores.)

### `GET /api/users/auth/microsoft` — one route, three behaviors

This single route has to serve the frontend's three different uses of the same URL, distinguished by request shape:

| Condition | Behavior |
|---|---|
| `?code=...` present | Microsoft's OAuth callback. Exchanges the code via MSAL, calls Graph `/me`, upserts the `users` row, mints the JWT, sets the cookie, redirects to `FRONTEND_URL`. |
| No code, valid `token` cookie | Background session check (`useMicrosoftLoginQuery` on every page load). Returns `{"user": {...}}`. |
| No code, no/invalid cookie, `Accept: text/html` | A real browser navigation — the "Login with Microsoft" button was clicked. Redirects to Microsoft's consent screen. |
| No code, no/invalid cookie, not HTML | Background session check while logged out. Returns `401`, so the frontend shows `LoginScreen`. |

### Dev bypass

`GET /api/users/auth/dev-login` skips Microsoft entirely: it upserts a fixed `dev@local.test` user straight into Supabase and sets the same cookie, same as a real login would. Active only while `DEBUG=true` in the backend's `.env`; returns `404` otherwise, so it can never be reachable in production.

## API reference

All routes are prefixed `/api`.

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/users/auth/microsoft` | — | See auth section above |
| GET | `/users/auth/dev-login` | — (DEBUG only) | Dev bypass login |
| GET | `/users/auth/logout` | — | Clears the cookie |
| GET | `/users/allusers` | required | `{"allUsers": [...]}` — used to resolve names/avatars in prompt lists |
| GET | `/prompts/` | — | All prompts, sorted by usage count desc. `{"allPrompts": [...]}` |
| GET | `/prompts/auth/verifiedUserPrompts/` | required | Current user's saved prompts. `{"allPrompts": [...]}` |
| POST | `/prompts/auth/verifiedUserPrompts/` | required | Body `{category, userPrompt, prompt, optimizer}` → creates a prompt owned by the caller, returns it directly (not wrapped) |
| GET | `/prompts/{id}` | — | Single prompt by id, `{"prompt": {...}}` — public since both "most used" and "my saved" views resolve through this |
| PATCH | `/prompts/updatePromptCount/{id}` | — | Increments the usage counter (fired on copy-to-clipboard) |
| PATCH | `/prompts/{id}` | required + ownership | Partial update; 403 if you don't own the prompt |
| POST | `/ai/generate-prompt` | required | Body `{userPrompt, selectedOptions}` → calls OpenAI server-side, returns `{category, userPrompt, optimizer, prompt, id}` |

Route ordering matters in `app/routers/prompts.py`: literal paths (`/auth/verifiedUserPrompts/`, `/updatePromptCount/{id}`) are declared before the generic `/{id}` route so FastAPI doesn't swallow them.

## Data model (Supabase/Postgres)

Defined in `tru-prompt-backend/supabase_schema.sql`. API responses map snake_case columns to the camelCase shape the frontend expects (`id → _id`, `user_prompt → userPrompt`, etc.) via `schemas/user.py` / `schemas/prompt.py` — plain dict mapping, no ORM.

**`users`**: `id` (uuid), `microsoft_oid` (unique — Azure AD object id, or the fixed dev-login value), `name`, `email` (unique), `role` (default `'user'`), `profile_image` (default `'404'`, a sentinel the frontend treats as "show the default avatar icon"), `created_at`, `updated_at`.

**`prompts`**: `id` (uuid), `user_id` (fk → users), `category`, `user_prompt` (the user's raw idea), `prompt` (the generated result), `optimizer` (bullet-point context GPT returns alongside the prompt), `most_used_prompt_count` (int, default 0), `created_at`, `updated_at`.

## Environment variables

**Backend** (`tru-prompt-backend/.env`, see `.env.example`): `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `MS_CLIENT_ID`/`MS_CLIENT_SECRET`/`MS_TENANT_ID`/`MS_REDIRECT_URI`, `JWT_SECRET`/`JWT_EXPIRE_MINUTES`, `OPENAI_API_KEY`, `FRONTEND_URL`/`BACKEND_URL`, `CORS_ORIGINS`, `DEBUG`.

**Frontend** (`tru-prompt-frontend/.env`): `REACT_APP_BACKEND_URL` — must match wherever the backend actually runs; CRA bakes `REACT_APP_*` vars in at dev-server/build start, so changing this requires restarting `npm start`.

## Local dev gotchas

- If port 8000 (backend) or 3000 (frontend) is already in use by something else on your machine, just run on a different port — but remember to update `MS_REDIRECT_URI` (backend `.env`) and `REACT_APP_BACKEND_URL` (frontend `.env`) to match, and restart both processes (neither picks up `.env` changes without a restart).
- `uvicorn --reload` only watches Python source files, not `.env` — a credentials change always needs a manual restart.

## Security notes

- `SUPABASE_SERVICE_ROLE_KEY` and `MS_CLIENT_SECRET` are confidential/bypass-RLS credentials — never expose them to the frontend, never commit `.env`.
- The frontend originally called OpenAI directly from the browser with `dangerouslyAllowBrowser: true`, and a separate dead file (`apiSlice.js`) had a hardcoded Groq key. Both are gone from the code, but **both keys were committed to git history and should be rotated/revoked regardless**.

## Roadmap

Deliberately not built yet — see `tru-prompt-backend/README.md` for the full list. Summary: pagination, rate limiting, and request logging (near-term); tags, favorites, soft delete, search, prompt versioning, templates (mid-term); AI provider abstraction, richer analytics, admin routes, org/RBAC (long-term). All of these were scoped out because most also need frontend UI that doesn't exist yet — building them backend-only would be dead API surface.
