# TruPrompt

An internal AI prompt-generation tool. Users sign in via Microsoft SSO, describe a rough idea plus pick "expert" categories (SEO, Design, Web Development, Lead Generation, etc.), and the app returns a polished, reusable prompt via GPT-4o-mini. Results can be saved, browsed ("most used" community-wide or "my saved"), copied, regenerated, and edited.

## Repositories

This directory contains two projects that work together:

- **[tru-prompt-frontend/](tru-prompt-frontend/)** — React 18 + Redux Toolkit UI. Originally built at [dev-truperformance/tru-prompt-frontend](https://github.com/dev-truperformance/tru-prompt-frontend) against a backend contract that didn't exist yet.
- **[tru-prompt-backend/](tru-prompt-backend/)** — FastAPI + Supabase (Postgres) service built to match that contract exactly: Microsoft SSO, prompt CRUD, and server-side AI generation.

See [TECHNICAL.md](TECHNICAL.md) for how the two talk to each other (auth flow, API reference, data model) and [TruPrompt-SOW.md](TruPrompt-SOW.md) for the internal scope/roadmap doc.

## Quick start (local dev)

1. **Backend**: follow [tru-prompt-backend/README.md](tru-prompt-backend/README.md) — needs a Supabase project (schema included) and, for real login, an Azure AD app registration. Without Azure AD creds, use the `GET /api/users/auth/dev-login` bypass instead of "Login with Microsoft."
2. **Frontend**: follow [tru-prompt-frontend/README.md](tru-prompt-frontend/README.md) — point `REACT_APP_BACKEND_URL` at wherever the backend is running.
3. Open the frontend in a browser, log in (via SSO or the dev bypass), and use the app.

## Current status

| Piece | Status |
|---|---|
| Frontend UI | Built, functional |
| Backend (auth, prompt CRUD, AI proxy) | Built, verified against a real Supabase project |
| Microsoft SSO | Wired up, needs real Azure AD app registration values to actually log in via SSO |
| AI generation | Wired up, needs a real OpenAI API key |
| Roadmap (tags, favorites, search, versioning, etc.) | Not built — see [TECHNICAL.md](TECHNICAL.md#roadmap) |

## Security note

The frontend originally called OpenAI directly from the browser (exposing the API key to every visitor) and had a second file with a hardcoded, already-leaked Groq API key. Both were removed as part of this build — the OpenAI call now goes through the backend, and the dead file is gone. **Both old keys should still be rotated/revoked**, since they were committed to git history before this fix.
