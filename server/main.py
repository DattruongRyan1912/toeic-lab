import asyncio
import hashlib
import logging
import os
import re
import uuid
from contextlib import asynccontextmanager, suppress
from pathlib import Path

import edge_tts
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from server import config
from server.database import SessionLocal, engine, init_db
from server.routers import (
    ai_agent_router,
    auth_router,
    dashboard_router,
    error_log_router,
    flashcard_router,
    knowledge_router,
    learner_router,
    listening_router,
    plan_router,
    practice_router,
    reminder_router,
    roadmap_router,
    test_router,
    user_router,
)
from server.services import ai_agent_service, insights, maintenance, reminder_service

logger = logging.getLogger("toeic")

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR = BASE_DIR.parent / "docs"

# Curated ETS-like native accents (single source of truth for the web settings page)
ETS_VOICES = [
    {"id": "en-US-JennyNeural", "name": "Jenny (US Female)", "accent": "US", "gender": "Female",
     "description": "Standard American English - Standard ETS Listening Voice"},
    {"id": "en-US-GuyNeural", "name": "Guy (US Male)", "accent": "US", "gender": "Male",
     "description": "Standard American English - Deep Natural Male Voice"},
    {"id": "en-GB-SoniaNeural", "name": "Sonia (UK Female)", "accent": "UK", "gender": "Female",
     "description": "British English - RP Accent common in ETS Part 3 & 4"},
    {"id": "en-GB-RyanNeural", "name": "Ryan (UK Male)", "accent": "UK", "gender": "Male",
     "description": "British English - Clear Business UK Accent"},
    {"id": "en-AU-NatashaNeural", "name": "Natasha (AU Female)", "accent": "AU", "gender": "Female",
     "description": "Australian English - Natural Australian Intonation"},
    {"id": "en-CA-ClaraNeural", "name": "Clara (CA Female)", "accent": "CA", "gender": "Female",
     "description": "Canadian English - Crisp North American Accent"},
]
VOICE_IDS = {voice["id"] for voice in ETS_VOICES}
VOICE_ALIASES = {
    "en-AU-WilliamNeural": "en-AU-NatashaNeural",
    "en-AU-WilliamMultilingualNeural": "en-AU-NatashaNeural",
    "en-CA-LiamNeural": "en-CA-ClaraNeural",
}
RATE_RE = re.compile(r"^[+-](?:[0-9]|[1-4][0-9]|50)%$")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with SessionLocal() as db:
        insights.get_or_create_user(db, config.DEFAULT_USER_ID)
        maintenance.run(db)
    stop = asyncio.Event()
    task = asyncio.create_task(reminder_service.reminder_loop(stop)) if reminder_service.dispatch_enabled() else None
    yield
    stop.set()
    if task is not None:
        with suppress(asyncio.TimeoutError, asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=5)


app = FastAPI(
    title="TOEIC Lab Full-Stack Platform API",
    description="SRS SM-2, mock tests with RCA error log, learning gaps, AI mentor (function calling) and Edge TTS.",
    version=config.APP_VERSION,
    lifespan=lifespan,
)

# No cookies/credentials are used, so credentials stay disabled and only listed origins are allowed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

for module in (
    auth_router,
    dashboard_router,
    user_router,
    roadmap_router,
    flashcard_router,
    error_log_router,
    knowledge_router,
    test_router,
    practice_router,
    plan_router,
    learner_router,
    listening_router,
    reminder_router,
    ai_agent_router,
):
    app.include_router(module.router)


def _health_payload() -> dict:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        logger.exception("Database health check failed")
        database = "error"
    return {
        "status": "healthy" if database == "ok" else "degraded",
        "service": "TOEIC Lab Full-Stack Engine",
        "version": config.APP_VERSION,
        "database": database,
        "ai": ai_agent_service.provider_status(),
        "telegram_configured": reminder_service.telegram_configured(),
        "cached_audio_count": sum(1 for _ in CACHE_DIR.glob("*.mp3")),
    }


@app.get("/health", include_in_schema=False)
async def health_check():
    """Used by the Docker healthcheck and the legacy UI."""
    return _health_payload()


@app.get("/api/health", tags=["System"])
async def api_health():
    """Same payload under /api so the Next.js BFF proxy can reach it."""
    return _health_payload()


@app.get("/api/voices", tags=["Audio"])
async def get_voices():
    return {"voices": ETS_VOICES}


@app.get("/api/tts", tags=["Audio"])
async def text_to_speech(
    text: str = Query(..., min_length=1, max_length=1000, description="English text to synthesize"),
    voice: str = Query("en-US-JennyNeural", description="Voice ID from /api/voices"),
    rate: str = Query("+0%", description="Rate adjustment, -50% .. +50%"),
    cache: bool = Query(True, description="Use the disk cache"),
):
    clean_text = text.strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    voice = VOICE_ALIASES.get(voice, voice)
    if voice not in VOICE_IDS:
        raise HTTPException(status_code=422, detail=f"Unknown voice '{voice}'. See /api/voices")

    # Normalize rate: handle unencoded '+' arriving as space, or missing leading sign (e.g. '0%', '10%')
    rate_clean = rate.strip()
    if rate_clean.startswith(" "):
        rate_clean = "+" + rate_clean.lstrip()
    if rate_clean and not rate_clean.startswith(("+", "-")):
        rate_clean = "+" + rate_clean

    if not RATE_RE.match(rate_clean):
        raise HTTPException(status_code=422, detail="Rate must look like +0%, -15% or +15% (max ±50%)")
    rate = rate_clean

    cache_file = CACHE_DIR / f"{hashlib.md5(f'{clean_text}_{voice}_{rate}'.encode('utf-8')).hexdigest()}.mp3"
    headers = {"Cache-Control": "public, max-age=31536000, immutable"}
    if cache and cache_file.exists() and cache_file.stat().st_size > 0:
        return FileResponse(path=str(cache_file), media_type="audio/mpeg", headers={**headers, "X-Audio-Cache": "HIT"})

    tmp_file = cache_file.with_suffix(f".{uuid.uuid4().hex}.tmp")
    try:
        await edge_tts.Communicate(text=clean_text, voice=voice, rate=rate).save(str(tmp_file))
        os.replace(tmp_file, cache_file)  # atomic: concurrent requests never read a half-written file
    except Exception as exc:
        tmp_file.unlink(missing_ok=True)
        logger.warning("TTS synthesis failed: %s", exc)
        raise HTTPException(status_code=502, detail="TTS synthesis failed (Edge TTS unreachable)")
    return FileResponse(path=str(cache_file), media_type="audio/mpeg", headers={**headers, "X-Audio-Cache": "MISS"})


LEGACY_ACTIVE = config.LEGACY_UI_ENABLED and DOCS_DIR.exists()


@app.get("/", include_in_schema=False)
async def service_index():
    # Deployments that point a domain straight at this API used to show the HTML UI on "/": keep that working.
    if LEGACY_ACTIVE:
        return RedirectResponse(url="/legacy/", status_code=307)
    return {
        "service": "TOEIC Lab API",
        "version": config.APP_VERSION,
        "docs": "/docs",
        "health": "/api/health",
        "web_app": config.WEB_APP_URL,
    }


if LEGACY_ACTIVE:

    @app.get("/{page_name}.html", include_in_schema=False)
    async def legacy_page_redirect(page_name: str):
        """Old bookmarks (/toeic_study_guide.html) keep working after the legacy UI moved to /legacy."""
        if (DOCS_DIR / f"{page_name}.html").is_file():
            return RedirectResponse(url=f"/legacy/{page_name}.html", status_code=307)
        raise HTTPException(status_code=404, detail="Not Found")

    # Standalone HTML UI (docs/). It calls /api/* relative to the origin, so it keeps working here.
    app.mount("/legacy", StaticFiles(directory=str(DOCS_DIR), html=True), name="legacy_ui")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server.main:app", host="0.0.0.0", port=config.PORT, reload=config.DEBUG)
