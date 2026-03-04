from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.backend.api.v1 import map_router, trip_router
from app.backend.core.config import Settings
from app.backend.core.lifespan import lifespan

settings = Settings()

app = FastAPI(
    title="Tourism Assistant API",
    description="An API for planning trips using AI agents.",
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health Check"])
async def root(request: Request):
    settings = request.app.state.settings
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }


app.include_router(trip_router, prefix="/api/v1")
app.include_router(map_router, prefix="/api/v1")
