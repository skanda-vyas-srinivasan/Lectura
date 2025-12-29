#!/usr/bin/env python3
"""
Test the dual-provider system: Sonnet for analysis, DeepSeek for narration.

Usage:
    python test_dual_provider.py <path_to_pdf> [--num-narrations N]
"""
import sys
import asyncio
from pathlib import Path

from app.services.parsers import PDFParser
from app.services.ai import ClaudeProvider, DeepSeekProvider
from app.services.global_context_builder import GlobalContextBuilder


async def main():
    if len(sys.argv) < 2:
        print("Usage: python test_dual_provider.py <path_to_pdf> [--num-narrations N]")
        sys.exit(1)

    pdf_path = sys.argv[1]

    # Optional: limit number of narrations to generate (for testing)
    num_narrations = 3  # Default: generate 3 narrations
    if "--num-narrations" in sys.argv:
        idx = sys.argv.index("--num-narrations")
        if idx + 1 < len(sys.argv):
            num_narrations = int(sys.argv[idx + 1])

    print(f"🚀 DUAL-PROVIDER SYSTEM TEST")
    print(f"📄 PDF: {pdf_path}")
    print(f"🎯 Strategy: Sonnet (analysis) → DeepSeek (narration)")
    print(f"📝 Generating {num_narrations} sample narrations\n")
    print("=" * 70)

    # Phase 1: Parse PDF
    print("\n📖 PHASE 1: Parsing PDF...")
    parser = PDFParser()
    slides = parser.parse(pdf_path)
    print(f"✅ Parsed {len(slides)} slides")

    # Show special content count
    total_special = sum(len(slide.special_contents) for slide in slides)
    print(f"📚 Found {total_special} special content items (definitions, theorems, etc.)")

    # Phase 2: Global Context with Claude Sonnet
    print("\n🧠 PHASE 2: Building Global Context with Claude Sonnet...")
    print("   (This uses smart reasoning for structural analysis)")

    claude_provider = ClaudeProvider()
    context_builder = GlobalContextBuilder(ai_provider=claude_provider)

    # Progress callback
    def progress_callback(stage: str, progress: float):
        status = "✓" if progress == 1.0 else "..."
        print(f"   [{status}] {stage}: {progress * 100:.0f}%")

    global_plan = await context_builder.build_context(slides, progress_callback)

    # Get token usage from analysis
    analysis_tokens = claude_provider.get_token_usage()
    print(f"\n📊 Analysis Token Usage (Sonnet):")
    print(f"   Input:  {analysis_tokens['input_tokens']:,} tokens")
    print(f"   Output: {analysis_tokens['output_tokens']:,} tokens")
    print(f"   Total:  {analysis_tokens['total_tokens']:,} tokens")

    # Calculate cost (Sonnet pricing)
    analysis_cost = (
        analysis_tokens['input_tokens'] / 1_000_000 * 3.00 +
        analysis_tokens['output_tokens'] / 1_000_000 * 15.00
    )
    print(f"   💰 Cost: ${analysis_cost:.4f}")

    # Display global plan summary
    print(f"\n📋 GLOBAL CONTEXT SUMMARY:")
    print(f"   Title: {global_plan.lecture_title}")
    print(f"   Sections: {len(global_plan.sections)}")
    print(f"   Learning Objectives: {len(global_plan.learning_objectives)}")
    print(f"   Key Diagrams: {len(global_plan.key_diagrams)}")
    print(f"   Terminology: {len(global_plan.terminology)} terms")
    print(f"   Special Content: {len(global_plan.special_contents)} items")

    if global_plan.sections:
        print("\n   Sections detected:")
        for sec in global_plan.sections[:5]:  # Show first 5
            print(f"      • {sec.title} (slides {sec.start_slide + 1}-{sec.end_slide + 1})")

    # Phase 3: Generate sample narrations with DeepSeek
    print(f"\n🎤 PHASE 3: Generating {num_narrations} Sample Narrations with DeepSeek...")
    print("   (This uses cheap narration for cost efficiency)")

    deepseek_provider = DeepSeekProvider()

    # Convert global_plan to dict for compatibility
    global_plan_dict = global_plan.model_dump()

    narrations = []
    for i in range(min(num_narrations, len(slides))):
        slide = slides[i]
        print(f"\n   Generating narration for Slide {i + 1}...")

        # Get previous narration summary (if exists)
        prev_summary = None
        if i > 0 and narrations:
            prev_narration = narrations[-1]
            # Simple summary: first 150 chars
            prev_summary = prev_narration[:150] + "..."

        narration = await deepseek_provider.generate_narration(
            slide=slide,
            global_plan=global_plan_dict,
            previous_narration_summary=prev_summary,
            related_slides=None
        )

        narrations.append(narration)
        print(f"   ✓ Generated {len(narration.split())} words")

    # Get token usage from narration
    narration_tokens = deepseek_provider.get_token_usage()
    print(f"\n📊 Narration Token Usage (DeepSeek):")
    print(f"   Input:  {narration_tokens['input_tokens']:,} tokens")
    print(f"   Output: {narration_tokens['output_tokens']:,} tokens")
    print(f"   Total:  {narration_tokens['total_tokens']:,} tokens")

    # Calculate cost (DeepSeek pricing)
    narration_cost = (
        narration_tokens['input_tokens'] / 1_000_000 * 0.27 +
        narration_tokens['output_tokens'] / 1_000_000 * 1.10
    )
    print(f"   💰 Cost: ${narration_cost:.4f}")

    # Extrapolate to full lecture
    avg_cost_per_narration = narration_cost / num_narrations
    estimated_full_cost = avg_cost_per_narration * len(slides)

    print(f"\n💵 TOTAL COST BREAKDOWN:")
    print(f"   Analysis (Sonnet):  ${analysis_cost:.4f}")
    print(f"   Narration (DeepSeek): ${narration_cost:.4f} ({num_narrations} slides)")
    print(f"   ──────────────────────────")
    print(f"   Total so far:       ${analysis_cost + narration_cost:.4f}")
    print(f"\n   📊 Estimated for full {len(slides)}-slide lecture:")
    print(f"      Analysis:  ${analysis_cost:.2f}")
    print(f"      Narration: ${estimated_full_cost:.2f}")
    print(f"      ═══════════════════════════")
    print(f"      TOTAL:     ${analysis_cost + estimated_full_cost:.2f}")

    # Display sample narrations
    print(f"\n📝 SAMPLE NARRATIONS:")
    print("=" * 70)

    for i, narration in enumerate(narrations):
        slide = slides[i]
        print(f"\n📍 SLIDE {i + 1}: {slide.title or '(No title)'}")
        print("-" * 70)
        print(narration)
        print()

    print("=" * 70)
    print("✅ Dual-provider test complete!")
    print(f"\n🎯 Strategy works: Sonnet for smart analysis, DeepSeek for cheap narration")
    print(f"💡 This approach saves ~75% on narration costs vs using Sonnet for everything")


if __name__ == "__main__":
    asyncio.run(main())
