#!/usr/bin/env python3
"""
FastAPI server for AI Lecturer system.
"""
import os
import asyncio
import uuid
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timedelta
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import json
from app.config import settings

# Session storage directory
SESSIONS_DIR = Path("backend/sessions")
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

# In-memory session storage (loaded from disk on startup)
sessions: Dict[str, Dict[str, Any]] = {}


def save_session(session_id: str):
    """Save a session to disk."""
    session_file = SESSIONS_DIR / f"{session_id}.json"
    session_data = sessions[session_id].copy()

    # Convert Path objects to strings for JSON serialization
    if "temp_file" in session_data:
        session_data["temp_file"] = str(session_data["temp_file"])

    with open(session_file, "w") as f:
        json.dump(session_data, f, indent=2, default=str)


def load_sessions():
    """Load all sessions from disk on startup."""
    for session_file in SESSIONS_DIR.glob("*.json"):
        try:
            with open(session_file, "r") as f:
                session_data = json.load(f)
                session_id = session_data["id"]
                sessions[session_id] = session_data
        except Exception as e:
            print(f"Error loading session {session_file}: {e}")

# Rate limiting storage: {ip_address: [timestamp1, timestamp2, ...]}
rate_limit_storage: Dict[str, list] = {}

app = FastAPI(title="AI Lecturer API")

# Add CORS middleware
# Allow both local development and production URLs
allowed_origins = [
    "http://localhost:3000",  # Local development
    "https://lectura-b14z.vercel.app",  # Vercel deployment
    "https://lectura.ink",  # Custom domain
    "http://lectura.ink",   # HTTP version
]

# Add custom frontend URL from settings if set
if settings.frontend_url and settings.frontend_url not in allowed_origins:
    allowed_origins.append(settings.frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",  # Allow all Vercel deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Load sessions from disk on startup."""
    print("Loading sessions from disk...")
    load_sessions()
    print(f"Loaded {len(sessions)} sessions")


def check_rate_limit(ip: str, max_requests: int = 5, window_hours: int = 24) -> bool:
    """
    Check if an IP address has exceeded the rate limit.

    Args:
        ip: IP address to check
        max_requests: Maximum number of requests allowed in the time window
        window_hours: Time window in hours

    Returns:
        True if within limit, False if exceeded
    """
    now = datetime.now()
    cutoff_time = now - timedelta(hours=window_hours)

    # Clean up old entries for this IP
    if ip in rate_limit_storage:
        rate_limit_storage[ip] = [
            timestamp for timestamp in rate_limit_storage[ip]
            if timestamp > cutoff_time
        ]
    else:
        rate_limit_storage[ip] = []

    # Check if over limit
    if len(rate_limit_storage[ip]) >= max_requests:
        return False

    # Add current request
    rate_limit_storage[ip].append(now)
    return True


@app.post("/api/v1/upload")
async def upload_file(request: Request, file: UploadFile = File(...), enable_vision: bool = False, tts_provider: str = "edge"):
    """Upload a PDF or PPTX file and start processing.

    Args:
        request: FastAPI request object (to get client IP)
        file: The PDF or PPTX file to process
        enable_vision: Whether to enable vision analysis for diagrams/tables (default: False)
        tts_provider: TTS provider (currently only "edge" supported)
    """
    # Get client IP
    client_ip = request.client.host

    # Check rate limit (5 lectures per 24 hours)
    if not check_rate_limit(client_ip, max_requests=5, window_hours=24):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. You can process up to 5 lectures per day. Please try again later."
        )
    # Validate file type
    if not (file.filename.endswith('.pdf') or file.filename.endswith('.pptx')):
        raise HTTPException(status_code=400, detail="Only PDF and PPTX files are supported")

    # Create session
    session_id = str(uuid.uuid4())
    temp_file = Path(f"/tmp/{session_id}_{file.filename}")

    # Save uploaded file
    with open(temp_file, "wb") as f:
        content = await file.read()
        f.write(content)

    # Initialize session
    sessions[session_id] = {
        "id": session_id,
        "filename": file.filename,
        "temp_file": str(temp_file),
        "enable_vision": enable_vision,
        "tts_provider": tts_provider,
        "created_at": datetime.now().isoformat(),
        "status": {
            "phase": "starting",
            "progress": 0,
            "message": "Starting processing...",
            "complete": False
        }
    }

    # Save initial session to disk
    save_session(session_id)

    # Start processing in background
    asyncio.create_task(process_lecture(session_id, str(temp_file), enable_vision, tts_provider))

    return {"session_id": session_id}


async def process_lecture(session_id: str, pdf_path: str, enable_vision: bool = False, tts_provider: str = "google"):
    """Process lecture in background.

    Args:
        session_id: Unique session identifier
        pdf_path: Path to the PDF file
        enable_vision: Whether to run vision analysis (default: False for safety)
        tts_provider: TTS provider to use - "google" or "edge" (default: "google")
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent))

    from app.services.parsers import PDFParser
    from app.services.ai import GeminiProvider
    from app.services.global_context_builder import GlobalContextBuilder
    from app.services.tts import GoogleTTSProvider
    from app.config import settings
    import fitz

    try:
        # Phase 1: Parsing
        sessions[session_id]["status"] = {
            "phase": "parsing",
            "progress": 10,
            "message": "Parsing PDF...",
            "complete": False
        }

        parser = PDFParser()
        slides = parser.parse(pdf_path)

        # Limit to 150 slides for cost protection
        if len(slides) > 150:
            sessions[session_id]["status"] = {
                "phase": "error",
                "progress": 0,
                "message": f"Presentation has {len(slides)} slides. Maximum allowed is 150 slides.",
                "complete": False
            }
            save_session(session_id)
            return

        sessions[session_id]["total_slides"] = len(slides)
        sessions[session_id]["status"]["total_slides"] = len(slides)

        # Phase 2: Extract slide images
        sessions[session_id]["status"] = {
            "phase": "extracting_images",
            "progress": 20,
            "message": "Extracting slide images...",
            "complete": False,
            "total_slides": len(slides)
        }

        output_dir = Path("output") / session_id
        output_slides_dir = output_dir / "slides"
        output_audio_dir = output_dir / "audio"
        output_slides_dir.mkdir(parents=True, exist_ok=True)
        output_audio_dir.mkdir(parents=True, exist_ok=True)

        doc = fitz.open(pdf_path)
        zoom = 150 / 72.0
        mat = fitz.Matrix(zoom, zoom)

        for page_num in range(len(slides)):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=mat)
            output_file = output_slides_dir / f"slide_{page_num:03d}.png"
            pix.save(output_file)

        doc.close()

        # Phase 3: Build global context
        sessions[session_id]["status"] = {
            "phase": "building_context",
            "progress": 35,
            "message": "Analyzing lecture structure...",
            "complete": False,
            "total_slides": len(slides)
        }

        gemini_provider = GeminiProvider(model=settings.gemini_model)
        context_builder = GlobalContextBuilder(ai_provider=gemini_provider)

        structural = await gemini_provider.analyze_structure(slides)

        # Vision analysis (optional, with fallback)
        visual = {"key_diagrams": []}
        if enable_vision:
            try:
                print(f"   🔍 Running vision analysis (this may take 30-60 seconds)...")
                # Collect all images from slides
                all_images = []
                for slide in slides:
                    all_images.extend(slide.images)

                if all_images:
                    visual = await gemini_provider.analyze_images(all_images, slides)
                    print(f"   ✅ Vision analysis complete! Found {len(visual.get('key_diagrams', []))} key diagrams")
                else:
                    print(f"   ⚠️  No images found in slides, skipping vision analysis")
            except Exception as e:
                print(f"   ⚠️  Vision analysis failed: {e}")
                print(f"   📝 Falling back to text-only analysis")
                visual = {"key_diagrams": []}

        global_plan = context_builder._synthesize_plan(slides, structural, visual)
        section_strategies = await context_builder._build_section_strategies(slides, global_plan)
        global_plan.section_narration_strategies = section_strategies

        # Phase 4: Generate narrations
        sessions[session_id]["status"] = {
            "phase": "generating_narrations",
            "progress": 55,
            "message": "Generating narrations...",
            "complete": False,
            "total_slides": len(slides)
        }

        all_narrations = {}
        global_plan_dict = global_plan.model_dump()

        for section_strategy in section_strategies:
            section_slides = slides[section_strategy.start_slide:section_strategy.end_slide + 1]
            try:
                section_narrations = await gemini_provider.generate_section_narrations(
                    section_slides=section_slides,
                    section_strategy=section_strategy.model_dump(),
                    global_plan=global_plan_dict
                )
                all_narrations.update(section_narrations)
                actual_slides = sorted(section_narrations.keys())
                expected_slides = list(range(section_strategy.start_slide, section_strategy.end_slide + 1))
                missing_in_section = [s for s in expected_slides if s not in actual_slides]

                if missing_in_section:
                    print(f"⚠️  Section {section_strategy.start_slide}-{section_strategy.end_slide}: Got {len(actual_slides)}/{len(expected_slides)} slides, missing {missing_in_section}")
                else:
                    print(f"✅ Generated narrations for slides {section_strategy.start_slide}-{section_strategy.end_slide}")
            except Exception as e:
                print(f"❌ Failed to generate narrations for slides {section_strategy.start_slide}-{section_strategy.end_slide}: {e}")
                import traceback
                traceback.print_exc()

        # Check for missing narrations
        missing_slides = [i for i in range(len(slides)) if i not in all_narrations]
        if missing_slides:
            print(f"⚠️  Missing narrations for {len(missing_slides)} slides: {missing_slides}")
        print(f"✅ Have narrations for {len(all_narrations)}/{len(slides)} slides")

        # Phase 5: Generate audio
        sessions[session_id]["status"] = {
            "phase": "generating_audio",
            "progress": 75,
            "message": "Generating audio files...",
            "complete": False,
            "total_slides": len(slides)
        }

        # Initialize TTS provider (Edge TTS only for now)
        from app.services.tts import EdgeTTSProvider
        tts = EdgeTTSProvider(voice="en-US-GuyNeural")

        # Store word timings for each slide
        all_timings = {}

        for slide_idx in sorted(all_narrations.keys()):
            narration = all_narrations[slide_idx]

            try:
                # Clean narration for TTS (remove all markdown and symbols)
                import re
                clean_narration = narration
                # Remove backticks
                clean_narration = clean_narration.replace("`", "")
                # Remove asterisks (bold/italic markdown)
                clean_narration = clean_narration.replace("*", "")
                # Remove underscores (markdown emphasis)
                clean_narration = re.sub(r'(?<!\w)_(?!\w)', '', clean_narration)
                # Remove markdown headers
                clean_narration = re.sub(r'^#+\s+', '', clean_narration, flags=re.MULTILINE)
                # Remove double spaces
                clean_narration = re.sub(r'\s+', ' ', clean_narration).strip()

                output_file = output_audio_dir / f"slide_{slide_idx:03d}.mp3"
                timing_data = await tts.generate_audio(clean_narration, str(output_file))
                all_timings[slide_idx] = timing_data["timings"]
            except Exception as e:
                print(f"❌ Failed to generate audio for slide {slide_idx}: {e}")

        # Phase 6: Store lecture data
        sessions[session_id]["status"] = {
            "phase": "creating_viewer",
            "progress": 95,
            "message": "Finalizing...",
            "complete": False,
            "total_slides": len(slides)
        }

        pdf_name = Path(pdf_path).stem
        slide_titles = [slide.title or f"Slide {i+1}" for i, slide in enumerate(slides)]

        sessions[session_id]["lecture_data"] = {
            "pdf_name": pdf_name,
            "total_slides": len(slides),
            "narrations": all_narrations,
            "slide_titles": slide_titles,
            "word_timings": all_timings
        }

        # Complete
        sessions[session_id]["status"] = {
            "phase": "complete",
            "progress": 100,
            "message": "Processing complete!",
            "complete": True,
            "total_slides": len(slides)
        }

        # Save completed session to disk
        save_session(session_id)

    except Exception as e:
        sessions[session_id]["status"] = {
            "phase": "error",
            "progress": 0,
            "message": f"Error: {str(e)}",
            "complete": False
        }
        print(f"Error processing session {session_id}: {e}")
        import traceback
        traceback.print_exc()

        # Save failed session to disk
        save_session(session_id)


@app.get("/api/v1/sessions")
async def list_sessions():
    """Get all completed sessions for the dashboard."""
    completed_sessions = []

    for session_id, session_data in sessions.items():
        if session_data.get("status", {}).get("complete"):
            completed_sessions.append({
                "id": session_id,
                "filename": session_data.get("filename"),
                "created_at": session_data.get("created_at"),
                "total_slides": session_data.get("lecture_data", {}).get("total_slides", 0),
                "enable_vision": session_data.get("enable_vision", False),
                "tts_provider": session_data.get("tts_provider", "google")
            })

    # Sort by creation date, most recent first
    completed_sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return {"sessions": completed_sessions}


@app.get("/api/v1/session/{session_id}/status")
async def get_status(session_id: str):
    """Get processing status for a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    return sessions[session_id]["status"]


@app.get("/api/v1/session/{session_id}/lecture")
async def get_lecture(session_id: str):
    """Get lecture data for viewing."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    if "lecture_data" not in sessions[session_id]:
        raise HTTPException(status_code=400, detail="Lecture not ready yet")

    return sessions[session_id]["lecture_data"]


@app.get("/api/v1/session/{session_id}/slide/{slide_index}")
async def get_slide(session_id: str, slide_index: int):
    """Serve slide image."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    slide_file = Path("output") / session_id / "slides" / f"slide_{slide_index:03d}.png"

    if not slide_file.exists():
        raise HTTPException(status_code=404, detail="Slide not found")

    return FileResponse(slide_file, media_type="image/png")


@app.get("/api/v1/session/{session_id}/audio/{slide_index}")
async def get_audio(session_id: str, slide_index: int):
    """Serve audio file."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    audio_file = Path("output") / session_id / "audio" / f"slide_{slide_index:03d}.mp3"

    if not audio_file.exists():
        raise HTTPException(status_code=404, detail="Audio not found")

    return FileResponse(audio_file, media_type="audio/mpeg")


@app.post("/api/v1/test-tts")
async def test_tts(text: str = "Hello, this is a test of the text to speech system.", provider: str = "google"):
    """
    Quick TTS test endpoint - generates audio from text without needing a full PDF upload.

    Args:
        text: Text to convert to speech (default: test message)
        provider: TTS provider to use - "google" or "edge" (default: "google")
    """
    import tempfile
    from pathlib import Path

    try:
        # Create temporary file for audio
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
            temp_audio_path = temp_audio.name

        # Initialize TTS provider (Edge TTS only for now)
        from app.services.tts import EdgeTTSProvider
        tts = EdgeTTSProvider(voice="en-US-GuyNeural")

        # Generate audio
        await tts.generate_audio(text, temp_audio_path)

        # Return the audio file
        return FileResponse(temp_audio_path, media_type="audio/mpeg", filename="test.mp3")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS test failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
