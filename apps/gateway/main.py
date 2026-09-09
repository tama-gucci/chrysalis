from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import config
from routers.orchestrator import router as orchestrator_router

app = FastAPI(
    title="Ambient Chrysalis Gateway",
    description="Lightweight at-home daemon bridging Chrysalis Mobile to Google Antigravity.",
    version=config.VERSION,
)

# Enable CORS for cross-origin mobile and web requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(orchestrator_router)


@app.get("/health")
async def health_check():
    """Liveness probe for Cloudflare Tunnel and orchestrator monitoring."""
    return {
        "status": "healthy",
        "service": "ambient-chrysalis-gateway",
        "version": config.VERSION,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
    )
