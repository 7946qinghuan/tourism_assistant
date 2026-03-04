import uvicorn

from app.backend.core.config import Settings

if __name__ == "__main__":
    settings = Settings()
    uvicorn.run(
        "app.backend.main:app",
        host=settings.TOURISM_HOST,
        port=settings.TOURISM_PORT,
        # reload=True,
    )
