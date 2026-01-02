#!/usr/bin/env python3
"""
FastAPI server for AI Lecturer system.
"""
import os
import subprocess
import re
import asyncio
import uuid
from pathlib import Path
from typing import Dict, Any
import shutil
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


def convert_pptx_to_pdf(pptx_path: Path) -> Path:
    """Convert a PPTX file to PDF using LibreOffice."""
    output_dir = pptx_path.parent
    try:
        subprocess.run(
            [
                "soffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(output_dir),
                str(pptx_path),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as e:
        raise RuntimeError("LibreOffice (soffice) is not installed on the server.") from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"PPTX conversion failed: {e.stderr.decode('utf-8', errors='ignore')}") from e

    pdf_path = output_dir / f"{pptx_path.stem}.pdf"
    if not pdf_path.exists():
        raise RuntimeError("PPTX conversion failed: PDF output not found.")
    return pdf_path

# Rate limiting storage: {ip_address: [timestamp1, timestamp2, ...]}
rate_limit_storage: Dict[str, list] = {}
polly_rate_limit_storage: Dict[str, list] = {}
active_sessions_by_ip: Dict[str, set] = {}
processing_tasks: Dict[str, asyncio.Task] = {}

app = FastAPI(title="AI Lecturer API")


def resolve_client_ip(request: Request) -> str:
    """Resolve client IP with safe handling of proxy headers."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    real_ip = request.headers.get("X-Real-IP")
    direct_ip = request.client.host

    if settings.frontend_url.startswith("http"):
        # In production behind a proxy, trust the first X-Forwarded-For if present.
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        if real_ip:
            return real_ip
    # Local/dev fallback.
    return direct_ip

# Add CORS middleware
# Allow both local development and production URLs
allowed_origins = [
    "http://localhost:3000",  # Local development
    "https://lectura-b14z.vercel.app",  # Vercel deployment
    "https://lectura.ink",  # Custom domain
    "https://www.lectura.ink",  # Custom domain with www
    "https://lectora.ink",  # Custom domain
    "https://www.lectora.ink",  # Custom domain with www
    "http://lectura.ink",   # HTTP version
    "http://www.lectura.ink",   # HTTP version with www
    "http://lectora.ink",   # HTTP version
    "http://www.lectora.ink",   # HTTP version with www
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


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Access logging disabled."""
    return await call_next(request)


@app.on_event("startup")
async def startup_event():
    """Load sessions from disk on startup."""
    print("Loading sessions from disk...")
    load_sessions()
    removed = await cleanup_expired_sessions(settings.session_ttl_hours)
    print(f"Loaded {len(sessions)} sessions (removed {removed} expired)")


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


def check_polly_rate_limit(ip: str, max_requests: int = 1, window_hours: int = 24) -> bool:
    """Check if an IP has exceeded the Polly-only rate limit."""
    now = datetime.now()
    cutoff_time = now - timedelta(hours=window_hours)

    if ip in polly_rate_limit_storage:
        polly_rate_limit_storage[ip] = [
            timestamp for timestamp in polly_rate_limit_storage[ip]
            if timestamp > cutoff_time
        ]
    else:
        polly_rate_limit_storage[ip] = []

    if len(polly_rate_limit_storage[ip]) >= max_requests:
        return False

    polly_rate_limit_storage[ip].append(now)
    return True


def check_concurrent_limit(ip: str, max_active: int = 1) -> bool:
    """Check if an IP has too many active sessions."""
    active = active_sessions_by_ip.get(ip, set())
    return len(active) < max_active


def register_active_session(ip: str, session_id: str) -> None:
    active_sessions_by_ip.setdefault(ip, set()).add(session_id)


def unregister_active_session(ip: str, session_id: str) -> None:
    active = active_sessions_by_ip.get(ip)
    if not active:
        return
    active.discard(session_id)
    if not active:
        active_sessions_by_ip.pop(ip, None)


async def cleanup_session_files(session_id: str) -> None:
    """Remove temp file and output artifacts for a session."""
    session = sessions.get(session_id, {})
    temp_path = session.get("temp_file")
    output_dir = Path("output") / session_id

    if temp_path:
        try:
            await asyncio.to_thread(Path(temp_path).unlink, missing_ok=True)
        except Exception:
            pass
    if output_dir.exists():
        try:
            await asyncio.to_thread(shutil.rmtree, output_dir, True)
        except Exception:
            pass


async def cleanup_expired_sessions(ttl_hours: int) -> int:
    """Remove expired sessions and their artifacts."""
    if ttl_hours <= 0:
        return 0
    now = datetime.now()
    cutoff = now - timedelta(hours=ttl_hours)
    removed = 0

    for session_id, session_data in list(sessions.items()):
        created_at = session_data.get("created_at")
        status = session_data.get("status", {})
        phase = status.get("phase")
        if phase not in {"complete", "error", "canceled"}:
            continue
        try:
            created_time = datetime.fromisoformat(created_at) if created_at else None
        except ValueError:
            created_time = None
        if not created_time or created_time > cutoff:
            continue

        await cleanup_session_files(session_id)
        session_file = SESSIONS_DIR / f"{session_id}.json"
        try:
            await asyncio.to_thread(session_file.unlink, missing_ok=True)
        except Exception:
            pass
        sessions.pop(session_id, None)
        removed += 1

    return removed


@app.post("/api/v1/upload")
async def upload_file(request: Request, file: UploadFile = File(...), enable_vision: bool = False, tts_provider: str = "edge", polly_voice: str = "Matthew"):
    """Upload a PDF or PPTX file and start processing.

    Args:
        request: FastAPI request object (to get client IP)
        file: The PDF or PPTX file to process
        enable_vision: Whether to enable vision analysis for diagrams/tables (default: False)
        tts_provider: TTS provider - "edge" (free, robotic) or "polly" (free tier, better quality)
    """
    print(f"📤 UPLOAD STARTED: {file.filename}, origin: {request.headers.get('origin')}")

    # Get client IP (handle proxies/load balancers)
    client_ip = resolve_client_ip(request)

    # Check overall rate limit (5 lectures per 24 hours)
    if not check_rate_limit(client_ip, max_requests=5, window_hours=24):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded (5 per day). Please try again later."
        )

    # Check Polly-only rate limit (1 lecture per 24 hours)
    if tts_provider == "polly":
        if not check_polly_rate_limit(client_ip, max_requests=1, window_hours=24):
            raise HTTPException(
                status_code=429,
                detail="Polly rate limit exceeded (1 per day). Please switch to Edge or try again later."
            )
    # Check concurrent processing limit (1 active session per IP)
    if not check_concurrent_limit(client_ip, max_active=1):
        raise HTTPException(
            status_code=429,
            detail="Another lecture is already processing for this IP. Please wait for it to finish."
        )
    # Validate file type
    if not (file.filename.endswith('.pdf') or file.filename.endswith('.pptx')):
        raise HTTPException(status_code=400, detail="Only PDF and PPTX files are supported")

    # Create session
    session_id = str(uuid.uuid4())
    temp_file = Path(f"/tmp/{session_id}_{file.filename}")

    # Save uploaded file
    content = await file.read()
    await asyncio.to_thread(lambda: temp_file.write_bytes(content))

    # Initialize session early (for conversion/status updates)
    sessions[session_id] = {
        "id": session_id,
        "filename": file.filename,
        "temp_file": str(temp_file),
        "original_file": str(temp_file),
        "enable_vision": enable_vision,
        "tts_provider": tts_provider,
        "client_ip": client_ip,
        "created_at": datetime.now().isoformat(),
        "status": {
            "phase": "starting",
            "progress": 0,
            "message": "Preparing your lecture...",
            "complete": False
        }
    }

    # Save initial session to disk
    await asyncio.to_thread(save_session, session_id)

    # Convert PPTX to PDF (auto)
    if file.filename.endswith(".pptx"):
        sessions[session_id]["status"] = {
            "phase": "converting",
            "progress": 5,
            "message": "Converting PPTX to PDF...",
            "complete": False
        }
        await asyncio.to_thread(save_session, session_id)
        try:
            temp_file = await asyncio.to_thread(convert_pptx_to_pdf, temp_file)
            sessions[session_id]["temp_file"] = str(temp_file)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Check slide count BEFORE processing (reject early)
    import fitz
    slide_count = await asyncio.to_thread(lambda: len(fitz.open(str(temp_file))))
    if slide_count > 100:
        # Clean up temp file
        await asyncio.to_thread(temp_file.unlink, missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail=f"Presentation has {slide_count} slides. Maximum allowed is 100 slides."
        )

    # Register active session for concurrency control
    register_active_session(client_ip, session_id)

    # Start processing in background
    task = asyncio.create_task(process_lecture(session_id, str(temp_file), enable_vision, tts_provider, polly_voice))
    processing_tasks[session_id] = task

    download_url = f"{request.base_url}api/v1/session/{session_id}/file"
    print(f"📎 DOWNLOAD LINK: {download_url}")
    print(f"✅ UPLOAD COMPLETE - returning session_id: {session_id}")
    return {"session_id": session_id}


async def process_lecture(session_id: str, pdf_path: str, enable_vision: bool = False, tts_provider: str = "google", polly_voice: str = "Matthew"):
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
    from app.config import settings
    import fitz

    try:
        # Phase 1: Parsing
        sessions[session_id]["status"] = {
            "phase": "parsing",
            "progress": 10,
            "message": "Reading slides...",
            "complete": False
        }

        parser = PDFParser()
        # Run blocking PDF parsing in thread pool to avoid blocking event loop
        slides = await asyncio.to_thread(parser.parse, pdf_path)

        # Slide count already validated at upload time, just set it
        sessions[session_id]["total_slides"] = len(slides)
        sessions[session_id]["status"]["total_slides"] = len(slides)

        # Phase 2: Extract slide images
        sessions[session_id]["status"] = {
            "phase": "extracting_images",
            "progress": 20,
            "message": "Rendering slides...",
            "complete": False,
            "total_slides": len(slides)
        }

        output_dir = Path("output") / session_id
        output_slides_dir = output_dir / "slides"
        output_audio_dir = output_dir / "audio"

        # Run blocking mkdir operations in thread pool
        await asyncio.to_thread(output_slides_dir.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(output_audio_dir.mkdir, parents=True, exist_ok=True)

        # Extract images in thread pool to avoid blocking
        def extract_slide_images():
            doc = fitz.open(pdf_path)
            zoom = 150 / 72.0
            mat = fitz.Matrix(zoom, zoom)

            for page_num in range(len(slides)):
                page = doc[page_num]
                pix = page.get_pixmap(matrix=mat)
                output_file = output_slides_dir / f"slide_{page_num:03d}.png"
                pix.save(output_file)

            doc.close()

        await asyncio.to_thread(extract_slide_images)

        # Phase 3: Build global context
        sessions[session_id]["status"] = {
            "phase": "building_context",
            "progress": 35,
            "message": "Understanding the lecture...",
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

        # Run synthesis in thread pool (might be CPU-intensive)
        global_plan = await asyncio.to_thread(context_builder._synthesize_plan, slides, structural, visual)
        section_strategies = await context_builder._build_section_strategies(slides, global_plan)
        global_plan.section_narration_strategies = section_strategies

        # Phase 4: Generate narrations
        sessions[session_id]["status"] = {
            "phase": "generating_narrations",
            "progress": 55,
            "message": "Writing narration...",
            "complete": False,
            "total_slides": len(slides)
        }

        all_narrations = {}
        global_plan_dict = global_plan.model_dump()

        # Chunk size: keep sections small to reduce truncation risk.
        CHUNK_SIZE = 8

        for section_strategy in section_strategies:
            section_slides = slides[section_strategy.start_slide:section_strategy.end_slide + 1]
            num_section_slides = len(section_slides)

            # If section is small enough, generate in one go
            if num_section_slides <= CHUNK_SIZE:
                try:
                    section_narrations = await gemini_provider.generate_section_narrations(
                        section_slides=section_slides,
                        section_strategy=section_strategy.model_dump(),
                        global_plan=global_plan_dict
                    )
                    all_narrations.update(section_narrations)
                    print(f"✅ Generated narrations for slides {section_strategy.start_slide}-{section_strategy.end_slide}")
                    # Yield control to event loop so other requests can be processed
                    await asyncio.sleep(0)
                except Exception as e:
                    print(f"❌ Failed to generate narrations for slides {section_strategy.start_slide}-{section_strategy.end_slide}: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                # Large section - split into chunks and pass context between them
                print(f"📦 Large section ({num_section_slides} slides) - splitting into chunks of {CHUNK_SIZE}")

                for chunk_start in range(0, num_section_slides, CHUNK_SIZE):
                    chunk_end = min(chunk_start + CHUNK_SIZE, num_section_slides)
                    chunk_slides = section_slides[chunk_start:chunk_end]

                    # Create chunk strategy
                    chunk_strategy = section_strategy.model_dump().copy()
                    chunk_strategy['start_slide'] = section_strategy.start_slide + chunk_start
                    chunk_strategy['end_slide'] = section_strategy.start_slide + chunk_end - 1

                    # Filter slide strategies for this chunk
                    chunk_strategy['slide_strategies'] = [
                        s for s in section_strategy.model_dump().get('slide_strategies', [])
                        if chunk_strategy['start_slide'] <= s['slide_index'] <= chunk_strategy['end_slide']
                    ]

                    # For chunks after the first, add context from previous chunk
                    if chunk_start > 0:
                        # Get last narration from previous chunk as context
                        prev_slide_idx = chunk_strategy['start_slide'] - 1
                        if prev_slide_idx in all_narrations:
                            prev_narration = all_narrations[prev_slide_idx]
                            # Add context hint to narrative arc
                            chunk_strategy['narrative_arc'] += f"\n\nCONTINUING FROM PREVIOUS: {prev_narration[-300:]}"

                    try:
                        chunk_narrations = await gemini_provider.generate_section_narrations(
                            section_slides=chunk_slides,
                            section_strategy=chunk_strategy,
                            global_plan=global_plan_dict
                        )
                        all_narrations.update(chunk_narrations)
                        print(f"✅ Generated chunk: slides {chunk_strategy['start_slide']}-{chunk_strategy['end_slide']}")
                        # Yield control to event loop so other requests can be processed
                        await asyncio.sleep(0)
                    except Exception as e:
                        print(f"❌ Failed chunk {chunk_strategy['start_slide']}-{chunk_strategy['end_slide']}: {e}")
                        import traceback
                        traceback.print_exc()

        # Check for missing narrations
        missing_slides = [i for i in range(len(slides)) if i not in all_narrations]
        if missing_slides:
            print(f"⚠️  Missing narrations for {len(missing_slides)} slides: {missing_slides}")
            print("🔁 Generating missing narrations individually...")
            for slide_idx in missing_slides:
                try:
                    prev_summary = None
                    if slide_idx - 1 in all_narrations:
                        prev_summary = all_narrations[slide_idx - 1][-300:]
                    narration = await gemini_provider.generate_narration(
                        slide=slides[slide_idx],
                        global_plan=global_plan_dict,
                        previous_narration_summary=prev_summary,
                        related_slides=None,
                    )
                    all_narrations[slide_idx] = narration.strip()
                    print(f"✅ Fallback narration generated for slide {slide_idx}")
                except Exception as e:
                    print(f"❌ Fallback failed for slide {slide_idx}: {e}")
        print(f"✅ Have narrations for {len(all_narrations)}/{len(slides)} slides")

        # Detect truncated or suspiciously short narrations and regenerate those slides.
        def is_incomplete_narration(slide_idx: int, text: str) -> bool:
            if not text:
                return True
            slide = slides[slide_idx]
            words = text.split()
            word_count = len(words)
            ends_with_punct = text.rstrip().endswith(('.', '!', '?'))
            has_substantial_content = bool(slide.body_text and len(slide.body_text.strip()) > 80)
            is_title_like = slide.slide_type.value in {"title", "section_header"}

            if is_title_like:
                return word_count < 18 and has_substantial_content
            if has_substantial_content and word_count < 80:
                return True
            if word_count >= 15 and not ends_with_punct:
                return True
            if word_count < 25 and not ends_with_punct:
                return True
            return False

        incomplete_slides = [
            i for i, narration in all_narrations.items()
            if i < len(slides) and is_incomplete_narration(i, narration)
        ]
        if incomplete_slides:
            print(f"⚠️  Incomplete narrations detected for slides: {sorted(incomplete_slides)}")
            print("🔁 Regenerating incomplete narrations individually...")
            for slide_idx in sorted(incomplete_slides):
                try:
                    prev_summary = None
                    if slide_idx - 1 in all_narrations:
                        prev_summary = all_narrations[slide_idx - 1][-300:]
                    narration = await gemini_provider.generate_narration(
                        slide=slides[slide_idx],
                        global_plan=global_plan_dict,
                        previous_narration_summary=prev_summary,
                        related_slides=None,
                    )
                    narration = narration.strip()
                    all_narrations[slide_idx] = narration
                    print(f"✅ Regenerated narration for slide {slide_idx}")

                    # Second-chance retry if still incomplete.
                    if is_incomplete_narration(slide_idx, narration):
                        print(f"🔁 Second retry for slide {slide_idx} (still incomplete)")
                        narration = await gemini_provider.generate_narration(
                            slide=slides[slide_idx],
                            global_plan=global_plan_dict,
                            previous_narration_summary=prev_summary,
                            related_slides=None,
                        )
                        all_narrations[slide_idx] = narration.strip()
                        print(f"✅ Second retry complete for slide {slide_idx}")
                except Exception as e:
                    print(f"❌ Regenerate failed for slide {slide_idx}: {e}")

        def format_display_math(text: str) -> str:
            """Convert spoken math into display-friendly notation."""
            if not text:
                return text
            s = text
            # R to the n -> R^n
            s = re.sub(r'\b([A-Za-z])\s+to the\s+([A-Za-z0-9]+)\b', r'\1^\2', s, flags=re.IGNORECASE)
            # x squared / x cubed -> x^2 / x^3
            s = re.sub(r'\b([A-Za-z0-9]+)\s+squared\b', r'\1^2', s, flags=re.IGNORECASE)
            s = re.sub(r'\b([A-Za-z0-9]+)\s+cubed\b', r'\1^3', s, flags=re.IGNORECASE)
            # x superscript 2 -> x^2
            s = re.sub(r'\b([A-Za-z0-9]+)\s+superscript\s+([A-Za-z0-9]+)\b', r'\1^\2', s, flags=re.IGNORECASE)
            # x sub k -> x_k
            s = re.sub(r'\b([A-Za-z0-9]+)\s+sub\s+([A-Za-z0-9]+)\b', r'\1_\2', s, flags=re.IGNORECASE)
            # x subscript 2 -> x_2
            s = re.sub(r'\b([A-Za-z0-9]+)\s+subscript\s+([A-Za-z0-9]+)\b', r'\1_\2', s, flags=re.IGNORECASE)
            return s

        def split_sentences(text: str) -> list:
            sentence_pattern = re.compile(r'[^.!?]+[.!?]|[^.!?]+$')
            return [s.strip() for s in sentence_pattern.findall(text or "") if s.strip()]

        # Build display-friendly narrations and sentence lists for subtitles
        display_narrations = {
            slide_idx: format_display_math(narration)
            for slide_idx, narration in all_narrations.items()
        }
        display_sentences = {
            slide_idx: split_sentences(display_narrations.get(slide_idx, ""))
            for slide_idx in all_narrations.keys()
        }

        # Phase 5: Generate audio
        sessions[session_id]["status"] = {
            "phase": "generating_audio",
            "progress": 75,
            "message": "Recording audio...",
            "complete": False,
            "total_slides": len(slides)
        }

        def normalize_math_speech(text: str) -> str:
            """Aggressively normalize math notation into spoken form."""
            import re

            digit_map = {
                "0": "zero",
                "1": "one",
                "2": "two",
                "3": "three",
                "4": "four",
                "5": "five",
                "6": "six",
                "7": "seven",
                "8": "eight",
                "9": "nine",
            }

            def speak_token(token: str) -> str:
                if token in digit_map:
                    return digit_map[token]
                return token

            def replace_power(base: str, exp: str) -> str:
                exp_spoken = speak_token(exp)
                if exp == "2":
                    return f"{base} squared"
                if exp == "3":
                    return f"{base} cubed"
                return f"{base} to the {exp_spoken}"

            s = text
            # LaTeX-style subscripts: x_{k} -> x k
            s = re.sub(r'([A-Za-z])\s*_\s*\{?\s*([A-Za-z0-9]+)\s*\}?', r'\1 \2', s)
            # Worded subscripts: x sub k -> x k
            s = re.sub(
                r'\b([A-Za-z])\s*(?:sub(?:script)?|underscore)\s*([A-Za-z0-9]+)\b',
                lambda m: f"{m.group(1)} {speak_token(m.group(2))}",
                s,
                flags=re.IGNORECASE,
            )
            # Underscore shorthand: x_k -> x k
            s = re.sub(r'\b([A-Za-z])_([A-Za-z0-9]+)\b', r'\1 \2', s)
            # Worded superscripts: x superscript 2 -> x squared
            s = re.sub(
                r'\b([A-Za-z0-9]+)\s*(?:super(?:script)?|superscript)\s*([A-Za-z0-9]+)\b',
                lambda m: replace_power(m.group(1), m.group(2)),
                s,
                flags=re.IGNORECASE,
            )
            # Caret power: x^2 or x caret 2
            s = re.sub(
                r'\b([A-Za-z0-9]+)\s*(?:\^|caret)\s*([A-Za-z0-9]+)\b',
                lambda m: replace_power(m.group(1), m.group(2)),
                s,
                flags=re.IGNORECASE,
            )
            return s

        # Initialize TTS provider
        print(f"🎤 Initializing TTS provider: {tts_provider}")
        try:
            if tts_provider == "polly":
                from app.services.tts import PollyTTSProvider
                print(f"   Polly voice: {polly_voice}, region: {settings.aws_region}")
                tts = PollyTTSProvider(
                    voice_id=polly_voice,
                    engine="neural",
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    aws_region=settings.aws_region
                )
                print(f"   ✅ Polly TTS initialized successfully")
            else:
                # Default to Edge TTS (free, no auth)
                from app.services.tts import EdgeTTSProvider
                tts = EdgeTTSProvider(voice="en-US-GuyNeural")
                print(f"   ✅ Edge TTS initialized successfully")
        except Exception as e:
            print(f"   ❌ TTS initialization failed: {e}")
            import traceback
            traceback.print_exc()
            raise

        # Store word timings for each slide
        all_timings = {}

        print(f"🔊 Starting audio generation for {len(all_narrations)} narrations...")
        tts_semaphore = asyncio.Semaphore(3)

        async def generate_audio_for_slide(slide_idx: int, narration_text: str):
            async with tts_semaphore:
                print(f"   Generating audio for slide {slide_idx}...")
                try:
                    # Clean narration for TTS (remove all markdown and symbols)
                    import re
                    clean_narration = normalize_math_speech(narration_text)
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

        tasks = [
            generate_audio_for_slide(slide_idx, all_narrations[slide_idx])
            for slide_idx in sorted(all_narrations.keys())
        ]
        await asyncio.gather(*tasks)

        # Phase 6: Store lecture data
        sessions[session_id]["status"] = {
            "phase": "creating_viewer",
            "progress": 95,
            "message": "Finalizing lecture...",
            "complete": False,
            "total_slides": len(slides)
        }

        pdf_name = Path(pdf_path).stem
        slide_titles = [slide.title or f"Slide {i+1}" for i, slide in enumerate(slides)]

        sessions[session_id]["lecture_data"] = {
            "pdf_name": pdf_name,
            "total_slides": len(slides),
            "narrations": display_narrations,
            "narrations_tts": all_narrations,
            "slide_titles": slide_titles,
            "tts_provider": tts_provider,
            "polly_voice": polly_voice,
            "enable_vision": enable_vision,
            "display_sentences": display_sentences,
            "word_timings": all_timings
        }

        # Complete
        sessions[session_id]["status"] = {
            "phase": "complete",
            "progress": 100,
            "message": "Lecture ready!",
            "complete": True,
            "total_slides": len(slides)
        }

        # Save completed session to disk
        await asyncio.to_thread(save_session, session_id)

        # Release concurrency slot
        client_ip = sessions[session_id].get("client_ip")
        if client_ip:
            unregister_active_session(client_ip, session_id)
        processing_tasks.pop(session_id, None)

    except asyncio.CancelledError:
        sessions[session_id]["status"] = {
            "phase": "canceled",
            "progress": 0,
            "message": "Processing canceled.",
            "complete": False
        }
        await asyncio.to_thread(save_session, session_id)
        await cleanup_session_files(session_id)
        client_ip = sessions.get(session_id, {}).get("client_ip")
        if client_ip:
            unregister_active_session(client_ip, session_id)
        processing_tasks.pop(session_id, None)
        return
    except Exception as e:
        sessions[session_id]["status"] = {
            "phase": "error",
            "progress": 0,
            "message": f"We hit a snag while processing this lecture. {str(e)}",
            "complete": False
        }
        print(f"Error processing session {session_id}: {e}")
        import traceback
        traceback.print_exc()

        # Save failed session to disk
        await asyncio.to_thread(save_session, session_id)

        # Release concurrency slot
        client_ip = sessions.get(session_id, {}).get("client_ip")
        if client_ip:
            unregister_active_session(client_ip, session_id)
        processing_tasks.pop(session_id, None)


@app.get("/api/v1/sessions")
async def list_sessions(request: Request):
    """Get completed sessions for the current client IP."""
    completed_sessions = []
    client_ip = resolve_client_ip(request)

    for session_id, session_data in sessions.items():
        if session_data.get("client_ip") != client_ip:
            continue
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


@app.post("/api/v1/session/{session_id}/cancel")
async def cancel_session(session_id: str):
    """Cancel a processing session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    status = sessions[session_id].get("status", {})
    if status.get("complete"):
        raise HTTPException(status_code=400, detail="Session already complete")
    if status.get("phase") in {"canceled", "error"}:
        return {"status": status}

    task = processing_tasks.get(session_id)
    if task and not task.done():
        task.cancel()

    sessions[session_id]["status"] = {
        "phase": "canceled",
        "progress": 0,
        "message": "Processing canceled.",
        "complete": False
    }
    await asyncio.to_thread(save_session, session_id)
    await cleanup_session_files(session_id)
    client_ip = sessions.get(session_id, {}).get("client_ip")
    if client_ip:
        unregister_active_session(client_ip, session_id)
    processing_tasks.pop(session_id, None)

    return {"status": sessions[session_id]["status"]}


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

    if not await asyncio.to_thread(slide_file.exists):
        raise HTTPException(status_code=404, detail="Slide not found")

    return FileResponse(slide_file, media_type="image/png")


@app.get("/api/v1/session/{session_id}/audio/{slide_index}")
async def get_audio(session_id: str, slide_index: int):
    """Serve audio file."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    audio_file = Path("output") / session_id / "audio" / f"slide_{slide_index:03d}.mp3"

    if not await asyncio.to_thread(audio_file.exists):
        raise HTTPException(status_code=404, detail="Audio not found")

    return FileResponse(audio_file, media_type="audio/mpeg")


@app.get("/api/v1/session/{session_id}/file")
async def get_uploaded_file(session_id: str):
    """Download the original uploaded file."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    original_file = sessions[session_id].get("original_file")
    if not original_file:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = Path(original_file)
    if not await asyncio.to_thread(file_path.exists):
        raise HTTPException(status_code=404, detail="File not found")

    filename = sessions[session_id].get("filename") or file_path.name
    return FileResponse(file_path, media_type="application/octet-stream", filename=filename)


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

        # Initialize TTS provider
        if tts_provider == "polly":
            from app.services.tts import PollyTTSProvider
            tts = PollyTTSProvider(
                voice_id=polly_voice,
                engine="neural",
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                aws_region=settings.aws_region
            )
        else:
            # Default to Edge TTS (free, no auth)
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
    # Use 1 worker since sessions dict is in-memory and not shared across workers
    # Rely on asyncio.to_thread() for concurrency instead
    uvicorn.run("server:app", host="0.0.0.0", port=8000, workers=1)
