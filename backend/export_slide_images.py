#!/usr/bin/env python3
"""
Extract PDF slides as PNG images for the viewer.

Usage:
    python export_slide_images.py <path_to_pdf>
"""
import sys
from pathlib import Path
import fitz  # PyMuPDF


def export_slides_as_images(pdf_path: str, output_dir: str = "output/slides", dpi: int = 150):
    """
    Export each PDF page as a PNG image.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save slide images
        dpi: Resolution for images (150 is good for web viewing)
    """
    print(f"📄 Extracting slides from: {pdf_path}")

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Open PDF
    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    print(f"📊 Found {total_pages} slides")
    print(f"💾 Saving to: {output_path.absolute()}\n")

    # Calculate zoom factor for DPI
    # PyMuPDF default is 72 DPI, so zoom = target_dpi / 72
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    for page_num in range(total_pages):
        page = doc[page_num]

        # Render page to pixmap (image)
        pix = page.get_pixmap(matrix=mat)

        # Save as PNG
        output_file = output_path / f"slide_{page_num:03d}.png"
        pix.save(output_file)

        # Get image dimensions
        width, height = pix.width, pix.height
        size_kb = len(pix.tobytes()) / 1024

        print(f"  ✅ Slide {page_num + 1:2d}: {output_file.name} ({width}x{height}px, {size_kb:.1f} KB)")

    doc.close()

    print(f"\n✨ Exported {total_pages} slides successfully!")
    print(f"📁 Location: {output_path.absolute()}")

    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python export_slide_images.py <path_to_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    if not Path(pdf_path).exists():
        print(f"❌ Error: PDF not found at {pdf_path}")
        sys.exit(1)

    export_slides_as_images(pdf_path)
