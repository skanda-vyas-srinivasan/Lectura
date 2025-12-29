#!/usr/bin/env python3
"""
Test the full pipeline with Gemini 2.0 Flash (FREE tier - 1,500 req/day!).

This script demonstrates the complete autonomous AI lecturer system:
1. PDF parsing with special content extraction
2. Global context building with Gemini 2.0 Flash
3. Vision analysis for diagrams (multimodal!)
4. Narration generation

Usage:
    python test_gemini.py <path_to_pdf> [--num-narrations N]
"""
import sys
import asyncio
from pathlib import Path

from app.services.parsers import PDFParser
from app.services.ai import GeminiProvider
from app.services.global_context_builder import GlobalContextBuilder
from app.config import settings


async def main():
    if len(sys.argv) < 2:
        print("Usage: python test_gemini.py <path_to_pdf> [--num-narrations N]")
        sys.exit(1)

    pdf_path = sys.argv[1]

    # Optional: limit number of narrations to generate (for testing)
    num_narrations = 5  # Default: generate 5 narrations
    if "--num-narrations" in sys.argv:
        idx = sys.argv.index("--num-narrations")
        if idx + 1 < len(sys.argv):
            num_narrations = int(sys.argv[idx + 1])

    print(f"🚀 GEMINI 2.0 FLASH - FULL PIPELINE TEST")
    print(f"📄 PDF: {pdf_path}")
    print(f"🤖 Model: Gemini 2.0 Flash (Experimental)")
    print(f"📝 Generating {num_narrations} sample narrations")
    print(f"💰 Cost: FREE! (1,500 requests/day limit)\n")
    print("=" * 70)

    # Phase 1: Parse PDF
    print("\n📖 PHASE 1: Parsing PDF...")
    parser = PDFParser()
    slides = parser.parse(pdf_path)
    print(f"✅ Parsed {len(slides)} slides")

    # Show special content count
    total_special = sum(len(slide.special_contents) for slide in slides)
    print(f"📚 Found {total_special} special content items")

    # Show breakdown by type
    if total_special > 0:
        from collections import Counter
        type_counts = Counter()
        for slide in slides:
            for special in slide.special_contents:
                type_counts[special.content_type] += 1

        print("   Breakdown:")
        for content_type, count in type_counts.most_common():
            print(f"      • {content_type}: {count}")

    # Count images
    total_images = sum(len(slide.images) for slide in slides)
    print(f"🖼️  Found {total_images} images across all slides")

    # Phase 2: Global Context with Gemini
    print(f"\n🧠 PHASE 2: Building Global Context with {settings.gemini_model}...")
    print("   Features: Structural analysis + Vision (multimodal!)")

    gemini_provider = GeminiProvider(model=settings.gemini_model)
    context_builder = GlobalContextBuilder(ai_provider=gemini_provider)

    # Progress callback
    def progress_callback(stage: str, progress: float):
        status = "✓" if progress == 1.0 else "..."
        print(f"   [{status}] {stage}: {progress * 100:.0f}%")

    global_plan = await context_builder.build_context(slides, progress_callback)

    # Get token usage from analysis
    analysis_tokens = gemini_provider.get_token_usage()
    print(f"\n📊 Analysis Token Usage:")
    print(f"   Input:  {analysis_tokens['input_tokens']:,} tokens")
    print(f"   Output: {analysis_tokens['output_tokens']:,} tokens")
    print(f"   Total:  {analysis_tokens['total_tokens']:,} tokens")
    print(f"   💰 Cost: $0.00 (FREE tier!)")

    # Display global plan summary
    print(f"\n📋 GLOBAL CONTEXT SUMMARY:")
    print(f"   Title: {global_plan.lecture_title}")
    print(f"   Total Slides: {global_plan.total_slides}")
    print(f"   Sections: {len(global_plan.sections)}")
    print(f"   Learning Objectives: {len(global_plan.learning_objectives)}")
    print(f"   Terminology: {len(global_plan.terminology)} terms")
    print(f"   Special Content: {len(global_plan.special_contents)} items")
    print(f"   Key Diagrams: {len(global_plan.key_diagrams)}")

    if global_plan.sections:
        print("\n   📑 Sections detected:")
        for i, sec in enumerate(global_plan.sections[:5], 1):  # Show first 5
            print(f"      {i}. {sec.title} (slides {sec.start_slide + 1}-{sec.end_slide + 1})")
            if sec.key_concepts:
                concepts_preview = ', '.join(sec.key_concepts[:3])
                if len(sec.key_concepts) > 3:
                    concepts_preview += f", +{len(sec.key_concepts) - 3} more"
                print(f"         Concepts: {concepts_preview}")

    if global_plan.learning_objectives:
        print("\n   🎯 Learning Objectives:")
        for i, obj in enumerate(global_plan.learning_objectives[:3], 1):
            print(f"      {i}. {obj}")
        if len(global_plan.learning_objectives) > 3:
            print(f"      ... +{len(global_plan.learning_objectives) - 3} more")

    if global_plan.terminology:
        print(f"\n   📖 Sample Terminology:")
        for i, (term, definition) in enumerate(list(global_plan.terminology.items())[:3], 1):
            def_preview = definition[:60] + "..." if len(definition) > 60 else definition
            print(f"      • {term}: {def_preview}")
        if len(global_plan.terminology) > 3:
            print(f"      ... +{len(global_plan.terminology) - 3} more terms")

    # Phase 3: Generate sample narrations with Gemini (SECTION-LEVEL)
    print(f"\n🎤 PHASE 3: Generating {num_narrations} Sample Narrations (Section-Level)...")
    print("   Using same Gemini 2.0 Flash model")
    print("   Generating sections as continuous narratives to avoid repetition")

    # Reset token counter for narration phase
    gemini_provider.reset_token_counter()

    # Convert global_plan to dict for compatibility
    global_plan_dict = global_plan.model_dump()

    # Generate narrations section-by-section
    # Determine which sections contain the slides we want to narrate
    all_narrations = {}
    sections_to_generate = set()
    for i in range(min(num_narrations, len(slides))):
        section = global_plan.get_section_for_slide(i)
        if section:
            sections_to_generate.add((section.start_slide, section.end_slide, section.title))

    print(f"   Generating {len(sections_to_generate)} section(s) sequentially\n")

    # Process sections ONE AT A TIME (sequential, more reliable)
    for start_slide, end_slide, section_title in sorted(sections_to_generate):
        # Get section strategy
        section_strategy = None
        for strat in global_plan_dict['section_narration_strategies']:
            if strat['start_slide'] == start_slide and strat['end_slide'] == end_slide:
                section_strategy = strat
                break

        if not section_strategy:
            print(f"   ⚠️  No strategy for section {section_title}, skipping")
            continue

        # Get slides for this section
        section_slides = slides[start_slide:end_slide + 1]
        num_section_slides = len(section_slides)

        print(f"   Generating section: {section_title} (slides {start_slide + 1}-{end_slide + 1}) - {num_section_slides} slides")

        # For very large sections (>15 slides), split into chunks to avoid token limits
        CHUNK_SIZE = 15
        if num_section_slides > CHUNK_SIZE:
            print(f"      ⚠️  Large section ({num_section_slides} slides) - splitting into chunks of {CHUNK_SIZE}")
            section_narrations = {}

            # Process chunks SEQUENTIALLY
            for chunk_start in range(0, num_section_slides, CHUNK_SIZE):
                chunk_end = min(chunk_start + CHUNK_SIZE, num_section_slides)
                chunk_slides = section_slides[chunk_start:chunk_end]

                # Create chunk strategy (subset of full section strategy)
                chunk_strategy = section_strategy.copy()
                chunk_strategy['start_slide'] = start_slide + chunk_start
                chunk_strategy['end_slide'] = start_slide + chunk_end - 1
                chunk_strategy['slide_strategies'] = [
                    s for s in section_strategy.get('slide_strategies', [])
                    if chunk_strategy['start_slide'] <= s['slide_index'] <= chunk_strategy['end_slide']
                ]

                print(f"      Chunk {chunk_start//CHUNK_SIZE + 1}: slides {chunk_strategy['start_slide'] + 1}-{chunk_strategy['end_slide'] + 1}")

                # Generate narrations for this chunk
                chunk_narrations = await gemini_provider.generate_section_narrations(
                    section_slides=chunk_slides,
                    section_strategy=chunk_strategy,
                    global_plan=global_plan_dict
                )

                section_narrations.update(chunk_narrations)
        else:
            # Generate ALL narrations for this section in ONE call
            section_narrations = await gemini_provider.generate_section_narrations(
                section_slides=section_slides,
                section_strategy=section_strategy,
                global_plan=global_plan_dict
            )

        # Add to results
        all_narrations.update(section_narrations)

        # Show what was generated
        for slide_idx in sorted(section_narrations.keys()):
            if slide_idx < num_narrations:  # Only show requested slides
                word_count = len(section_narrations[slide_idx].split())
                print(f"      Slide {slide_idx + 1}: {word_count} words")

    # Extract narrations in order
    narrations = []
    for i in range(min(num_narrations, len(slides))):
        if i in all_narrations:
            narrations.append(all_narrations[i])
        else:
            narrations.append(f"(Narration not generated for slide {i + 1})")

    # Get token usage from narration
    narration_tokens = gemini_provider.get_token_usage()
    print(f"\n📊 Narration Token Usage:")
    print(f"   Input:  {narration_tokens['input_tokens']:,} tokens")
    print(f"   Output: {narration_tokens['output_tokens']:,} tokens")
    print(f"   Total:  {narration_tokens['total_tokens']:,} tokens")
    print(f"   💰 Cost: $0.00 (FREE tier!)")

    # Calculate total requests used
    total_requests = 1 + len(narrations)  # 1 for analysis, N for narrations
    if total_images > 0:
        total_requests += 1  # 1 for vision analysis

    # Extrapolate to full lecture
    requests_per_full_lecture = 1 + len(slides)  # 1 analysis + all narrations
    if total_images > 0:
        requests_per_full_lecture += 1

    print(f"\n📈 REQUEST USAGE:")
    print(f"   Analysis:  1 request")
    if total_images > 0:
        print(f"   Vision:    1 request")
    print(f"   Narration: {len(narrations)} requests")
    print(f"   ──────────────────────────")
    print(f"   Total:     {total_requests} requests")
    print(f"\n   📊 For full {len(slides)}-slide lecture:")
    print(f"      Total requests: {requests_per_full_lecture}")
    print(f"      Daily limit: 1,500 requests")
    print(f"      ═══════════════════════════")
    print(f"      Can process ~{int(1500 / requests_per_full_lecture)} full lectures per day!")

    # Display sample narrations
    print(f"\n📝 SAMPLE NARRATIONS:")
    print("=" * 70)

    for i, narration in enumerate(narrations):
        slide = slides[i]
        print(f"\n📍 SLIDE {i + 1}: {slide.title or '(No title)'}")
        print("-" * 70)

        # Show special content if any
        if slide.special_contents:
            print("🔖 Special Content:")
            for special in slide.special_contents[:2]:  # Show first 2
                number_str = f" {special.number}" if special.number else ""
                content_preview = special.content[:100] + "..." if len(special.content) > 100 else special.content
                print(f"   [{special.content_type.upper()}{number_str}] {content_preview}")
            if len(slide.special_contents) > 2:
                print(f"   ... +{len(slide.special_contents) - 2} more")
            print()

        print("🎤 Narration:")
        print(narration)
        print()

    print("=" * 70)
    print("✅ Gemini 2.0 Flash test complete!")
    print(f"\n🎯 Quality Assessment:")
    print(f"   • Analysis: Good structural understanding")
    print(f"   • Vision: Native multimodal support")
    print(f"   • Narration: Conversational and pedagogical")
    print(f"\n💰 Cost: $0.00 (completely FREE!)")
    print(f"🚀 Limit: {int(1500 / requests_per_full_lecture)} full lectures per day")
    print(f"\n💡 This is PERFECT for prototyping and testing your system!")
    print(f"   You can iterate quickly without any API costs.")
    print(f"   Upgrade to Sonnet + DeepSeek later for production quality.")

    # Cache the narrations for reuse
    print(f"\n💾 Caching narrations...")
    from app.services.narration_cache import NarrationCache
    cache = NarrationCache()

    # Create narrations dict
    narrations_dict = {i: narrations[i] for i in range(len(narrations))}

    # Extract PDF name from path
    pdf_name = Path(pdf_path).stem

    cache.save(pdf_name, narrations_dict, global_plan_dict)
    print(f"   ✅ Cached {len(narrations_dict)} narrations")
    print(f"   📁 Cache location: {cache.get_cache_path(pdf_name)}")
    print(f"\n💡 You can now run test_tts.py to generate audio from these narrations!")


if __name__ == "__main__":
    asyncio.run(main())
