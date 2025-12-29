#!/usr/bin/env python3
"""Generate narrations for intro slides (title, outline, section header)."""
import asyncio
from pathlib import Path

from app.services.parsers import PDFParser
from app.services.ai import GeminiProvider
from app.services.narration_cache import NarrationCache
from app.config import settings


async def main():
    pdf_path = "/Users/skandavyassrinivasan/Downloads/728 S24/slides/3. Linear Inequalities and Polyhedra.pdf"

    print(f"🚀 GENERATING INTRO SLIDE NARRATIONS")
    print(f"📄 PDF: {pdf_path}")
    print("=" * 70)

    # Parse PDF
    print("\n📖 Parsing PDF...")
    parser = PDFParser()
    slides = parser.parse(pdf_path)
    print(f"✅ Parsed {len(slides)} slides")

    # Load cached data
    cache = NarrationCache()
    pdf_name = Path(pdf_path).stem
    cached_data = cache.load(pdf_name)

    if not cached_data:
        print("❌ No cached data found!")
        return

    narrations = cached_data.get('narrations', {})
    global_plan = cached_data.get('global_plan', {})

    # Generate narrations for intro slides
    gemini_provider = GeminiProvider(model=settings.gemini_model)

    print(f"\n🎤 Generating narrations for intro slides (0-2)...")

    # Slide 0: Title slide
    print(f"\n   Generating for Slide 1 (Title)...")
    slide_0 = slides[0]

    prompt_0 = f"""You are an expert lecturer. Generate a brief (~50-75 word) introduction narration for this title slide.

**SLIDE CONTENT:**
{slide_0.body_text}

**INSTRUCTIONS:**
- Introduce the lecture topic warmly
- Mention this is chapter 3 on Linear Inequalities and Polyhedra
- Keep it brief and welcoming
- NO instructor names or university names (for privacy)
- Convert all LaTeX/math to spoken form

Generate the narration now:"""

    response_0 = gemini_provider.model.generate_content(
        prompt_0,
        generation_config={"temperature": 0.4, "max_output_tokens": 200}
    )
    narration_0 = response_0.text.strip()
    narrations['0'] = narration_0
    print(f"      ✅ Generated ({len(narration_0.split())} words)")

    # Slide 1: Outline
    print(f"\n   Generating for Slide 2 (Outline)...")
    slide_1 = slides[1]

    prompt_1 = f"""You are an expert lecturer. Generate a brief (~75-100 word) narration for this outline slide.

**SLIDE CONTENT:**
{slide_1.body_text}

**INSTRUCTIONS:**
- Briefly preview the topics we'll cover
- Mention we'll start with section 3.4 (Affine combinations)
- Keep it conversational and encouraging
- NO instructor names
- Convert all LaTeX/math to spoken form

Generate the narration now:"""

    response_1 = gemini_provider.model.generate_content(
        prompt_1,
        generation_config={"temperature": 0.4, "max_output_tokens": 250}
    )
    narration_1 = response_1.text.strip()
    narrations['1'] = narration_1
    print(f"      ✅ Generated ({len(narration_1.split())} words)")

    # Slide 2: Section header
    print(f"\n   Generating for Slide 3 (Section Header)...")
    slide_2 = slides[2]

    prompt_2 = f"""You are an expert lecturer. Generate a brief (~40-60 word) transition narration for this section header slide.

**SLIDE CONTENT:**
{slide_2.body_text}

**INSTRUCTIONS:**
- Transition into section 3.4
- Explain this section is about affine combinations and dimension
- Keep it brief - just a transition
- Convert all LaTeX/math to spoken form

Generate the narration now:"""

    response_2 = gemini_provider.model.generate_content(
        prompt_2,
        generation_config={"temperature": 0.4, "max_output_tokens": 150}
    )
    narration_2 = response_2.text.strip()
    narrations['2'] = narration_2
    print(f"      ✅ Generated ({len(narration_2.split())} words)")

    # Save to cache
    print(f"\n💾 Saving to cache...")
    cache.save(pdf_name, narrations, global_plan)
    print(f"✅ Saved all narrations to cache")

    # Display results
    print(f"\n📝 GENERATED NARRATIONS:")
    print("=" * 70)

    for i in range(3):
        slide = slides[i]
        print(f"\n📍 SLIDE {i + 1}: {slide.title or '(No title)'}")
        print("-" * 70)
        print(f"🎤 {narrations[str(i)]}\n")

    print("=" * 70)
    print("✅ Intro narrations complete!")
    print(f"   Next: Run test_tts.py to regenerate audio files")


if __name__ == "__main__":
    asyncio.run(main())
