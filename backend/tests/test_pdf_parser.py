"""Tests for PDF parser."""
import pytest
from pathlib import Path
from app.services.parsers import PDFParser
from app.models import SlideType


class TestPDFParser:
    """Test suite for PDFParser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = PDFParser()

    def test_parser_initialization(self):
        """Test parser can be initialized."""
        assert self.parser is not None
        assert hasattr(self.parser, 'parse')
        assert hasattr(self.parser, 'validate_file')

    def test_validate_file_nonexistent(self):
        """Test validation fails for nonexistent file."""
        result = self.parser.validate_file("nonexistent.pdf")
        assert result is False

    def test_validate_file_wrong_extension(self, tmp_path):
        """Test validation fails for wrong file extension."""
        # Create a dummy .txt file
        dummy_file = tmp_path / "test.txt"
        dummy_file.write_text("test content")

        result = self.parser.validate_file(dummy_file)
        assert result is False

    def test_parse_nonexistent_file_raises_error(self):
        """Test parsing nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            self.parser.parse("nonexistent.pdf")

    def test_extract_title_from_heading(self):
        """Test title extraction from markdown heading."""
        markdown = "# Introduction to ML\n\nSome content here"
        title = self.parser._extract_title(markdown)
        assert title == "Introduction to ML"

    def test_extract_title_from_first_line(self):
        """Test title extraction from first line when no heading."""
        markdown = "Machine Learning Basics\nMore content"
        title = self.parser._extract_title(markdown)
        assert title == "Machine Learning Basics"

    def test_extract_title_empty_markdown(self):
        """Test title extraction from empty markdown."""
        title = self.parser._extract_title("")
        assert title is None

    def test_extract_bullet_points_dash(self):
        """Test bullet point extraction with dashes."""
        markdown = """
        - First point
        - Second point
        - Third point
        """
        bullets = self.parser._extract_bullet_points(markdown)
        assert len(bullets) == 3
        assert "First point" in bullets
        assert "Second point" in bullets

    def test_extract_bullet_points_numbered(self):
        """Test bullet point extraction with numbers."""
        markdown = """
        1. First item
        2. Second item
        3. Third item
        """
        bullets = self.parser._extract_bullet_points(markdown)
        assert len(bullets) == 3
        assert "First item" in bullets

    def test_extract_bullet_points_asterisk(self):
        """Test bullet point extraction with asterisks."""
        markdown = """
        * Point A
        * Point B
        """
        bullets = self.parser._extract_bullet_points(markdown)
        assert len(bullets) == 2
        assert "Point A" in bullets

    def test_infer_slide_type_first_page(self):
        """Test first page is inferred as title slide."""
        slide_type = self.parser._infer_slide_type("Test", [], 0)
        assert slide_type == SlideType.TITLE

    def test_infer_slide_type_many_images(self):
        """Test slide with many images is diagram-heavy."""
        from app.models import ImageContent

        images = [
            ImageContent(image_id="1", format="png", extracted_from_slide=1),
            ImageContent(image_id="2", format="png", extracted_from_slide=1),
        ]
        slide_type = self.parser._infer_slide_type("Test", images, 1)
        assert slide_type == SlideType.DIAGRAM_HEAVY

    def test_infer_slide_type_section_header(self):
        """Test section header detection."""
        markdown = "## Section 2: Neural Networks"
        slide_type = self.parser._infer_slide_type(markdown, [], 5)
        assert slide_type == SlideType.SECTION_HEADER

    def test_infer_slide_type_conclusion(self):
        """Test conclusion slide detection."""
        markdown = "# Conclusion\n\nThank you for your attention"
        slide_type = self.parser._infer_slide_type(markdown, [], 10)
        assert slide_type == SlideType.CONCLUSION

    def test_infer_slide_type_default_content(self):
        """Test default content slide type."""
        markdown = "Regular slide content here"
        slide_type = self.parser._infer_slide_type(markdown, [], 5)
        assert slide_type == SlideType.CONTENT

    def test_markdown_to_plain_text_removes_headings(self):
        """Test markdown heading removal."""
        markdown = "# Title\n## Subtitle\nContent"
        plain = self.parser._markdown_to_plain_text(markdown)
        assert "#" not in plain
        assert "Title" in plain
        assert "Subtitle" in plain

    def test_markdown_to_plain_text_removes_bold(self):
        """Test markdown bold removal."""
        markdown = "This is **bold text** here"
        plain = self.parser._markdown_to_plain_text(markdown)
        assert "**" not in plain
        assert "bold text" in plain

    def test_markdown_to_plain_text_removes_links(self):
        """Test markdown link removal."""
        markdown = "Check [this link](https://example.com)"
        plain = self.parser._markdown_to_plain_text(markdown)
        assert "this link" in plain
        assert "https://" not in plain
        assert "](" not in plain

    def test_markdown_to_plain_text_removes_bullets(self):
        """Test markdown bullet removal."""
        markdown = "- First\n- Second"
        plain = self.parser._markdown_to_plain_text(markdown)
        assert "First" in plain
        assert "Second" in plain
        # Bullet markers should be removed
        lines = plain.split('\n')
        assert not any(line.strip().startswith('-') for line in lines)

    def test_split_markdown_by_pages(self):
        """Test markdown splitting by pages."""
        markdown = "Page 1\n\n-----\n\nPage 2\n\n-----\n\nPage 3"
        pages = self.parser._split_markdown_by_pages(markdown, 3)
        assert len(pages) == 3
        assert "Page 1" in pages[0]
        assert "Page 2" in pages[1]
        assert "Page 3" in pages[2]

    def test_split_markdown_by_pages_fewer_than_expected(self):
        """Test markdown splitting with fewer pages than expected."""
        markdown = "Page 1"
        pages = self.parser._split_markdown_by_pages(markdown, 3)
        assert len(pages) == 3
        assert pages[0] == "Page 1"
        assert pages[1] == ""
        assert pages[2] == ""

    def test_get_file_info(self, tmp_path):
        """Test file info extraction."""
        # Create a dummy file
        dummy_file = tmp_path / "test.pdf"
        dummy_file.write_text("dummy content")

        info = self.parser.get_file_info(dummy_file)
        assert info["filename"] == "test.pdf"
        assert info["extension"] == ".pdf"
        assert info["exists"] is True
        assert info["size_bytes"] > 0

    def test_get_file_info_nonexistent(self):
        """Test file info for nonexistent file."""
        info = self.parser.get_file_info("nonexistent.pdf")
        assert info["exists"] is False
        assert info["size_bytes"] == 0


# Integration test (only runs if sample PDF exists)
class TestPDFParserIntegration:
    """Integration tests with actual PDF files."""

    @pytest.fixture
    def sample_pdf_path(self):
        """Path to sample PDF for testing (if exists)."""
        return Path("tests/fixtures/sample_lecture.pdf")

    @pytest.mark.skipif(
        not Path("tests/fixtures/sample_lecture.pdf").exists(),
        reason="Sample PDF not found"
    )
    def test_parse_sample_pdf(self, sample_pdf_path):
        """Test parsing an actual PDF file."""
        parser = PDFParser()
        slides = parser.parse(sample_pdf_path)

        assert len(slides) > 0
        assert all(hasattr(slide, 'slide_index') for slide in slides)
        assert all(hasattr(slide, 'body_text') for slide in slides)
        assert slides[0].slide_index == 0

    @pytest.mark.skipif(
        not Path("tests/fixtures/sample_lecture.pdf").exists(),
        reason="Sample PDF not found"
    )
    def test_parsed_slides_have_content(self, sample_pdf_path):
        """Test that parsed slides contain actual content."""
        parser = PDFParser()
        slides = parser.parse(sample_pdf_path)

        # At least one slide should have text
        has_text = any(slide.body_text.strip() for slide in slides)
        assert has_text

        # Check that SlideContent model is properly populated
        for slide in slides:
            assert slide.slide_index >= 0
            assert slide.raw_markdown is not None
            assert isinstance(slide.images, list)
