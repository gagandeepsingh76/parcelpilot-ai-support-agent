"""FastAPI entrypoint.

Step 0: minimal app with health endpoints only. Routers for chat, tools,
insights and auth are added in subsequent steps.
"""

from app import __version__
from app.config import get_settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description=(
        "AI support agent for ParcelPilot: document retrieval, structured-data "
        "tools, confirmation-gated actions, role-scoped access control."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
@app.get("/api/health")
def health() -> dict:
    """Liveness probe used by tests, the UI and the deploy target."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "version": __version__,
    }
