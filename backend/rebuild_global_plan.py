#!/usr/bin/env python3
"""Rebuild global plan with intro section support."""
import asyncio
from pathlib import Path

from app.services.parsers import PDFParser
from app.services.ai import GeminiProvider
from app.services.global_context_builder import GlobalContextBuilder
from app.services.narration_cache import NarrationCache
from app.config import settings


async def main():
    pdf_path = "/Users/skandavyassrinivasan/Downloads/728 S24/slides/3. Linear Inequalities and Polyhedra.pdf"

    print(f"🚀 REBUILDING GLOBAL PLAN WITH INTRO SECTION")
    print(f"📄 PDF: {pdf_path}")
    print("=" * 70)

    # Parse PDF
    print("\n📖 PHASE 1: Parsing PDF...")
    parser = PDFParser()
    slides = parser.parse(pdf_path)
    print(f"✅ Parsed {len(slides)} slides")

    # Only process first 5 slides to save time
    slides_subset = slides[:5]
    print(f"   Using first {len(slides_subset)} slides for testing")

    # Load existing cache to get structural/visual analysis
    cache = NarrationCache()
    pdf_name = Path(pdf_path).stem
    cached_data = cache.load(pdf_name)

    if not cached_data or 'global_plan' not in cached_data:
        print("❌ No cached global plan found! Run test_gemini.py first.")
        return

    old_global_plan = cached_data['global_plan']

    # Build context builder
    gemini_provider = GeminiProvider(model=settings.gemini_model)
    context_builder = GlobalContextBuilder(ai_provider=gemini_provider)

    # Manually build the global plan using cached structural/visual data
    print("\n🧠 PHASE 2: Building global plan with intro section...")

    # Import necessary models
    from app.models import GlobalContextPlan, Section, KeyDiagram, SectionNarrationStrategy, SlideNarrationStrategy

    # Recreate sections from cache
    sections = []
    for sec_data in old_global_plan.get('sections', []):
        sections.append(Section(
            title=sec_data['title'],
            start_slide=sec_data['start_slide'],
            end_slide=sec_data['end_slide'],
            summary=sec_data['summary'],
            key_concepts=sec_data.get('key_concepts', [])
        ))

    # Create global plan
    global_plan = GlobalContextPlan(
        lecture_title=old_global_plan.get('lecture_title', ''),
        total_slides=len(slides),
        sections=sections,
        topic_progression=old_global_plan.get('topic_progression', []),
        learning_objectives=old_global_plan.get('learning_objectives', []),
        terminology=old_global_plan.get('terminology', {}),
        prerequisites=old_global_plan.get('prerequisites', []),
        cross_references=old_global_plan.get('cross_references', {}),
        instructional_style=old_global_plan.get('instructional_style', ''),
        audience_level=old_global_plan.get('audience_level', ''),
        key_diagrams=[],
        special_contents=[]
    )

    # Build section strategies (this will now include intro section)
    print("   Building section strategies (including intro)...")
    section_strategies = await context_builder._build_section_strategies(slides, global_plan)
    global_plan.section_narration_strategies = section_strategies

    print(f"✅ Created {len(section_strategies)} section strategies")
    for strategy in section_strategies:
        print(f"   • {strategy.section_title}: slides {strategy.start_slide + 1}-{strategy.end_slide + 1}")

    # Save to cache
    print(f"\n💾 Saving updated global plan...")
    global_plan_dict = global_plan.model_dump()

    # Keep old narrations if any
    narrations = cached_data.get('narrations', {})

    cache.save(pdf_name, narrations, global_plan_dict)
    print(f"✅ Saved updated global plan to cache")

    print(f"\n✅ Global plan rebuilt!")
    print(f"   Next: Run regenerate_with_incremental.py to generate narrations")


if __name__ == "__main__":
    asyncio.run(main())
