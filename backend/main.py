"""
SkillSpark AI — FastAPI Application Entry Point
----------------------------------------------------
Wires together all routers, middleware, and startup events.

Endpoints:
  GET  /                    → welcome message
  GET  /health              → health check
  POST /api/v1/upload       → file upload + parse
  POST /api/v1/analyse      → gap analysis pipeline
  POST /api/v1/pathway      → pathway generation
  POST /api/v1/reroute      → skip skill + recalculate
  POST /api/v1/complete     → mark skill complete

Run locally:
  cd backend
  uvicorn main:app --reload --port 8000
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ai.claude_client import check_claude_health
from api.routes.upload import router as upload_router
from api.routes.analyse import router as analyse_router
from api.routes.pathway import router as pathway_router
from api.routes.reroute import router as reroute_router
from nlp.extractor import get_extractor
from nlp.normaliser import get_normaliser
from utils.catalog import load_catalog
from utils.logger import get_logger

# Load environment variables
load_dotenv()

logger = get_logger(__name__)


# ── Startup + shutdown ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup and shutdown.

    Startup:
      - Load spaCy model
      - Load Sentence Transformer
      - Load catalog + taxonomies
      - Check Claude API health

    Shutdown:
      - Clean up resources
    """
    # ── STARTUP ──────────────────────────────────────────────────
    logger.info("SkillSpark AI starting up...")

    # Load catalog (cached)
    try:
        catalog = load_catalog()
        logger.info(
            f"Catalog loaded: {len(catalog)} skills"
        )
    except Exception as e:
        logger.error(f"Catalog load failed: {e}")

    # Load spaCy extractor (heavy — load once)
    try:
        logger.info("Loading spaCy model...")
        extractor = get_extractor()
        logger.info("spaCy model loaded")
    except Exception as e:
        logger.error(f"spaCy load failed: {e}")

    # Load Sentence Transformer (heavy — load once)
    try:
        logger.info("Loading Sentence Transformer...")
        normaliser = get_normaliser()
        logger.info("Sentence Transformer loaded")
    except Exception as e:
        logger.error(f"Sentence Transformer load failed: {e}")

    # Check Claude API
    try:
        claude_health = check_claude_health()
        logger.info(
            f"Claude API: {claude_health['status']} "
            f"({claude_health['model']})"
        )
    except Exception as e:
        logger.warning(
            f"Claude API check failed — "
            f"fallback mode will be used: {e}"
        )

    logger.info("SkillSpark AI ready!")

    yield  # App runs here

    # ── SHUTDOWN ─────────────────────────────────────────────────
    logger.info("SkillSpark AI shutting down...")


# ── App creation ──────────────────────────────────────────────────

app = FastAPI(
    title="SkillSpark AI API",
    description=(
        "AI-powered adaptive onboarding engine. "
        "Diagnoses skill gaps and generates personalised "
        "learning pathways for job readiness."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── CORS middleware ───────────────────────────────────────────────
# Allows React frontend to call the API

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",    # React dev server
        "http://localhost:5173",    # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────

API_PREFIX = "/api/v1"

app.include_router(
    upload_router,
    prefix=API_PREFIX,
    tags=["Upload"],
)
app.include_router(
    analyse_router,
    prefix=API_PREFIX,
    tags=["Analysis"],
)
app.include_router(
    pathway_router,
    prefix=API_PREFIX,
    tags=["Pathway"],
)
app.include_router(
    reroute_router,
    prefix=API_PREFIX,
    tags=["Reroute"],
)


# ── Root endpoint ─────────────────────────────────────────────────

@app.get("/", tags=["Root"])
async def root() -> JSONResponse:
    """Welcome message and API info."""
    return JSONResponse(
        content={
            "app":         "SkillSpark AI",
            "version":     "1.0.0",
            "status":      "running",
            "docs":        "/docs",
            "endpoints": {
                "upload":   "/api/v1/upload",
                "analyse":  "/api/v1/analyse",
                "pathway":  "/api/v1/pathway",
                "reroute":  "/api/v1/reroute",
                "complete": "/api/v1/complete",
            },
        }
    )


# ── Health check ──────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health() -> JSONResponse:
    """
    Full health check.
    Checks catalog, models, and Claude API.
    """
    health_status = {
        "status":      "healthy",
        "app_name":    "SkillSpark AI",
        "version":     "1.0.0",
        "claude":      "unknown",
        "catalog":     "unknown",
        "spacy":       "unknown",
        "transformer": "unknown",
    }

    # Check catalog
    try:
        catalog = load_catalog()
        health_status["catalog"] = (
            f"ok — {len(catalog)} skills"
        )
    except Exception as e:
        health_status["catalog"] = f"error: {e}"
        health_status["status"]  = "degraded"

    # Check spaCy
    try:
        get_extractor()
        health_status["spacy"] = "ok"
    except Exception as e:
        health_status["spacy"]  = f"error: {e}"
        health_status["status"] = "degraded"

    # Check Sentence Transformer
    try:
        get_normaliser()
        health_status["transformer"] = "ok"
    except Exception as e:
        health_status["transformer"] = f"error: {e}"
        health_status["status"]      = "degraded"

    # Check Claude
    try:
        claude_result = check_claude_health()
        health_status["claude"] = claude_result["status"]
        if claude_result["status"] != "healthy":
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["claude"]  = f"error: {e}"
        health_status["status"]  = "degraded"

    status_code = (
        200 if health_status["status"] == "healthy"
        else 207
    )

    return JSONResponse(
        status_code=status_code,
        content=health_status,
    )


# ── Run directly ──────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("BACKEND_PORT", 8000))

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )