"""Test suite for data models."""
import pytest
from datetime import datetime

from app.models import (
    SlideContent,
    ImageContent,
    SlideType,
    GlobalContextPlan,
    Section,
    KeyDiagram,
    LectureSession,
    NarrationSegment,
    SessionStatus,
)


def test_image_content_creation():
    """Test ImageContent model creation and validation."""
    image = ImageContent(
        image_id="test_img_001",
        format="png",
        extracted_from_slide=5,
        position={"x": 100, "y": 200, "width": 400, "height": 300},
    )

    assert image.image_id == "test_img_001"
    assert image.format == "png"
    assert image.extracted_from_slide == 5
    assert image.vision_description is None


def test_slide_content_creation():
    """Test SlideContent model creation and helper methods."""
    slide = SlideContent(
        slide_index=0,
        slide_type=SlideType.TITLE,
        title="Introduction to ML",
        body_text="Machine Learning Fundamentals",
        raw_markdown="# Introduction to ML\nMachine Learning Fundamentals",
    )

    assert slide.slide_index == 0
    assert slide.is_title_slide()
    assert not slide.is_section_header()
    assert not slide.has_images()
    assert "Introduction to ML" in slide.get_text_content()


def test_slide_content_with_images():
    """Test SlideContent with images."""
    image = ImageContent(
        image_id="img_1",
        format="png",
        extracted_from_slide=1,
    )

    slide = SlideContent(
        slide_index=1,
        slide_type=SlideType.DIAGRAM_HEAVY,
        title="Neural Network Architecture",
        images=[image],
    )

    assert slide.has_images()
    assert len(slide.images) == 1


def test_section_creation():
    """Test Section model."""
    section = Section(
        title="Introduction",
        start_slide=0,
        end_slide=10,
        summary="Overview of machine learning concepts",
        key_concepts=["supervised learning", "unsupervised learning"],
    )

    assert section.title == "Introduction"
    assert section.start_slide == 0
    assert section.end_slide == 10
    assert len(section.key_concepts) == 2


def test_global_context_plan_creation():
    """Test GlobalContextPlan model creation and helper methods."""
    section = Section(
        title="Basics",
        start_slide=0,
        end_slide=10,
        summary="Fundamentals",
    )

    plan = GlobalContextPlan(
        lecture_title="ML 101",
        total_slides=50,
        sections=[section],
        topic_progression=["Intro", "Supervised", "Unsupervised"],
        learning_objectives=["Understand ML basics"],
        terminology={"ML": "Machine Learning"},
        cross_references={5: [3, 7]},
    )

    assert plan.lecture_title == "ML 101"
    assert plan.total_slides == 50
    assert len(plan.sections) == 1
    assert plan.get_section_for_slide(5) == section
    assert plan.get_section_for_slide(15) is None
    assert plan.get_related_slides(5) == [3, 7]
    assert plan.get_related_slides(99) == []


def test_narration_segment_creation():
    """Test NarrationSegment model and duration estimation."""
    narration = NarrationSegment(
        slide_index=5,
        narration_text="This is a test narration with exactly ten words here.",
        estimated_duration_seconds=90.0,
        introduces_concepts=["neural networks"],
    )

    assert narration.slide_index == 5
    assert narration.get_word_count() == 10
    # 10 words at 150 wpm = 10/150 * 60 = 4 seconds
    assert abs(narration.estimate_duration_from_text() - 4.0) < 0.1


def test_lecture_session_creation():
    """Test LectureSession model creation and helper methods."""
    session = LectureSession(
        session_id="test_session_001",
        original_filename="test.pdf",
        file_format="pdf",
    )

    assert session.session_id == "test_session_001"
    assert session.status == SessionStatus.CREATED
    assert session.current_phase == 0
    assert session.progress_percentage == 0.0
    assert session.get_total_slides() == 0
    assert session.get_completed_narrations() == 0
    assert not session.is_processing_complete()
    assert not session.has_global_plan()


def test_lecture_session_error_handling():
    """Test error handling in LectureSession."""
    session = LectureSession(
        session_id="test_session_002",
        original_filename="test.pdf",
        file_format="pdf",
    )

    session.add_error("Test error message")

    assert len(session.errors) == 1
    assert session.status == SessionStatus.ERROR
    assert "Test error message" in session.errors


def test_lecture_session_with_data():
    """Test LectureSession with slides and narrations."""
    slide = SlideContent(
        slide_index=0,
        title="Test Slide",
        body_text="Test content",
    )

    narration = NarrationSegment(
        slide_index=0,
        narration_text="Test narration",
        estimated_duration_seconds=60.0,
    )

    session = LectureSession(
        session_id="test_session_003",
        original_filename="test.pdf",
        file_format="pdf",
        slides=[slide],
        narrations={0: narration},
    )

    assert session.get_total_slides() == 1
    assert session.get_completed_narrations() == 1
    assert session.get_narration_for_slide(0) == narration
    assert session.get_narration_for_slide(1) is None


def test_session_progress_update():
    """Test session progress updates."""
    session = LectureSession(
        session_id="test_session_004",
        original_filename="test.pdf",
        file_format="pdf",
    )

    session.update_progress(50.0, SessionStatus.ANALYZING)

    assert session.progress_percentage == 50.0
    assert session.status == SessionStatus.ANALYZING


def test_global_context_plan_get_relevant_terminology():
    """Test terminology extraction based on content."""
    plan = GlobalContextPlan(
        lecture_title="ML 101",
        total_slides=10,
        terminology={
            "ML": "Machine Learning",
            "NN": "Neural Network",
            "AI": "Artificial Intelligence",
        },
    )

    content = "This slide discusses ML and NN architectures"
    relevant = plan.get_relevant_terminology(content)

    assert "ML" in relevant
    assert "NN" in relevant
    assert "AI" not in relevant  # Not mentioned in content
