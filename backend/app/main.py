"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

# Create FastAPI app
app = FastAPI(
    title="AI Lecturer System API",
    description="Autonomous AI lecturer for slide-based instructional material",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "service": "AI Lecturer System",
        "version": "0.1.0",
        "ai_provider": settings.ai_provider,
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "ai_provider": settings.ai_provider,
        "max_file_size_mb": settings.max_file_size_mb,
    }


# TODO: Include routers when implemented
# from app.api import upload, session, narration, stream
# app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
# app.include_router(session.router, prefix="/api/v1", tags=["session"])
# app.include_router(narration.router, prefix="/api/v1", tags=["narration"])
# app.include_router(stream.router, prefix="/api/v1", tags=["stream"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
