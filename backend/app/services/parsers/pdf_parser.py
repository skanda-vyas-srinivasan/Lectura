"""PDF parser using pymupdf4llm for text and PyMuPDF for images."""
import re
import base64
from pathlib import Path
from typing import List, Optional
import pymupdf4llm
import fitz  # PyMuPDF
from PIL import Image
import io

from app.models import SlideContent, ImageContent, SlideType, SpecialContent, SpecialContentType
from app.services.parsers.base import BaseParser
from app.services.incremental_build_detector import detect_incremental_builds


class PDFParser(BaseParser):
    """
    Parser for PDF documents.

    Uses pymupdf4llm for high-quality markdown text extraction
    and PyMuPDF (fitz) for image extraction.
    """

    def __init__(self):
        """Initialize the PDF parser."""
        self.supported_image_formats = ["png", "jpg", "jpeg"]

    def validate_file(self, file_path: str | Path) -> bool:
        """
        Validate that the file is a valid PDF.

        Args:
            file_path: Path to the PDF file

        Returns:
            True if valid PDF, False otherwise
        """
        path = Path(file_path)

        if not path.exists():
            return False

        if path.suffix.lower() != ".pdf":
            return False

        try:
            # Try to open with PyMuPDF to verify it's valid
            doc = fitz.open(str(path))
            doc.close()
            return True
        except Exception:
            return False

    def parse(self, file_path: str | Path) -> List[SlideContent]:
        """
        Parse PDF file and extract slide content.

        Args:
            file_path: Path to the PDF file

        Returns:
            List of SlideContent objects, one per page

        Raises:
            FileNotFoundError: If PDF doesn't exist
            ValueError: If PDF is invalid or corrupted
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        if not self.validate_file(file_path):
            raise ValueError(f"Invalid or corrupted PDF file: {file_path}")

        try:
            # Open PDF with PyMuPDF
            doc = fitz.open(str(path))

            slides = []
            for page_num in range(doc.page_count):
                page = doc[page_num]

                # Extract text per-page using PyMuPDF directly
                # This is more reliable than pymupdf4llm's page splitting
                page_text = page.get_text("text")  # Plain text

                # Try to get markdown from pymupdf4llm for this specific page
                try:
                    # Extract just this page as markdown
                    page_md_dict = pymupdf4llm.to_markdown(str(path), pages=[page_num])
                    page_md = page_md_dict if isinstance(page_md_dict, str) else page_text
                except:
                    # Fallback to plain text if pymupdf4llm fails
                    page_md = page_text

                # Extract images from this page
                images = self._extract_images_from_page(page, page_num)

                # Create SlideContent model
                slide = self._create_slide_content(
                    page_num=page_num,
                    markdown_text=page_md,
                    images=images,
                )

                slides.append(slide)

            doc.close()

            # Detect incremental builds (slides that progressively reveal content)
            slides = detect_incremental_builds(slides)

            return slides

        except Exception as e:
            raise ValueError(f"Error parsing PDF: {str(e)}")

    def _split_markdown_by_pages(self, markdown: str, page_count: int) -> List[str]:
        """
        Split markdown content by pages.

        pymupdf4llm adds page markers like '-----\n\n' between pages.

        Args:
            markdown: Complete markdown content
            page_count: Number of pages in the PDF

        Returns:
            List of markdown strings, one per page
        """
        # Split by the page separator that pymupdf4llm uses
        pages = re.split(r'\n---+\n', markdown)

        # Ensure we have the right number of pages
        while len(pages) < page_count:
            pages.append("")

        return pages[:page_count]

    def _extract_images_from_page(
        self, page: fitz.Page, page_num: int
    ) -> List[ImageContent]:
        """
        Extract all images from a PDF page.

        Args:
            page: PyMuPDF page object
            page_num: Page number (0-indexed)

        Returns:
            List of ImageContent objects
        """
        images = []
        image_list = page.get_images(full=True)

        for img_index, img_info in enumerate(image_list):
            try:
                xref = img_info[0]  # Image reference number
                base_image = page.parent.extract_image(xref)

                if base_image:
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    # Convert to base64 for storage
                    image_b64 = base64.b64encode(image_bytes).decode('utf-8')

                    # Get image position on page
                    image_rects = page.get_image_rects(xref)
                    position = {}
                    if image_rects:
                        rect = image_rects[0]
                        position = {
                            "x": rect.x0,
                            "y": rect.y0,
                            "width": rect.width,
                            "height": rect.height,
                        }

                    image_content = ImageContent(
                        image_id=f"page{page_num}_img{img_index}",
                        image_data=image_b64,
                        format=image_ext,
                        extracted_from_slide=page_num,
                        position=position,
                    )

                    images.append(image_content)

            except Exception as e:
                # Skip problematic images but continue processing
                print(f"Warning: Could not extract image {img_index} from page {page_num}: {e}")
                continue

        return images

    def _extract_special_content(
        self, text: str, slide_index: int
    ) -> List[SpecialContent]:
        """
        Detect and extract special content (definitions, theorems, corollaries, etc.).

        Args:
            text: Text content to search
            slide_index: Index of the current slide

        Returns:
            List of SpecialContent objects found in the text
        """
        special_items = []

        # Patterns to match various special content types
        # Format: (regex_pattern, content_type)
        # Use [\s\S] to match across multiple lines (including newlines)
        # Lookahead stops at: another keyword, double newline, or end of text

        # Build lookahead pattern that stops at next special content keyword
        next_keyword = r'(?=\n(?:Definition|Theorem|Corollary|Lemma|Proposition|Property|Proof|Example|Remark|Axiom|Claim|DEFINITION|THEOREM|COROLLARY|LEMMA|PROPOSITION|PROPERTY|PROOF|EXAMPLE|REMARK|AXIOM|CLAIM)\s*\d*\.?\d*:?|\Z)'

        patterns = [
            (rf'(?:Definition|DEFINITION)\s*(\d+\.?\d*)?:?\s*([\s\S]+?){next_keyword}', SpecialContentType.DEFINITION),
            (rf'(?:Theorem|THEOREM)\s*(\d+\.?\d*)?:?\s*([\s\S]+?){next_keyword}', SpecialContentType.THEOREM),
            (rf'(?:Corollary|COROLLARY)\s*(\d+\.?\d*)?:?\s*([\s\S]+?){next_keyword}', SpecialContentType.COROLLARY),
            (rf'(?:Lemma|LEMMA)\s*(\d+\.?\d*)?:?\s*([\s\S]+?){next_keyword}', SpecialContentType.LEMMA),
            (rf'(?:Proposition|PROPOSITION)\s*(\d+\.?\d*)?:?\s*([\s\S]+?){next_keyword}', SpecialContentType.PROPOSITION),
            (rf'(?:Property|PROPERTY)\s*(\d+\.?\d*)?:?\s*([\s\S]+?){next_keyword}', SpecialContentType.PROPERTY),
            (rf'(?:Proof|PROOF)\s*(\d+\.?\d*)?\.?\s*([\s\S]+?){next_keyword}', SpecialContentType.PROOF),
            (rf'(?:Example|EXAMPLE)\s*(\d+\.?\d*)?:?\s*([\s\S]+?){next_keyword}', SpecialContentType.EXAMPLE),
            (rf'(?:Remark|REMARK)\s*(\d+\.?\d*)?:?\s*([\s\S]+?){next_keyword}', SpecialContentType.REMARK),
            (rf'(?:Axiom|AXIOM)\s*(\d+\.?\d*)?:?\s*([\s\S]+?){next_keyword}', SpecialContentType.AXIOM),
            (rf'(?:Claim|CLAIM)\s*(\d+\.?\d*)?:?\s*([\s\S]+?){next_keyword}', SpecialContentType.CLAIM),
        ]

        for pattern, content_type in patterns:
            matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
            for match in matches:
                # Extract number if present
                number = match.group(1).strip() if match.group(1) else None

                # Extract content
                content = match.group(2).strip() if len(match.groups()) >= 2 else ""

                # Skip if content is too short (likely a false positive)
                if len(content) < 10:
                    continue

                # Skip if this is a reference, not a definition
                # References typically start with: "implies", "shows", "states", "proves", etc.
                reference_words = ['implies', 'shows', 'states', 'proves', 'guarantees', 'ensures', 'yields']
                if any(content.lower().startswith(word) for word in reference_words):
                    continue

                # Clean up content (remove excessive whitespace)
                content = re.sub(r'\s+', ' ', content)

                special_items.append(
                    SpecialContent(
                        content_type=content_type,
                        number=number,
                        content=content,
                        slide_index=slide_index,
                    )
                )

        return special_items

    def _create_slide_content(
        self,
        page_num: int,
        markdown_text: str,
        images: List[ImageContent],
    ) -> SlideContent:
        """
        Create a SlideContent object from extracted page data.

        Args:
            page_num: Page number (0-indexed)
            markdown_text: Markdown content of the page
            images: List of extracted images

        Returns:
            SlideContent object
        """
        # Extract title (first heading or first line)
        title = self._extract_title(markdown_text)

        # Extract bullet points
        bullet_points = self._extract_bullet_points(markdown_text)

        # Infer slide type
        slide_type = self._infer_slide_type(markdown_text, images, page_num)

        # Create body text (remove markdown formatting for plain text)
        body_text = self._markdown_to_plain_text(markdown_text)

        # Extract special content (definitions, theorems, etc.)
        special_contents = self._extract_special_content(markdown_text, page_num)

        return SlideContent(
            slide_index=page_num,
            slide_type=slide_type,
            title=title,
            bullet_points=bullet_points,
            body_text=body_text,
            images=images,
            special_contents=special_contents,
            raw_markdown=markdown_text,
        )

    def _extract_title(self, markdown: str) -> Optional[str]:
        """
        Extract title from markdown (first heading or first line).

        Args:
            markdown: Markdown text

        Returns:
            Title string or None
        """
        if not markdown.strip():
            return None

        # Look for markdown headings (# Title)
        heading_match = re.search(r'^#+\s+(.+)$', markdown, re.MULTILINE)
        if heading_match:
            return heading_match.group(1).strip()

        # Fallback: use first non-empty line
        lines = markdown.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                return line[:100]  # Limit title length

        return None

    def _extract_bullet_points(self, markdown: str) -> List[str]:
        """
        Extract bullet points from markdown.

        Args:
            markdown: Markdown text

        Returns:
            List of bullet point strings
        """
        bullets = []

        # Match markdown bullet points (-, *, +) or numbered lists (1., 2., etc.)
        bullet_pattern = r'^[\s]*[-*+]\s+(.+)$|^[\s]*\d+\.\s+(.+)$'

        for line in markdown.split('\n'):
            match = re.match(bullet_pattern, line)
            if match:
                bullet_text = match.group(1) or match.group(2)
                if bullet_text:
                    bullets.append(bullet_text.strip())

        return bullets

    def _infer_slide_type(
        self, markdown: str, images: List[ImageContent], page_num: int
    ) -> SlideType:
        """
        Infer the type of slide based on content.

        Args:
            markdown: Markdown text
            images: List of images on this slide
            page_num: Page number (0-indexed)

        Returns:
            SlideType enum value
        """
        text_lower = markdown.lower()

        # First page is usually a title slide
        if page_num == 0:
            return SlideType.TITLE

        # Many images = diagram-heavy
        if len(images) >= 2:
            return SlideType.DIAGRAM_HEAVY

        # Section headers often have keywords
        section_keywords = ['section', 'chapter', 'part', 'overview']
        if any(keyword in text_lower for keyword in section_keywords):
            # Check if it's a short slide (likely just a header)
            if len(markdown.strip().split('\n')) <= 3:
                return SlideType.SECTION_HEADER

        # Conclusion keywords
        conclusion_keywords = ['conclusion', 'summary', 'recap', 'takeaway', 'thank you']
        if any(keyword in text_lower for keyword in conclusion_keywords):
            return SlideType.CONCLUSION

        # Default to content slide
        return SlideType.CONTENT

    def _markdown_to_plain_text(self, markdown: str) -> str:
        """
        Convert markdown to plain text (remove formatting).

        Args:
            markdown: Markdown text

        Returns:
            Plain text string
        """
        # Remove markdown headings (#)
        text = re.sub(r'^#+\s+', '', markdown, flags=re.MULTILINE)

        # Remove bold/italic markers (**text**, *text*)
        text = re.sub(r'\*+([^*]+)\*+', r'\1', text)

        # Remove links [text](url) -> text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

        # Remove bullet markers
        text = re.sub(r'^[\s]*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^[\s]*\d+\.\s+', '', text, flags=re.MULTILINE)

        return text.strip()
