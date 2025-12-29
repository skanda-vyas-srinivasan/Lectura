"""Data models for lecture sessions and narration segments."""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime, timedelta

from app.models.slide import SlideContent
from app.models.global_plan import GlobalContextPlan


class SessionStatus(str, Enum):
    """Status of a lecture processing session."""

    CREATED = "created"
    UPLOADING = "uploading"
    PARSING = "parsing"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    COMPLETE = "complete"
    ERROR = "error"


class NarrationSegment(BaseModel):
    """Generated narration for a single slide."""

    slide_index: int = Field(..., ge=0, description="Slide this narration is for")
    narration_text: str = Field(..., description="The generated narration content")
    estimated_duration_seconds: float = Field(
        ..., gt=0, description="Estimated speaking time in seconds"
    )

    # Context tracking
    references_previous_slides: List[int] = Field(
        default_factory=list,
        description="Slide indices referenced in this narration",
    )
    introduces_concepts: List[str] = Field(
        default_factory=list,
        description="New concepts introduced in this narration",
    )
    prepares_for_next: Optional[str] = Field(
        None, description="How this narration prepares for upcoming content"
    )

    # Quality metadata
    faithfulness_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Self-assessed faithfulness to source material (0-1)",
    )
    generation_timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="When this narration was generated",
    )
    tokens_used: int = Field(
        default=0, ge=0, description="Tokens used to generate this narration"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "slide_index": 5,
                "narration_text": "Now that we understand the basics of supervised learning, let's dive into neural networks. As you can see in this diagram, a neural network consists of layers of interconnected nodes...",
                "estimated_duration_seconds": 95.5,
                "references_previous_slides": [3, 4],
                "introduces_concepts": ["neural network", "layers", "nodes"],
                "prepares_for_next": "activation functions in the next slide",
                "tokens_used": 350,
            }
        }

    def get_word_count(self) -> int:
        """Calculate word count of narration."""
        return len(self.narration_text.split())

    def estimate_duration_from_text(self, words_per_minute: int = 150) -> float:
        """
        Estimate speaking duration based on word count.

        Args:
            words_per_minute: Average speaking rate (default: 150 wpm)

        Returns:
            Estimated duration in seconds
        """
        word_count = self.get_word_count()
        return (word_count / words_per_minute) * 60


class LectureSession(BaseModel):
    """
    Complete state of a lecture processing session.

    This is stored in-memory and tracks all aspects of processing
    from upload through narration generation.
    """

    session_id: str = Field(..., description="Unique session identifier")
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="When this session was created",
    )
    expires_at: str = Field(
        default_factory=lambda: (
            datetime.utcnow() + timedelta(hours=2)
        ).isoformat(),
        description="When this session expires and can be cleaned up",
    )

    # Processing state
    status: SessionStatus = Field(
        default=SessionStatus.CREATED, description="Current processing status"
    )
    current_phase: int = Field(
        default=0, ge=0, le=3, description="Current phase (0=not started, 1-3=active)"
    )
    progress_percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Overall progress percentage",
    )

    # Input data
    original_filename: str = Field(..., description="Original uploaded filename")
    file_format: str = Field(..., description="File format (pdf, pptx, etc.)")

    # Processed data
    slides: List[SlideContent] = Field(
        default_factory=list, description="Extracted slide content"
    )
    global_plan: Optional[GlobalContextPlan] = Field(
        None, description="Global lecture understanding (phase 2)"
    )
    narrations: Dict[int, NarrationSegment] = Field(
        default_factory=dict,
        description="Generated narrations keyed by slide index",
    )

    # Error tracking
    errors: List[str] = Field(default_factory=list, description="Error messages")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123xyz",
                "status": "generating",
                "current_phase": 3,
                "progress_percentage": 65.0,
                "original_filename": "ml_lecture.pdf",
                "file_format": "pdf",
                "slides": [],
                "global_plan": None,
                "narrations": {},
                "errors": [],
                "warnings": [],
            }
        }

    def is_expired(self) -> bool:
        """Check if this session has expired."""
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.utcnow() > expires

    def add_error(self, error_message: str) -> None:
        """Add an error and update status."""
        self.errors.append(error_message)
        self.status = SessionStatus.ERROR

    def add_warning(self, warning_message: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning_message)

    def update_progress(self, percentage: float, status: SessionStatus) -> None:
        """Update progress and status."""
        self.progress_percentage = min(100.0, max(0.0, percentage))
        self.status = status

    def get_total_slides(self) -> int:
        """Get total number of slides."""
        return len(self.slides)

    def get_completed_narrations(self) -> int:
        """Get count of completed narrations."""
        return len(self.narrations)

    def is_processing_complete(self) -> bool:
        """Check if all processing is complete."""
        return self.status == SessionStatus.COMPLETE

    def has_global_plan(self) -> bool:
        """Check if global plan has been generated."""
        return self.global_plan is not None

    def get_narration_for_slide(self, slide_idx: int) -> Optional[NarrationSegment]:
        """Get narration for a specific slide index."""
        return self.narrations.get(slide_idx)
