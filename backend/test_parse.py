#!/usr/bin/env python3
"""
Test script to parse a PDF file and display results.

Usage:
    python test_parse.py <path_to_pdf>

Example:
    python test_parse.py ~/Desktop/lecture.pdf
"""
import sys
from pathlib import Path
from app.services.parsers import PDFParser


def main():
    # Check if file path was provided
    if len(sys.argv) < 2:
        print("❌ Error: Please provide a PDF file path")
        print()
        print("Usage:")
        print("  python test_parse.py <path_to_pdf>")
        print()
        print("Example:")
        print("  python test_parse.py ~/Desktop/my_lecture.pdf")
        print("  python test_parse.py ../documents/slides.pdf")
        sys.exit(1)

    # Get the PDF file path from command line
    pdf_path = sys.argv[1]

    # Check if file exists
    if not Path(pdf_path).exists():
        print(f"❌ Error: File not found: {pdf_path}")
        sys.exit(1)

    print(f"📄 Parsing PDF: {pdf_path}")
    print()

    try:
        # Create parser and parse the PDF
        parser = PDFParser()
        slides = parser.parse(pdf_path)

        print(f"✅ Successfully parsed {len(slides)} slides!")
        print("=" * 60)
        print()

        # Display summary of each slide
        for slide in slides:
            print(f"📑 Slide {slide.slide_index + 1} (Index: {slide.slide_index})")
            print(f"   Type: {slide.slide_type}")
            print(f"   Title: {slide.title or '(No title)'}")
            print(f"   Bullet points: {len(slide.bullet_points)}")
            print(f"   Images: {len(slide.images)}")
            print(f"   Text length: {len(slide.body_text)} characters")

            if slide.bullet_points:
                print(f"   Bullets preview:")
                for bullet in slide.bullet_points[:3]:  # Show first 3
                    print(f"     • {bullet[:60]}...")

            print()

        # Show detailed view of first slide
        print("=" * 60)
        print("DETAILED VIEW - First Slide:")
        print("=" * 60)
        first = slides[0]
        print(f"Title: {first.title}")
        print(f"Type: {first.slide_type}")
        print(f"Images: {len(first.images)}")
        print()
        print("Content preview:")
        print(first.body_text[:300] + "..." if len(first.body_text) > 300 else first.body_text)
        print()

        if first.images:
            print(f"Image details:")
            for img in first.images:
                print(f"  - {img.image_id}: {img.format}, {len(img.image_data or '')} bytes (base64)")

        print()
        print("=" * 60)
        print("✅ Parsing complete!")

    except Exception as e:
        print(f"❌ Error parsing PDF: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
