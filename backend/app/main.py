import contextlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.mcp_server import mcp_app
from app.routers import (
    ai,
    api_keys,
    custom_fields,
    departments,
    orgs,
    prompts,
    public_api,
    public_shares,
    tags,
    users,
)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # A mounted sub-app's own lifespan (mcp_app's session-manager task group)
    # isn't started automatically by FastAPI/Starlette's Mount -- it has to be
    # entered explicitly here, or every /mcp request 500s with "Task group is
    # not initialized".
    async with mcp_app.router.lifespan_context(mcp_app):
        yield


app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(prompts.router, prefix="/api/prompts", tags=["prompts"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(orgs.router, prefix="/api/orgs", tags=["orgs"])
app.include_router(departments.router, prefix="/api/departments", tags=["departments"])
app.include_router(custom_fields.router, prefix="/api/custom-fields", tags=["custom-fields"])
app.include_router(tags.router, prefix="/api/tags", tags=["tags"])
app.include_router(public_shares.router, prefix="/api/public", tags=["public"])
app.include_router(api_keys.router, prefix="/api/api-keys", tags=["api-keys"])
app.include_router(public_api.router, prefix="/v1", tags=["public-api-v1"])
app.mount("/mcp", mcp_app)


@app.get("/")
def root():
    return {"message": f"Welcome to {settings.APP_NAME}"}
