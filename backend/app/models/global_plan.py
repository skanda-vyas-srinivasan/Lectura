"""Data models for global lecture context and understanding."""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.models.slide import SpecialContent


class Section(BaseModel):
    """Represents a section/chapter within the lecture."""

    title: str = Field(..., description="Section title or heading")
    start_slide: int = Field(..., ge=0, description="First slide index of this section")
    end_slide: int = Field(..., ge=0, description="Last slide index of this section")
    summary: str = Field(..., description="Brief summary of what this section covers")
    key_concepts: List[str] = Field(
        default_factory=list, description="Main concepts introduced in this section"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Introduction to Neural Networks",
                "start_slide": 10,
                "end_slide": 25,
                "summary": "Covers basic neural network architecture and forward propagation",
                "key_concepts": ["neurons", "activation functions", "layers"],
            }
        }


class SlideNarrationStrategy(BaseModel):
    """Strategy for narrating a single slide within a section."""

    slide_index: int = Field(..., ge=0, description="Index of this slide")
    role: str = Field(..., description="Role in section: 'introduce', 'elaborate', 'example', 'transition', 'conclude'")
    concepts_to_introduce: List[str] = Field(
        default_factory=list, description="New concepts introduced in THIS slide"
    )
    concepts_to_build_upon: List[str] = Field(
        default_factory=list, description="Concepts from PREVIOUS slides to reference/build upon"
    )
    key_points: List[str] = Field(
        default_factory=list, description="2-3 key points to cover in narration"
    )
    avoid_repeating: List[str] = Field(
        default_factory=list, description="Specific content already covered in previous slides (DO NOT repeat)"
    )


class SectionNarrationStrategy(BaseModel):
    """Narration strategy for an entire section - maps out slide-by-slide progression."""

    section_index: int = Field(..., ge=0, description="Index in sections list")
    section_title: str = Field(..., description="Title of this section")
    start_slide: int = Field(..., ge=0, description="First slide of section")
    end_slide: int = Field(..., ge=0, description="Last slide of section")
    narrative_arc: str = Field(..., description="Overall narrative progression for this section")
    slide_strategies: List[SlideNarrationStrategy] = Field(
        default_factory=list, description="Strategy for each slide in this section"
    )

    def get_strategy_for_slide(self, slide_idx: int) -> Optional[SlideNarrationStrategy]:
        """Get the narration strategy for a specific slide."""
        for strategy in self.slide_strategies:
            if strategy.slide_index == slide_idx:
                return strategy
        return None


class KeyDiagram(BaseModel):
    """Metadata about an important diagram in the lecture."""

    slide_idx: int = Field(..., ge=0, description="Slide index containing the diagram")
    description: str = Field(..., description="What the diagram depicts")
    purpose: str = Field(
        ..., description="Pedagogical purpose (why it's included)"
    )
    concepts_illustrated: List[str] = Field(
        default_factory=list, description="Concepts this diagram helps explain"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "slide_idx": 15,
                "description": "Neural network architecture with 3 layers",
                "purpose": "Show how data flows through the network",
                "concepts_illustrated": ["input layer", "hidden layer", "output layer"],
            }
        }


class GlobalContextPlan(BaseModel):
    """
    The canonical global understanding of the entire lecture.

    This is built BEFORE any narration generation and serves as the
    foundation for all contextual narration decisions.
    """

    lecture_title: str = Field(..., description="Overall title of the lecture")
    total_slides: int = Field(..., gt=0, description="Total number of slides")

    # High-level structure
    sections: List[Section] = Field(
        default_factory=list,
        description="Major sections/chapters with boundaries",
    )
    topic_progression: List[str] = Field(
        default_factory=list,
        description="Ordered sequence of main topics covered",
    )
    learning_objectives: List[str] = Field(
        default_factory=list,
        description="What students should learn from this lecture (inferred or explicit)",
    )

    # Semantic relationships
    terminology: Dict[str, str] = Field(
        default_factory=dict,
        description="Key terms and their definitions introduced in the lecture",
    )
    prerequisites: List[str] = Field(
        default_factory=list,
        description="Assumed prior knowledge required",
    )
    cross_references: Dict[int, List[int]] = Field(
        default_factory=dict,
        description="Map of slide indices to related slide indices",
    )

    # Pedagogical metadata
    instructional_style: str = Field(
        default="mixed",
        description="Teaching approach: theoretical, practical, or mixed",
    )
    audience_level: str = Field(
        default="intermediate",
        description="Target audience: beginner, intermediate, or advanced",
    )

    # Visual content summary
    key_diagrams: List[KeyDiagram] = Field(
        default_factory=list,
        description="Important diagrams/images and their purposes",
    )

    # Special academic content (definitions, theorems, etc.)
    special_contents: List[SpecialContent] = Field(
        default_factory=list,
        description="All definitions, theorems, corollaries, etc. from the lecture",
    )

    # Narration strategies (NEW - for avoiding repetition)
    section_narration_strategies: List[SectionNarrationStrategy] = Field(
        default_factory=list,
        description="Slide-by-slide narration strategies for each section to ensure continuity",
    )

    # Metadata
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Timestamp when this plan was created",
    )
    total_tokens_analyzed: int = Field(
        default=0,
        ge=0,
        description="Total tokens used in analysis (for cost tracking)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "lecture_title": "Introduction to Machine Learning",
                "total_slides": 50,
                "sections": [
                    {
                        "title": "Fundamentals",
                        "start_slide": 0,
                        "end_slide": 10,
                        "summary": "Basic ML concepts",
                        "key_concepts": ["supervised learning", "unsupervised learning"],
                    }
                ],
                "topic_progression": [
                    "ML Overview",
                    "Supervised Learning",
                    "Neural Networks",
                ],
                "learning_objectives": [
                    "Understand what machine learning is",
                    "Distinguish between supervised and unsupervised learning",
                ],
                "terminology": {
                    "ML": "Machine Learning",
                    "NN": "Neural Network",
                },
                "prerequisites": ["Basic Python", "Linear Algebra"],
                "cross_references": {5: [3, 7], 10: [8, 9]},
                "instructional_style": "practical",
                "audience_level": "beginner",
                "key_diagrams": [],
                "total_tokens_analyzed": 45000,
            }
        }

    def get_section_for_slide(self, slide_idx: int) -> Optional[Section]:
        """Find which section a given slide belongs to."""
        for section in self.sections:
            if section.start_slide <= slide_idx <= section.end_slide:
                return section
        return None

    def get_related_slides(self, slide_idx: int) -> List[int]:
        """Get list of slides that cross-reference the given slide."""
        return self.cross_references.get(slide_idx, [])

    def get_relevant_terminology(self, slide_content: str) -> Dict[str, str]:
        """Extract terminology relevant to a specific slide's content."""
        relevant = {}
        content_lower = slide_content.lower()
        for term, definition in self.terminology.items():
            if term.lower() in content_lower:
                relevant[term] = definition
        return relevant

    def get_narration_strategy_for_slide(self, slide_idx: int) -> Optional[SlideNarrationStrategy]:
        """Get the narration strategy for a specific slide."""
        # Find which section this slide belongs to
        section = self.get_section_for_slide(slide_idx)
        if not section:
            return None

        # Find the section strategy
        for section_strategy in self.section_narration_strategies:
            if section_strategy.start_slide <= slide_idx <= section_strategy.end_slide:
                return section_strategy.get_strategy_for_slide(slide_idx)

        return None
