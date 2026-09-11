# Statement of Work: TruPrompt

**Product:** TruPrompt
**Owning org:** truperformance
**Document type:** Internal Statement of Work (planning/alignment document)
**Status:** Draft
**Date:** 2026-07-16

> This is an internal planning document. truperformance is building TruPrompt for its own internal use — there is no external client and no separate contracting party. Accordingly, this SOW omits legal boilerplate, liability/indemnification clauses, and signature blocks that would appear in a client-facing contract. Its purpose is to align the team on what is in scope now, what's deferred, and how we'll know Phase 1 is done.

---

## 1. Project Overview

TruPrompt is an internal AI prompt-generation tool. A logged-in user describes a rough idea, picks one or more "expert" categories (SEO, Design, Communication, Web Development, Lead Generation, Lifecycle Marketing, Business Development), and the app calls GPT-4o-mini to turn that rough idea into a polished, reusable prompt — returning both an "optimizer" (bullet-point context) and the final prompt text. Users can save results, browse prompts by "most used" (community-wide) or "my saved" (per-user), copy a prompt (incrementing a usage counter), regenerate, and edit.

This SOW exists to align the team on scope across the *whole* product — not just the backend work currently in flight — so everyone is working from the same picture of what's being built now, what's explicitly deferred, and what "done" looks like for the current phase.

---

## 2. Background / Problem Statement

The `tru-prompt-frontend` app (React 18 + Redux Toolkit/RTK Query + Bootstrap) was built and is functional, but it was built against a backend contract that never actually existed. In place of a real backend, it called OpenAI directly from the browser — which is a real security problem, since it required embedding an OpenAI API key in client-side code, exposing that key to every visitor. A hardcoded/leaked key was found in this path, and a second, unused/dead file also contained a leaked Groq API key.

`tru-prompt-backend` is being built now to give the frontend a real, secure backend: a FastAPI + Supabase (Postgres) service that handles authentication, prompt storage, and moves the OpenAI call server-side so no provider API key is ever shipped to the browser.

---

## 3. Scope of Work

### Phase 1 — Current (in progress)

Phase 1 delivers a working backend for TruPrompt and closes the client-side API key exposure. Deliverables and their acceptance criteria:

| # | Deliverable | Acceptance Criteria |
|---|---|---|
| 1 | Microsoft SSO login (Azure AD OAuth via MSAL) | User can log in via Microsoft SSO; a session is established via an httpOnly JWT cookie; the session persists across a page reload without re-authenticating. |
| 2 | Session/auth handling | Unauthenticated requests to protected endpoints are rejected; the cookie is httpOnly (not readable via JS) and scoped appropriately. |
| 3 | Users table (Supabase/Postgres) | On first login, a user row is created/updated with `microsoft_oid`, `name`, `email`, `role`, `profile_image`, and timestamps; repeat logins map to the same user record. |
| 4 | Prompts table (Supabase/Postgres) | Table exists with `id`, `user_id`, `category`, `user_prompt`, `prompt`, `optimizer`, `most_used_prompt_count`, and timestamps, with `user_id` referencing the owning user. |
| 5 | List all prompts (community/most-used) | Endpoint returns prompts across all users, orderable/viewable by usage count, matching the frontend's "Most Used" view. |
| 6 | List current user's saved prompts | Endpoint returns only the authenticated user's prompts, matching the frontend's "My Saved" view. |
| 7 | Create/save a prompt | A newly saved prompt appears in the creating user's "My Saved Prompts" and is retrievable by its id immediately after creation. |
| 8 | Get single prompt by id | Endpoint returns a single prompt's full record (category, user_prompt, prompt, optimizer, usage count) given its id. |
| 9 | Increment usage count on copy | Copying a prompt increments `most_used_prompt_count` server-side; the updated count is reflected on next fetch. |
| 10 | Update/edit a prompt (with ownership check) | A user can edit their own prompt; a request to edit a prompt owned by another user is rejected. |
| 11 | `POST /api/ai/generate-prompt` endpoint | Given a rough idea + category selection(s), the endpoint calls OpenAI (GPT-4o-mini) server-side and returns an `optimizer` + `prompt` payload matching what the frontend expects. |
| 12 | Frontend `openAIUtils.js` update | Frontend calls the new backend endpoint instead of instantiating the OpenAI SDK client-side. |
| 13 | Removal of leaked API keys | The hardcoded/leaked OpenAI key and the dead file containing the leaked Groq key are removed from the frontend codebase and confirmed absent from any built/bundled output and from current source control. |

### Phase 2+ — Roadmap (not yet scoped or estimated)

The following are backlog ideas for future phases, not commitments, and have no estimates or dates attached. They are grouped by rough priority horizon and will need their own scoping (including frontend UI work, in most cases) before being committed to a SOW or sprint.

**Near-term**
- AI provider abstraction (swap OpenAI for Claude / Gemini / Groq / OpenRouter without rewriting the generation endpoint)
- Prompt versioning (preserve edit history instead of overwriting)
- Tags (in addition to existing category field)
- Favorites
- Soft delete (instead of hard delete)
- Pagination on list endpoints

**Mid-term**
- Dedicated search endpoint (keyword / category / tag / owner)
- Richer usage analytics (views, copies, favorites, runs, last-used, average rating — beyond today's single usage counter)
- Rate limiting on the AI generation endpoint
- Structured request logging (request id, user id, execution time, tokens, cost)
- Prompt templates (e.g., SEO Blog, Landing Page, Cold Email, Code Review, PRD)

**Long-term / enterprise**
- Admin dashboard and routes (`/admin/users`, `/admin/prompts`, `/admin/stats`, `/admin/ai-cost`)
- Org/team support with role-based access control (RBAC)

---

## 4. Out of Scope (for Phase 1)

Phase 1 explicitly does **not** include any of the following. Each would require frontend UI work in addition to backend work, and all are deferred to Phase 2+ per the roadmap above:

- Tags
- Favorites
- Prompt versioning / edit history
- Search (dedicated search endpoint)
- Pagination on list endpoints
- Rate limiting on AI generation
- Structured request/cost logging
- Prompt templates
- Admin dashboard/routes
- Multi-tenant org/team support and RBAC

---

## 5. Deliverables (Phase 1)

1. **FastAPI backend service** (`tru-prompt-backend`) implementing Microsoft SSO auth, prompt CRUD, usage-count increment, and the AI generation endpoint.
2. **Supabase/Postgres schema** — Users table and Prompts table as described in Section 3.
3. **Updated frontend** — `openAIUtils.js` modified to call the backend's `/api/ai/generate-prompt` endpoint; dead file with the leaked Groq key deleted; leaked OpenAI key removed.
4. **README** documenting local setup (environment variables, running the backend, connecting to Supabase) and capturing the Phase 2+ roadmap backlog for future reference.

---

## 6. Assumptions / Dependencies

- truperformance already has an Azure AD app registration (client id, client secret, tenant id) available for MSAL/OAuth integration.
- truperformance will provision a Supabase project (Postgres instance + connection credentials) for this service.
- Both of the above are supplied outside of this document — via a local `.env` file — and are never committed to source control.
- No third-party contractor or external vendor is involved; all work is performed by the internal team.

---

## 7. Milestones / Timeline

No firm calendar dates are set at this time. Timeline is intentionally loose and will be refined as Phase 1 nears completion:

- **Phase 1 — In progress.** Backend build (auth, prompt CRUD, AI generation endpoint) and corresponding frontend fix, per Section 3.
- **Phase 1 sign-off** — once acceptance criteria in Section 9 are met.
- **Phase 2 — To be scheduled after Phase 1 ships.** Backlog items to be triaged, estimated, and formally scoped (likely as a follow-on SOW or set of tickets) once Phase 1 is stable in use.

---

## 8. Pricing / Payment Terms

_[Internal project — no billing arrangement; delete this section or fill in cost/time tracking as needed.]_

---

## 9. Acceptance Criteria (Phase 1 Sign-Off Checklist)

- [ ] User can log in via Microsoft SSO; session cookie persists across page reload.
- [ ] User record is created/updated in Supabase on login with expected fields.
- [ ] A saved prompt appears in "My Saved Prompts" and is retrievable by id.
- [ ] "Most Used" view returns community-wide prompts, independent of the requesting user.
- [ ] Copying a prompt increments its usage counter, reflected on next fetch.
- [ ] Editing a prompt succeeds for its owner and is rejected for non-owners.
- [ ] `POST /api/ai/generate-prompt` returns a valid `optimizer` + `prompt` payload from the backend.
- [ ] Frontend generates prompts via the backend endpoint, not a client-side OpenAI SDK call.
- [ ] No OpenAI or Groq API key is present in any frontend bundle, build artifact, or committed file.
- [ ] README documents setup steps and lists the Phase 2+ roadmap backlog.
