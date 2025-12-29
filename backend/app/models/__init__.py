"""
Data models for the AI Lecturer System.

All models use Pydantic for validation and type safety.
"""

from app.models.slide import SlideContent, ImageContent, SlideType, SpecialContent, SpecialContentType
from app.models.global_plan import (
    GlobalContextPlan,
    Section,
    KeyDiagram,
    SectionNarrationStrategy,
    SlideNarrationStrategy,
)
from app.models.session import (
    LectureSession,
    NarrationSegment,
    SessionStatus,
)

__all__ = [
    # Slide models
    "SlideContent",
    "ImageContent",
    "SlideType",
    "SpecialContent",
    "SpecialContentType",
    # Global plan models
    "GlobalContextPlan",
    "Section",
    "KeyDiagram",
    "SectionNarrationStrategy",
    "SlideNarrationStrategy",
    # Session models
    "LectureSession",
    "NarrationSegment",
    "SessionStatus",
]
