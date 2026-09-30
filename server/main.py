import os
import hashlib
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import edge_tts

app = FastAPI(
    title="TOEIC Studio Audio Microservice",
    description="High-fidelity Azure Neural TTS service tailored for TOEIC learning with disk caching.",
    version="1.0.0"
)

# Enable CORS for all domains so frontend can call from anywhere
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Path to static web app if running as standalone monolithic server
DOCS_DIR = BASE_DIR.parent / "docs"

# Curated list of ETS-like native accents
ETS_VOICES = [
    {
        "id": "en-US-JennyNeural",
        "name": "Jenny (US Female)",
        "accent": "US",
        "gender": "Female",
        "description": "Standard American English - Standard ETS Listening Voice"
    },
    {
        "id": "en-US-GuyNeural",
        "name": "Guy (US Male)",
        "accent": "US",
        "gender": "Male",
        "description": "Standard American English - Deep Natural Male Voice"
    },
    {
        "id": "en-GB-SoniaNeural",
        "name": "Sonia (UK Female)",
        "accent": "UK",
        "gender": "Female",
        "description": "British English - RP Accent common in ETS Part 3 & 4"
    },
    {
        "id": "en-GB-RyanNeural",
        "name": "Ryan (UK Male)",
        "accent": "UK",
        "gender": "Male",
        "description": "British English - Clear Business UK Accent"
    },
    {
        "id": "en-AU-NatashaNeural",
        "name": "Natasha (AU Female)",
        "accent": "AU",
        "gender": "Female",
        "description": "Australian English - Natural Australian Intonation"
    },
    {
        "id": "en-CA-ClaraNeural",
        "name": "Clara (CA Female)",
        "accent": "CA",
        "gender": "Female",
        "description": "Canadian English - Crisp North American Accent"
    }
]

@app.get("/health")
async def health_check():
    cached_files = list(CACHE_DIR.glob("*.mp3"))
    return {
        "status": "healthy",
        "service": "TOEIC Audio Engine",
        "cached_audio_count": len(cached_files),
        "cache_dir": str(CACHE_DIR)
    }

@app.get("/api/voices")
async def get_voices():
    return JSONResponse(content={"voices": ETS_VOICES})

@app.get("/api/tts")
async def text_to_speech(
    text: str = Query(..., min_length=1, max_length=1000, description="English text to synthesize"),
    voice: str = Query("en-US-JennyNeural", description="Voice ID from /api/voices"),
    rate: str = Query("+0%", description="Rate adjustment (e.g. +0%, -15%, +15%)"),
    cache: bool = Query(True, description="Whether to utilize disk cache")
):
    """
    Synthesize high-fidelity MP3 using Microsoft Azure Neural TTS.
    Utilizes MD5 disk cache for instant 0ms responses on repeated requests.
    """
    clean_text = text.strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    # Generate MD5 hash key based on text, voice, and rate
    hash_key = hashlib.md5(f"{clean_text}_{voice}_{rate}".encode("utf-8")).hexdigest()
    cache_file = CACHE_DIR / f"{hash_key}.mp3"

    if cache and cache_file.exists() and cache_file.stat().st_size > 0:
        return FileResponse(
            path=str(cache_file),
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "public, max-age=31536000, immutable",
                "X-Audio-Cache": "HIT"
            }
        )

    try:
        communicate = edge_tts.Communicate(text=clean_text, voice=voice, rate=rate)
        await communicate.save(str(cache_file))
    except Exception as e:
        if cache_file.exists():
            cache_file.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {str(e)}")

    return FileResponse(
        path=str(cache_file),
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "X-Audio-Cache": "MISS"
        }
    )

# Mount docs directory if it exists, allowing all-in-one serving
if DOCS_DIR.exists():
    app.mount("/", StaticFiles(directory=str(DOCS_DIR), html=True), name="static_docs")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
