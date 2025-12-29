#!/usr/bin/env python3
"""Regenerate first 5 narrations with incremental build detection."""
import asyncio
import sys
from pathlib import Path

from app.services.parsers import PDFParser
from app.services.ai import GeminiProvider
from app.services.narration_cache import NarrationCache
from app.config import settings


async def main():
    pdf_path = "/Users/skandavyassrinivasan/Downloads/728 S24/slides/3. Linear Inequalities and Polyhedra.pdf"
    num_slides = 5

    print(f"🚀 REGENERATING NARRATIONS WITH INCREMENTAL BUILD DETECTION")
    print(f"📄 PDF: {pdf_path}")
    print(f"📝 Slides to regenerate: {num_slides}")
    print("=" * 70)

    # Parse PDF (this now detects incremental builds)
    print("\n📖 PHASE 1: Parsing PDF...")
    parser = PDFParser()
    slides = parser.parse(pdf_path)
    print(f"✅ Parsed {len(slides)} slides")

    # Show incremental builds in first 5 slides
    for i in range(min(num_slides, len(slides))):
        slide = slides[i]
        if slide.is_incremental_build:
            print(f"   🔄 Slide {i + 1} is incremental build (builds on Slide {slide.previous_slide_index + 1})")

    # Load cached global plan (to avoid regenerating it)
    print(f"\n💾 Loading cached global plan...")
    cache = NarrationCache()
    pdf_name = Path(pdf_path).stem
    cached_data = cache.load(pdf_name)

    if not cached_data or 'global_plan' not in cached_data:
        print("❌ No cached global plan found! Run test_gemini.py first.")
        return

    global_plan = cached_data['global_plan']
    print(f"✅ Loaded global plan")

    # Generate narrations for sections containing first 5 slides
    print(f"\n🎤 PHASE 2: Generating narrations with incremental build awareness...")

    gemini_provider = GeminiProvider(model=settings.gemini_model)

    # Find which sections contain our slides
    sections_to_generate = set()
    for i in range(num_slides):
        for strategy in global_plan.get('section_narration_strategies', []):
            if strategy['start_slide'] <= i <= strategy['end_slide']:
                sections_to_generate.add((strategy['start_slide'], strategy['end_slide'], strategy['section_title']))
                break

    print(f"   Will generate {len(sections_to_generate)} section(s)")

    all_narrations = {}

    for start_slide, end_slide, section_title in sorted(sections_to_generate):
        # Get section strategy
        section_strategy = None
        for strat in global_plan['section_narration_strategies']:
            if strat['start_slide'] == start_slide and strat['end_slide'] == end_slide:
                section_strategy = strat
                break

        if not section_strategy:
            print(f"   ⚠️  No strategy for section {section_title}, skipping")
            continue

        # Get slides for this section
        section_slides = slides[start_slide:end_slide + 1]

        print(f"\n   Generating section: {section_title} (slides {start_slide + 1}-{end_slide + 1})...")

        # Check if any are incremental builds
        incremental_count = sum(1 for s in section_slides if s.is_incremental_build)
        if incremental_count > 0:
            print(f"      ⚠️  Contains {incremental_count} incremental build(s)")

        # Generate ALL narrations for this section in ONE call
        section_narrations = await gemini_provider.generate_section_narrations(
            section_slides=section_slides,
            section_strategy=section_strategy,
            global_plan=global_plan
        )

        # Add to results
        all_narrations.update(section_narrations)

        # Show what was generated
        for slide_idx in sorted(section_narrations.keys()):
            if slide_idx < num_slides:  # Only show first 5
                slide = slides[slide_idx]
                word_count = len(section_narrations[slide_idx].split())
                incremental_marker = " [INCREMENTAL]" if slide.is_incremental_build else ""
                print(f"      Slide {slide_idx + 1}{incremental_marker}: {word_count} words")

    # Show sample narrations
    print(f"\n📝 GENERATED NARRATIONS:")
    print("=" * 70)

    for i in range(num_slides):
        if i in all_narrations:
            slide = slides[i]
            print(f"\n📍 SLIDE {i + 1}: {slide.title or '(No title)'}")
            if slide.is_incremental_build:
                print(f"   ⚠️  INCREMENTAL BUILD (builds on Slide {slide.previous_slide_index + 1})")
            print("-" * 70)
            print(f"🎤 {all_narrations[i]}")

    # Save to cache
    print(f"\n💾 Saving to cache...")
    narrations_dict = {i: all_narrations.get(i, f"(Not generated for slide {i + 1})") for i in range(num_slides)}
    cache.save(pdf_name, narrations_dict, global_plan)
    print(f"✅ Saved {len(narrations_dict)} narrations to cache")

    print(f"\n✅ Regeneration complete!")
    print(f"   Next: Run test_tts.py to generate audio files")


if __name__ == "__main__":
    asyncio.run(main())
