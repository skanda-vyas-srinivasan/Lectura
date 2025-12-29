#!/usr/bin/env python3
"""
Complete AI Lecturer Pipeline - One script does everything.

Usage:
    python pipeline.py <path_to_pdf> [--slides N]
"""
import sys
import asyncio
import json
from pathlib import Path

from app.services.parsers import PDFParser
from app.services.ai import GeminiProvider
from app.services.global_context_builder import GlobalContextBuilder
from app.services.tts import EdgeTTSProvider
from app.services.narration_cache import NarrationCache
from app.config import settings


async def main():
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <path_to_pdf> [--slides N]")
        sys.exit(1)

    pdf_path = sys.argv[1]

    # Optional: limit number of slides
    num_slides = None
    if "--slides" in sys.argv:
        idx = sys.argv.index("--slides")
        if idx + 1 < len(sys.argv):
            num_slides = int(sys.argv[idx + 1])

    print("=" * 70)
    print("🚀 AI LECTURER - COMPLETE PIPELINE")
    print("=" * 70)
    print(f"📄 PDF: {pdf_path}")
    if num_slides:
        print(f"📝 Processing first {num_slides} slides")
    print()

    # ========================================================================
    # PHASE 1: PARSE PDF
    # ========================================================================
    print("📖 PHASE 1: Parsing PDF...")
    parser = PDFParser()
    slides = parser.parse(pdf_path)
    print(f"✅ Parsed {len(slides)} slides")

    if num_slides:
        slides = slides[:num_slides]
        print(f"   Using first {num_slides} slides")

    # ========================================================================
    # PHASE 2: EXTRACT SLIDE IMAGES
    # ========================================================================
    print("\n🖼️  PHASE 2: Extracting slide images...")

    import fitz
    doc = fitz.open(pdf_path)

    output_slides_dir = Path("output/slides")
    output_slides_dir.mkdir(parents=True, exist_ok=True)

    zoom = 150 / 72.0  # 150 DPI
    mat = fitz.Matrix(zoom, zoom)

    slides_to_export = num_slides if num_slides else len(doc)
    for page_num in range(min(slides_to_export, len(doc))):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=mat)
        output_file = output_slides_dir / f"slide_{page_num:03d}.png"
        pix.save(output_file)

    doc.close()
    print(f"✅ Extracted {slides_to_export} slide images to output/slides/")

    # ========================================================================
    # PHASE 3: BUILD GLOBAL CONTEXT
    # ========================================================================
    print("\n🧠 PHASE 3: Building global context...")
    gemini_provider = GeminiProvider(model=settings.gemini_model)
    context_builder = GlobalContextBuilder(ai_provider=gemini_provider)

    def progress_callback(stage: str, progress: float):
        status = "✓" if progress == 1.0 else "..."
        print(f"   [{status}] {stage}: {progress * 100:.0f}%")

    # Skip vision analysis to avoid timeout - use structural only
    print("   Running structural analysis...")
    structural = await gemini_provider.analyze_structure(slides)

    print("   Synthesizing global plan...")
    # Create minimal visual analysis
    visual = {"key_diagrams": []}

    global_plan = context_builder._synthesize_plan(slides, structural, visual)

    print("   Building section strategies (including intro)...")
    section_strategies = await context_builder._build_section_strategies(slides, global_plan)
    global_plan.section_narration_strategies = section_strategies

    print(f"✅ Created {len(section_strategies)} section strategies:")
    for strategy in section_strategies:
        print(f"      • {strategy.section_title}: slides {strategy.start_slide + 1}-{strategy.end_slide + 1}")

    # ========================================================================
    # PHASE 4: GENERATE NARRATIONS
    # ========================================================================
    print("\n🎤 PHASE 4: Generating narrations...")

    global_plan_dict = global_plan.model_dump()
    all_narrations = {}

    for section_strategy in section_strategies:
        start = section_strategy.start_slide
        end = section_strategy.end_slide

        # Only process sections that contain our slides
        if start >= len(slides):
            continue

        section_slides = slides[start:min(end + 1, len(slides))]

        print(f"   Generating: {section_strategy.section_title} (slides {start + 1}-{end + 1})...")

        # Generate narrations for this section
        section_narrations = await gemini_provider.generate_section_narrations(
            section_slides=section_slides,
            section_strategy=section_strategy.model_dump(),
            global_plan=global_plan_dict
        )

        all_narrations.update(section_narrations)

        # Show progress
        for slide_idx in sorted(section_narrations.keys()):
            if slide_idx < len(slides):
                word_count = len(section_narrations[slide_idx].split())
                print(f"      Slide {slide_idx + 1}: {word_count} words")

    print(f"✅ Generated {len(all_narrations)} narrations")

    # ========================================================================
    # PHASE 5: CACHE RESULTS
    # ========================================================================
    print("\n💾 PHASE 5: Caching results...")
    cache = NarrationCache()
    pdf_name = Path(pdf_path).stem

    cache.save(pdf_name, all_narrations, global_plan_dict)
    print(f"✅ Cached to: {cache.get_cache_path(pdf_name)}")

    # ========================================================================
    # PHASE 5: GENERATE AUDIO
    # ========================================================================
    print("\n🔊 PHASE 5: Generating audio files...")
    tts = EdgeTTSProvider(voice="en-US-GuyNeural")

    output_dir = Path("output/audio")
    output_dir.mkdir(parents=True, exist_ok=True)

    for slide_idx in sorted(all_narrations.keys()):
        narration = all_narrations[slide_idx]
        output_file = output_dir / f"slide_{slide_idx:03d}.mp3"

        await tts.generate_audio(narration, str(output_file))

        file_size_kb = output_file.stat().st_size / 1024
        word_count = len(narration.split())
        print(f"   ✅ Slide {slide_idx + 1}: {output_file.name} ({file_size_kb:.1f} KB, {word_count} words)")

    print(f"✅ Generated {len(all_narrations)} audio files")

    # ========================================================================
    # PHASE 6: GENERATE VIEWER
    # ========================================================================
    print("\n🎬 PHASE 6: Generating viewer...")

    # Create viewer HTML - pass narrations directly
    viewer_html = create_viewer_html(pdf_name, len(all_narrations), slides, all_narrations)

    viewer_path = Path("viewer.html")
    viewer_path.write_text(viewer_html)

    print(f"✅ Created viewer: {viewer_path.absolute()}")

    # ========================================================================
    # DONE
    # ========================================================================
    print("\n" + "=" * 70)
    print("✅ PIPELINE COMPLETE!")
    print("=" * 70)
    print(f"\n📊 Summary:")
    print(f"   • Slides processed: {len(slides)}")
    print(f"   • Narrations generated: {len(all_narrations)}")
    print(f"   • Audio files: {len(all_narrations)}")
    print(f"   • Viewer: viewer.html")
    print(f"\n🎬 Open viewer.html in your browser to watch the lecture!")


def create_viewer_html(pdf_name: str, total_slides: int, slides, narrations_dict: dict) -> str:
    """Create viewer HTML with embedded transcripts."""

    # Convert narrations dict to list for JavaScript
    transcripts_list = []
    for i in range(total_slides):
        narration_text = narrations_dict.get(i, '')  # narrations_dict has int keys
        transcripts_list.append(narration_text)

    transcripts_json = json.dumps(transcripts_list)
    slide_titles_json = json.dumps([slide.title or f'Slide {i+1}' for i, slide in enumerate(slides[:total_slides])])

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Lecturer - {pdf_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a1a; color: #fff; display: flex; flex-direction: column; height: 100vh; }}
        .header {{ background: #2d2d2d; padding: 1rem 2rem; border-bottom: 2px solid #3d3d3d; display: flex; align-items: center; justify-content: space-between; }}
        .header h1 {{ font-size: 1.5rem; font-weight: 600; }}
        .header p {{ color: #999; font-size: 0.9rem; margin-top: 0.25rem; }}
        .transcript-toggle {{ background: #3b82f6; color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; font-size: 0.9rem; transition: all 0.2s; }}
        .transcript-toggle:hover {{ background: #2563eb; }}
        .main-content {{ flex: 1; display: flex; overflow: hidden; }}
        .slide-container {{ flex: 1; display: flex; align-items: center; justify-content: center; padding: 2rem; background: #222; transition: all 0.3s; }}
        .slide-container.with-transcript {{ flex: 0.6; }}
        .slide-display {{ background: white; box-shadow: 0 4px 20px rgba(0,0,0,0.5); max-width: 90%; max-height: 90%; display: flex; align-items: center; justify-content: center; overflow: hidden; }}
        .slide-image {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
        .transcript-panel {{ width: 0; background: #2d2d2d; border-left: 2px solid #3d3d3d; overflow-y: auto; transition: width 0.3s; display: flex; flex-direction: column; }}
        .transcript-panel.open {{ width: 40%; }}
        .transcript-header {{ padding: 1.5rem; border-bottom: 2px solid #3d3d3d; background: #252525; }}
        .transcript-header h2 {{ font-size: 1.2rem; margin-bottom: 0.5rem; }}
        .transcript-header .slide-title {{ color: #3b82f6; font-size: 0.9rem; }}
        .transcript-content {{ padding: 1.5rem; line-height: 1.8; color: #ddd; flex: 1; overflow-y: auto; }}
        .transcript-content p {{ margin-bottom: 1rem; }}
        .controls {{ background: #2d2d2d; padding: 1.5rem 2rem; border-top: 2px solid #3d3d3d; }}
        .progress-bar {{ width: 100%; height: 4px; background: #3d3d3d; border-radius: 2px; margin-bottom: 1rem; overflow: hidden; }}
        .progress-fill {{ height: 100%; background: linear-gradient(90deg, #3b82f6, #8b5cf6); width: 0%; transition: width 0.1s linear; }}
        .control-buttons {{ display: flex; align-items: center; gap: 1rem; }}
        .btn {{ background: #3b82f6; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 6px; cursor: pointer; font-size: 1rem; transition: all 0.2s; }}
        .btn:hover {{ background: #2563eb; transform: translateY(-1px); }}
        .btn:disabled {{ background: #4a4a4a; cursor: not-allowed; transform: none; }}
        .btn-secondary {{ background: #4a4a4a; }}
        .btn-secondary:hover {{ background: #5a5a5a; }}
        .slide-info {{ flex: 1; text-align: center; font-size: 1.1rem; color: #999; }}
        .current-slide {{ color: #3b82f6; font-weight: 600; }}
        .audio-time {{ margin-left: auto; color: #999; font-size: 0.9rem; }}
        .status {{ text-align: center; color: #3b82f6; margin-bottom: 1rem; font-size: 0.9rem; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>🎓 AI Lecturer</h1>
            <p>{pdf_name}</p>
        </div>
        <button class="transcript-toggle" onclick="toggleTranscript()">📄 Show Transcript</button>
    </div>

    <div class="main-content">
        <div class="slide-container" id="slideContainer">
            <div class="slide-display">
                <img id="slideImage" class="slide-image" src="output/slides/slide_000.png" alt="Slide 1">
            </div>
        </div>
        <div class="transcript-panel" id="transcriptPanel">
            <div class="transcript-header">
                <h2>Transcript</h2>
                <div class="slide-title" id="transcriptSlideTitle">Slide 1</div>
            </div>
            <div class="transcript-content" id="transcriptContent"></div>
        </div>
    </div>

    <div class="controls">
        <div class="status" id="status">Ready</div>
        <div class="progress-bar"><div class="progress-fill" id="progress"></div></div>
        <div class="control-buttons">
            <button class="btn btn-secondary" id="prevBtn" onclick="previousSlide()">⏮ Previous</button>
            <button class="btn" id="playPauseBtn" onclick="togglePlayPause()">▶️ Play</button>
            <button class="btn btn-secondary" id="nextBtn" onclick="nextSlide()">Next ⏭</button>
            <div class="slide-info"><span class="current-slide" id="currentSlide">1</span> / <span id="totalSlides">{total_slides}</span></div>
            <div class="audio-time"><span id="currentTime">0:00</span> / <span id="duration">0:00</span></div>
        </div>
    </div>

    <audio id="audioPlayer"></audio>

    <script>
        const TOTAL_SLIDES = {total_slides};
        const AUDIO_PATH = 'output/audio/';
        const SLIDES_PATH = 'output/slides/';

        let currentSlide = 0;
        let isPlaying = false;
        let audio = document.getElementById('audioPlayer');
        let transcriptOpen = false;

        const slideTitles = {slide_titles_json};
        const transcripts = {transcripts_json};

        function formatTime(seconds) {{
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${{mins}}:${{secs.toString().padStart(2, '0')}}`;
        }}

        function toggleTranscript() {{
            const panel = document.getElementById('transcriptPanel');
            const container = document.getElementById('slideContainer');
            const btn = document.querySelector('.transcript-toggle');
            transcriptOpen = !transcriptOpen;
            if (transcriptOpen) {{
                panel.classList.add('open');
                container.classList.add('with-transcript');
                btn.textContent = '✖ Hide Transcript';
            }} else {{
                panel.classList.remove('open');
                container.classList.remove('with-transcript');
                btn.textContent = '📄 Show Transcript';
            }}
        }}

        function updateTranscript() {{
            document.getElementById('transcriptSlideTitle').textContent = `Slide ${{currentSlide + 1}}: ${{slideTitles[currentSlide]}}`;
            document.getElementById('transcriptContent').innerHTML = `<p>${{transcripts[currentSlide]}}</p>`;
        }}

        function updateUI() {{
            document.getElementById('slideImage').src = `${{SLIDES_PATH}}slide_${{currentSlide.toString().padStart(3, '0')}}.png`;
            document.getElementById('currentSlide').textContent = currentSlide + 1;
            document.getElementById('prevBtn').disabled = currentSlide === 0;
            document.getElementById('nextBtn').disabled = currentSlide === TOTAL_SLIDES - 1;
            updateTranscript();
        }}

        function loadSlide(slideIndex) {{
            currentSlide = slideIndex;
            audio.src = `${{AUDIO_PATH}}slide_${{slideIndex.toString().padStart(3, '0')}}.mp3`;
            updateUI();
            document.getElementById('status').textContent = `Loading slide ${{slideIndex + 1}}...`;
            if (isPlaying) {{
                audio.play().then(() => {{
                    document.getElementById('status').textContent = `Playing slide ${{slideIndex + 1}}`;
                }}).catch(err => {{
                    console.error('Error:', err);
                    document.getElementById('status').textContent = 'Error loading audio';
                    isPlaying = false;
                    updatePlayButton();
                }});
            }} else {{
                document.getElementById('status').textContent = 'Ready';
            }}
        }}

        function togglePlayPause() {{
            if (isPlaying) {{
                audio.pause();
                isPlaying = false;
                document.getElementById('status').textContent = 'Paused';
            }} else {{
                audio.play().then(() => {{
                    isPlaying = true;
                    document.getElementById('status').textContent = `Playing slide ${{currentSlide + 1}}`;
                }}).catch(err => {{
                    console.error('Error:', err);
                    document.getElementById('status').textContent = 'Error playing audio';
                }});
            }}
            updatePlayButton();
        }}

        function updatePlayButton() {{
            document.getElementById('playPauseBtn').textContent = isPlaying ? '⏸ Pause' : '▶️ Play';
        }}

        function nextSlide() {{
            if (currentSlide < TOTAL_SLIDES - 1) loadSlide(currentSlide + 1);
        }}

        function previousSlide() {{
            if (currentSlide > 0) loadSlide(currentSlide - 1);
        }}

        audio.addEventListener('timeupdate', () => {{
            if (audio.duration) {{
                document.getElementById('progress').style.width = (audio.currentTime / audio.duration) * 100 + '%';
                document.getElementById('currentTime').textContent = formatTime(audio.currentTime);
                document.getElementById('duration').textContent = formatTime(audio.duration);
            }}
        }});

        audio.addEventListener('ended', () => {{
            document.getElementById('status').textContent = 'Slide complete';
            isPlaying = false;
            updatePlayButton();
            if (currentSlide < TOTAL_SLIDES - 1) {{
                setTimeout(() => {{
                    document.getElementById('status').textContent = 'Auto-advancing...';
                    nextSlide();
                    setTimeout(() => {{
                        if (!isPlaying) togglePlayPause();
                    }}, 500);
                }}, 1000);
            }} else {{
                document.getElementById('status').textContent = 'Lecture complete! 🎉';
            }}
        }});

        audio.addEventListener('loadedmetadata', () => {{
            document.getElementById('duration').textContent = formatTime(audio.duration);
        }});

        loadSlide(0);
        updateUI();
    </script>
</body>
</html>'''


if __name__ == "__main__":
    asyncio.run(main())
