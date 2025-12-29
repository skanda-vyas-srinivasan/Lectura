#!/usr/bin/env python3
"""
Interactive PDF parser test script.
Prompts user for PDF file path.
"""
from pathlib import Path
from app.services.parsers import PDFParser


def main():
    print("=" * 60)
    print("PDF Parser Test - Interactive Mode")
    print("=" * 60)
    print()

    # Prompt for file path
    pdf_path = input("Enter the path to your PDF file: ").strip()

    # Remove quotes if user copied a path with quotes
    pdf_path = pdf_path.strip('"').strip("'")

    # Check if file exists
    path = Path(pdf_path)
    if not path.exists():
        print(f"\n❌ Error: File not found: {pdf_path}")
        print("\nTip: You can drag and drop the file into the terminal")
        return

    print(f"\n📄 Parsing: {path.name}")
    print()

    try:
        parser = PDFParser()
        slides = parser.parse(pdf_path)

        print(f"✅ Successfully parsed {len(slides)} slides!\n")

        # Show summary
        for i, slide in enumerate(slides, 1):
            print(f"{i}. {slide.title or '(Untitled)'} [{slide.slide_type}]")
            if slide.bullet_points:
                print(f"   • {len(slide.bullet_points)} bullet points")
            if slide.images:
                print(f"   • {len(slide.images)} images")

        print(f"\n✅ Done! Created {len(slides)} SlideContent objects")

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
