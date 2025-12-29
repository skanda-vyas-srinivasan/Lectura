"""Data models for slide content and images."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class SlideType(str, Enum):
    """Types of slides based on content and purpose."""

    TITLE = "title"
    CONTENT = "content"
    SECTION_HEADER = "section_header"
    CONCLUSION = "conclusion"
    DIAGRAM_HEAVY = "diagram_heavy"


class SpecialContentType(str, Enum):
    """Types of special mathematical/technical content (boxed items)."""

    DEFINITION = "definition"
    THEOREM = "theorem"
    COROLLARY = "corollary"
    LEMMA = "lemma"
    PROPOSITION = "proposition"
    PROOF = "proof"
    EXAMPLE = "example"
    REMARK = "remark"
    PROPERTY = "property"
    AXIOM = "axiom"
    CLAIM = "claim"


class SpecialContent(BaseModel):
    """Represents a boxed/highlighted special content item (definition, theorem, etc.)."""

    content_type: SpecialContentType = Field(
        ..., description="Type of special content"
    )
    number: Optional[str] = Field(
        None, description="Number/label (e.g., '3.26', '2.1')"
    )
    title: Optional[str] = Field(
        None, description="Optional title (e.g., 'Fundamental Theorem of Calculus')"
    )
    content: str = Field(..., description="The actual definition/theorem text")
    slide_index: int = Field(..., ge=0, description="Which slide this appears on")

    class Config:
        json_schema_extra = {
            "example": {
                "content_type": "corollary",
                "number": "3.26",
                "title": None,
                "content": "If a polyhedron P is bounded, then it has at least one extreme point.",
                "slide_index": 42,
            }
        }


class ImageContent(BaseModel):
    """Represents an image/diagram extracted from a slide."""

    image_id: str = Field(..., description="Unique identifier for the image")
    image_data: Optional[str] = Field(
        None, description="Base64-encoded image data or file path"
    )
    format: str = Field(..., description="Image format (png, jpg, svg, etc.)")
    extracted_from_slide: int = Field(
        ..., description="Slide index this image came from"
    )
    position: Dict[str, float] = Field(
        default_factory=dict,
        description="Position metadata (x, y, width, height)",
    )
    vision_description: Optional[str] = Field(
        None, description="AI-generated description of image content"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "image_id": "img_slide5_001",
                "format": "png",
                "extracted_from_slide": 5,
                "position": {"x": 100, "y": 200, "width": 400, "height": 300},
                "vision_description": "Bar chart showing revenue growth from 2020-2024",
            }
        }


class SlideContent(BaseModel):
    """Represents the complete content of a single slide."""

    slide_index: int = Field(..., ge=0, description="Zero-based slide index")
    slide_type: SlideType = Field(
        default=SlideType.CONTENT, description="Type/category of this slide"
    )
    title: Optional[str] = Field(None, description="Slide title or heading")
    bullet_points: List[str] = Field(
        default_factory=list, description="Extracted bullet points"
    )
    body_text: str = Field(default="", description="Full text content of the slide")
    images: List[ImageContent] = Field(
        default_factory=list, description="Images/diagrams on this slide"
    )
    special_contents: List[SpecialContent] = Field(
        default_factory=list,
        description="Definitions, theorems, corollaries, and other boxed items",
    )
    notes: Optional[str] = Field(None, description="Speaker notes if available")
    raw_markdown: str = Field(
        default="", description="Complete slide content in markdown format"
    )
    layout_hint: Optional[str] = Field(
        None, description="Layout type hint (e.g., 'two-column', 'title-only')"
    )
    is_incremental_build: bool = Field(
        default=False,
        description="True if this slide builds on previous slide (adds content progressively)"
    )
    new_content_only: Optional[str] = Field(
        None,
        description="For incremental builds: only the NEW content added on this slide"
    )
    previous_slide_index: Optional[int] = Field(
        None,
        description="For incremental builds: index of the slide this builds upon"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "slide_index": 0,
                "slide_type": "title",
                "title": "Introduction to Machine Learning",
                "bullet_points": [],
                "body_text": "Introduction to Machine Learning\nCS 101 - Fall 2024",
                "images": [],
                "notes": "Welcome students, start with motivation",
                "raw_markdown": "# Introduction to Machine Learning\nCS 101 - Fall 2024",
            }
        }

    def has_images(self) -> bool:
        """Check if this slide contains any images."""
        return len(self.images) > 0

    def get_text_content(self) -> str:
        """Get all text content combined."""
        parts = []
        if self.title:
            parts.append(self.title)
        if self.bullet_points:
            parts.extend(self.bullet_points)
        if self.body_text and self.body_text not in [self.title or ""]:
            parts.append(self.body_text)
        return "\n".join(parts)

    def is_title_slide(self) -> bool:
        """Check if this is a title slide."""
        return self.slide_type == SlideType.TITLE

    def is_section_header(self) -> bool:
        """Check if this is a section header."""
        return self.slide_type == SlideType.SECTION_HEADER
