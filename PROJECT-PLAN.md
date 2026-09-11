# TruPrompt — Project Plan

Single consolidated plan from discovery (benchmarked against [promptitude.io](https://www.promptitude.io/) and the wider prompt-management market). Decision locked: **build the focused prompt-management product first — not Promptitude's full Assistants/Flows/Tools agent-platform surface.** Faster to a sellable product, matches what's already 80% built, and doesn't bet engineering time on agentic features nobody's asked for yet.

## Phase 1 — Prompt Management, working end to end

This is what ships first. Already built (Phase 0): generate, save, browse ("most used"/"my saved"), edit, Microsoft SSO login. To reach real parity as a sellable product, Phase 1 adds:

- **Organization**: tags + folders, replacing the current free-text `category`
- **Versioning**: edit creates a new version instead of overwriting; view history
- **Sharing**: a public link per prompt, optionally password-protected, with a per-visitor generation limit — an embeddable widget is a fast-follow, not required for v1
- **Public API**: API keys + a documented REST endpoint so a customer can integrate a prompt into their own app in "one call," same pitch as Promptitude's
- **Multi-tenancy (required, not optional)**: since this is going to external customers, every prompt/user has to belong to an organization from day one, with data isolation enforced at the DB layer. This isn't a separate initiative — it's the thing that makes everything above actually sellable to a second company. The hard part of this (letting each customer bring their own Okta/Azure AD) is one integration, not a build — see Build vs. Buy below.

**Phase 1 is done when**: a customer org can sign up, invite teammates, tag/organize/version their prompts, share one publicly, and call one via API — all fully isolated from any other org's data.

## Phase 2 — Everything else (future scope, sequenced after Phase 1 ships)

1. **Multi-model**: OpenRouter integration (one API, covers OpenAI/Anthropic/Google/Meta/Mistral/etc.) + a playground UI to compare outputs before saving
2. **Content input**: let a prompt take an uploaded doc or scraped URL as context, not just typed text
3. **Analytics**: per-prompt usage/rating beyond the raw counter, org-level usage/cost dashboard (Langfuse is a build-vs-buy candidate here, not yet verified in depth)
4. **MCP / Claude custom connector**: can run in parallel with any of the above once Phase 1's multi-tenancy lands — the connector needs to know which org's prompts a given Claude connection can see, so it depends on org-scoped data existing, not on Phase 2's other items
5. **Explicitly not planned**: Assistants/Flows/Tools (agentic layer), prompt A/B testing, a prompt marketplace — these are what would make TruPrompt "Promptitude, fully matched." Revisit only if real customers ask for it; don't pre-build it.

## Competitive landscape — and how TruPrompt wins

| Competitor | Positioning | Where they're strong | Where TruPrompt can beat them |
|---|---|---|---|
| **Promptitude** | No-code, business-user friendly, agent-platform ambitions | Broad feature surface (Assistants/Flows/Tools), 8 model providers, mature | Broad = unfocused. We win on being simpler and faster to adopt for teams that just want great prompts, not a whole agent builder they didn't ask for |
| **PromptLayer** | Dev-tool, "collaboration layer for AI engineering teams" — CMS + eval + observability | Strong with engineering teams already deep in AI-native workflows | Positioned at developers, not the marketers/ops teams who actually write most prompts day to day (which is TruPrompt's current user base already — SEO/Design/Marketing categories) |
| **Langfuse & similar observability tools** | Open-source, dev-first, strong on logging/tracing/eval | Excellent instrumentation, weak on being a place non-engineers write and manage prompts | We're the front-end business users actually touch; they're plumbing we could integrate with, not compete against |

**The actual differentiator, regardless of competitor**: none of them can pre-load *your* company's approved templates, house style, and category-specific rules — that's proprietary to whoever runs the product. For TruPrompt specifically, that means an "approved" status on prompts (a curated, reviewed library per org) is worth more than matching any competitor's feature count. A generic prompt tool is a commodity; a company's own vetted prompt library is not. Lead with that in any sales conversation, not a feature checklist against Promptitude.

## Build vs. buy — don't build what's already solved

- **Per-org SSO → [WorkOS](https://workos.com/)**: each customer connects their own Okta/Azure AD/Google Workspace through one unified API instead of us maintaining per-provider OAuth code. First 1M MAUs free on their bundled AuthKit; SSO connections from $125 down to $50/mo at volume.
- **Multi-model (Phase 2) → [OpenRouter](https://openrouter.ai/)**: one OpenAI-SDK-compatible API covering 400+ models/70+ providers, credit-based pricing, no subscription.
- **Analytics (Phase 2) → [Langfuse](https://langfuse.com/)** is a lead worth validating, not yet verified as thoroughly as the two above.
- **Billing → Stripe Billing**, industry default; decision needed is seat- vs. usage-based, not which platform.

## Open questions — still need your manager's call

- Pricing model (seat-based, usage-based, or a tiered ladder like Promptitude's $43/$99/$309/custom)
- Timeline/budget for Phase 1's multi-tenancy piece — real re-architecture even with WorkOS absorbing the SSO integration
- Do existing users' data migrate into a first org, or does the product relaunch clean?
- Confirm the scope call above (focused prompt tool, not the full agent-platform surface) is actually agreed, not just assumed
