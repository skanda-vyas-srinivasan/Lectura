#!/usr/bin/env python3
"""Quick test of incremental build narration for slides 3-4."""
import asyncio
import sys
from pathlib import Path

from app.services.parsers import PDFParser
from app.services.ai import GeminiProvider
from app.config import settings


async def main():
    pdf_path = "/Users/skandavyassrinivasan/Downloads/728 S24/slides/3. Linear Inequalities and Polyhedra.pdf"

    print(f"🚀 TESTING INCREMENTAL BUILD NARRATION")
    print(f"📄 PDF: {pdf_path}")
    print("=" * 70)

    # Parse PDF (this now detects incremental builds)
    print("\n📖 Parsing PDF...")
    parser = PDFParser()
    slides = parser.parse(pdf_path)
    print(f"✅ Parsed {len(slides)} slides")

    # Focus on slides 3-4 (indices 3-4)
    slide_3 = slides[3]
    slide_4 = slides[4]

    print(f"\n📊 Slide {slide_3.slide_index + 1}:")
    print(f"   Title: {slide_3.title}")
    print(f"   Incremental Build: {slide_3.is_incremental_build}")
    print(f"   Content length: {len(slide_3.raw_markdown)} chars")

    print(f"\n📊 Slide {slide_4.slide_index + 1}:")
    print(f"   Title: {slide_4.title}")
    print(f"   Incremental Build: {slide_4.is_incremental_build}")
    print(f"   Previous Slide: {slide_4.previous_slide_index}")
    print(f"   Content length: {len(slide_4.raw_markdown)} chars")
    print(f"   NEW content only: {slide_4.new_content_only}")

    # Load cached global plan
    print(f"\n💾 Loading cached global plan...")
    from app.services.narration_cache import NarrationCache
    cache = NarrationCache()
    pdf_name = Path(pdf_path).stem

    cached_data = cache.load(pdf_name)
    if not cached_data or 'global_plan' not in cached_data:
        print("❌ No cached global plan found!")
        return

    global_plan = cached_data['global_plan']
    print(f"✅ Loaded global plan")

    # Find the section strategy for slides 3-4
    section_strategy = None
    for strategy in global_plan.get('section_narration_strategies', []):
        if strategy['start_slide'] <= 3 and strategy['end_slide'] >= 4:
            section_strategy = strategy
            break

    if not section_strategy:
        print("❌ No section strategy found for slides 3-4!")
        return

    print(f"\n📋 Section Strategy:")
    print(f"   Section: {section_strategy['section_title']}")
    print(f"   Slides: {section_strategy['start_slide'] + 1} - {section_strategy['end_slide'] + 1}")

    # Generate narrations using Gemini
    print(f"\n🎤 Generating narrations for slides 3-4 with incremental build awareness...")

    gemini_provider = GeminiProvider(model=settings.gemini_model)

    # Get section slides
    section_slides = slides[section_strategy['start_slide']:section_strategy['end_slide'] + 1]

    # Generate narrations
    narrations = await gemini_provider.generate_section_narrations(
        section_slides=section_slides,
        section_strategy=section_strategy,
        global_plan=global_plan
    )

    # Show results
    print("\n" + "=" * 70)
    print("📝 GENERATED NARRATIONS")
    print("=" * 70)

    for slide_idx in [3, 4]:
        if slide_idx in narrations:
            slide = slides[slide_idx]
            print(f"\n📍 SLIDE {slide_idx + 1}: {slide.title}")
            if slide.is_incremental_build:
                print(f"   ⚠️  INCREMENTAL BUILD (builds on Slide {slide.previous_slide_index + 1})")
            print("-" * 70)
            print(f"🎤 Narration:\n{narrations[slide_idx]}\n")

    print("=" * 70)
    print("✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(main())
