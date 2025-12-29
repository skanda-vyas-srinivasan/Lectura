#!/usr/bin/env python3
"""
Test TTS audio generation with Edge TTS.

If you have cached narrations, this will use them.
Otherwise, you'll need to provide narration text manually.

Usage:
    python test_tts.py
"""
import asyncio
from pathlib import Path

from app.services.tts import EdgeTTSProvider
from app.services.narration_cache import NarrationCache


async def main():
    print("🎤 EDGE TTS - AUDIO GENERATION TEST")
    print("=" * 70)

    # Check for cached narrations
    cache = NarrationCache()
    pdf_name = "3 Linear Inequalities and Polyhedra"

    cached_data = cache.load(pdf_name)

    if cached_data and cached_data["narrations"]:
        print(f"\n✅ Found cached narrations for '{pdf_name}'")
        narrations = cached_data["narrations"]
        print(f"   Available slides: {list(narrations.keys())}")
    else:
        print(f"\n⚠️  No cached narrations found.")
        print(f"   Please run test_gemini.py first to generate narrations,")
        print(f"   or provide sample text below.")

        # Sample narration for testing
        narrations = {
            0: "Welcome to this course on Linear Optimization. This is a test narration."
        }
        print(f"\n   Using sample narration for testing...")

    # Initialize TTS provider
    print(f"\n🎤 Initializing Edge TTS...")
    tts = EdgeTTSProvider(voice="en-US-GuyNeural")  # Male US voice
    print(f"   Voice: {tts.voice}")

    # Create output directory
    output_dir = Path("output/audio")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate audio for first 5 slides (or all available)
    slides_to_generate = list(narrations.keys())[:5]

    print(f"\n🔊 Generating audio for {len(slides_to_generate)} slides...")
    print("=" * 70)

    for slide_idx in slides_to_generate:
        narration_text = narrations[slide_idx]
        output_path = output_dir / f"slide_{slide_idx:03d}.mp3"

        print(f"\n📝 Slide {slide_idx}:")
        print(f"   Text: {narration_text[:80]}{'...' if len(narration_text) > 80 else ''}")
        print(f"   Length: {len(narration_text)} chars, ~{len(narration_text.split())} words")
        print(f"   Generating audio...")

        try:
            await tts.generate_audio(narration_text, output_path)
            file_size = output_path.stat().st_size / 1024  # KB
            print(f"   ✅ Saved: {output_path} ({file_size:.1f} KB)")
        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("\n" + "=" * 70)
    print("✅ Audio generation complete!")
    print(f"\n📁 Audio files saved to: {output_dir.absolute()}")
    print(f"\n💡 TIP: You can play these files with any media player")
    print(f"   or use them in the slide viewer we'll build next!")

    # Show voice options
    print(f"\n🎭 Available voices:")
    print(f"   Male US:   en-US-GuyNeural")
    print(f"   Female US: en-US-JennyNeural")
    print(f"   Male UK:   en-GB-RyanNeural")
    print(f"   Female UK: en-GB-SoniaNeural")
    print(f"\n   To change voice, edit the 'voice' parameter in this script")


if __name__ == "__main__":
    asyncio.run(main())
