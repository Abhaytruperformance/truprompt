from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "tru-prompt-backend"
    DEBUG: bool = False

    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # Direct Postgres connection as the restricted `tru_app` role (NOBYPASSRLS)
    # -- used for org-scoped tables so Row Level Security actually enforces
    # something (SUPABASE_SERVICE_ROLE_KEY above bypasses RLS unconditionally,
    # REST or direct, so it can't be used for this). See app/db/pg.py.
    APP_DB_HOST: str = "localhost"
    APP_DB_PORT: int = 5432
    APP_DB_NAME: str = "postgres"
    APP_DB_USER: str = "tru_app"
    APP_DB_PASSWORD: str = "placeholder-app-db-password"

    MS_CLIENT_ID: str
    MS_CLIENT_SECRET: str
    MS_TENANT_ID: str
    MS_REDIRECT_URI: str

    # WorkOS AuthKit -- lets a customer connect their own Okta/Azure AD/Google
    # Workspace as an identity provider for their org. Scaffolded with
    # placeholders; not live until a real WorkOS account exists.
    WORKOS_API_KEY: str = "placeholder-workos-api-key"
    WORKOS_CLIENT_ID: str = "placeholder-workos-client-id"
    WORKOS_REDIRECT_URI: str = "http://localhost:8000/api/orgs/sso/callback"

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 days

    OPENAI_API_KEY: str = "placeholder-openai-key"

    # OpenRouter (openrouter.ai) -- OpenAI-compatible API covering many providers,
    # including free-tier models. Useful for testing generation without paying
    # for OpenAI; swap back by clearing OPENROUTER_API_KEY once ready for
    # production models (see Phase 2 "Block 6" in the project plan for the
    # long-term multi-model plan this anticipates).
    # NOTE: OpenRouter's free-model catalog changes over time -- if this model
    # 404s as "unavailable for free", check https://openrouter.ai/models?max_price=0
    # for a current one.
    OPENROUTER_API_KEY: str = "placeholder-openrouter-api-key"
    OPENROUTER_MODEL: str = "openai/gpt-oss-20b:free"
    # Used only if OPENROUTER_MODEL gets rate-limited upstream (free-tier
    # models share a provider-side quota, not a per-user one) -- a different
    # free model on a separate quota keeps generation working either way.
    OPENROUTER_FALLBACK_MODEL: str = "openai/gpt-oss-20b:free"
    OPENROUTER_FALLBACK_MODELS: str = "openrouter/free"
    # Curated model picker (multi-model/Playground) -- comma-separated, same
    # pattern as CORS_ORIGINS below. Deliberately not "every OpenRouter model"
    # -- a short, curated list matches this product's "focused tool" positioning
    # (see PROJECT-PLAN.md). Empty by default: falls back to the two models
    # already configured and proven working above.
    OPENROUTER_AVAILABLE_MODELS: str = ""

    @property
    def use_openrouter(self) -> bool:
        return not self.OPENROUTER_API_KEY.startswith("placeholder-")

    @property
    def openrouter_available_models_list(self) -> list[str]:
        if self.OPENROUTER_AVAILABLE_MODELS.strip():
            return [m.strip() for m in self.OPENROUTER_AVAILABLE_MODELS.split(",") if m.strip()]
        return list(dict.fromkeys([self.OPENROUTER_MODEL, *self.openrouter_fallback_models_list]))

    @property
    def openrouter_fallback_models_list(self) -> list[str]:
        configured = [m.strip() for m in self.OPENROUTER_FALLBACK_MODELS.split(",") if m.strip()]
        return list(dict.fromkeys([*configured, self.OPENROUTER_FALLBACK_MODEL]))

    # Resend (resend.com) -- sends invitation emails. Placeholder until a real
    # API key exists; send_invitation_email() logs instead of sending while it is.
    RESEND_API_KEY: str = "placeholder-resend-api-key"
    EMAIL_FROM: str = "TruPrompt <onboarding@resend.dev>"

    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"
    CORS_ORIGINS: str = ""

    # Content input (doc/URL as generation context) -- all bound the cost/risk
    # of accepting arbitrary user-supplied files and URLs.
    MAX_UPLOAD_SIZE_MB: int = 5
    URL_FETCH_TIMEOUT_SECONDS: float = 10.0
    MAX_URL_RESPONSE_BYTES: int = 2 * 1024 * 1024  # 2MB
    MAX_CONTEXT_CHARS: int = 8000  # bounds cost/context-window use per generation
    URL_CACHE_TTL_SECONDS: int = 900  # re-fetching the same URL repeatedly (Playground re-runs, retries) is wasted latency + risk for content that rarely changes minute to minute

    # Per-API-key rate limiting (public REST API + MCP, both funnel through
    # app/auth/api_key.py's resolve_api_key_org) -- guards against a leaked or
    # malicious key hammering the LLM-backed generate endpoint unmetered.
    API_KEY_RATE_LIMIT_PER_MINUTE: int = 60
    API_KEY_RATE_LIMIT_WINDOW_SECONDS: int = 60

    # A share creator picking a generation limit shouldn't be able to set an
    # effectively-unlimited number (e.g. accidentally or maliciously) and
    # call it a "limit" -- bounds anonymous public-share LLM spend.
    MAX_SHARE_GENERATION_LIMIT: int = 1000
    # Applied when a share is created without specifying a limit -- unlimited
    # anonymous generation must be something an admin explicitly opts into
    # (an explicit null), not the effortless default for leaving a field blank.
    DEFAULT_SHARE_GENERATION_LIMIT: int = 20

    @property
    def cors_origins_list(self) -> list[str]:
        if self.CORS_ORIGINS.strip():
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return [self.FRONTEND_URL]

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
