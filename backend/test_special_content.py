#!/usr/bin/env python3
"""
Test script to extract and display special content from a PDF.

Usage:
    python test_special_content.py <path_to_pdf>
"""
import sys
from app.services.parsers import PDFParser


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_special_content.py <path_to_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    print(f"📄 Extracting special content from: {pdf_path}\n")

    parser = PDFParser()
    slides = parser.parse(pdf_path)

    # Collect all special content
    all_special = []
    for slide in slides:
        for special in slide.special_contents:
            all_special.append((slide.slide_index, special))

    print(f"✅ Found {len(all_special)} special content items across {len(slides)} slides\n")
    print("="*70)

    # Group by type
    by_type = {}
    for slide_idx, special in all_special:
        if special.content_type not in by_type:
            by_type[special.content_type] = []
        by_type[special.content_type].append((slide_idx, special))

    # Display summary
    print("\n📊 SUMMARY BY TYPE:")
    print("-"*70)
    for content_type, items in sorted(by_type.items()):
        print(f"{content_type.upper():15s}: {len(items)} items")

    # Display details
    print("\n\n📖 DETAILED LIST:")
    print("="*70)

    for slide_idx, special in all_special:
        number_str = f" {special.number}" if special.number else ""
        print(f"\n📍 Slide {slide_idx + 1} - {special.content_type.upper()}{number_str}")
        print("-"*70)
        # Show first 200 chars
        content_preview = special.content[:200] + "..." if len(special.content) > 200 else special.content
        print(content_preview)

    print("\n"+"="*70)
    print(f"✅ Total: {len(all_special)} special content items")


if __name__ == "__main__":
    main()
