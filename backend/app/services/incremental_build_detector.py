"""Detect incremental slide builds (progressive content revelation)."""
from typing import List
from difflib import SequenceMatcher
from app.models.slide import SlideContent


def detect_incremental_builds(slides: List[SlideContent]) -> List[SlideContent]:
    """
    Detect and mark slides that are incremental builds of previous slides.

    An incremental build occurs when:
    - Slide N+1 has the same title as slide N
    - Slide N+1 contains ALL content from slide N
    - Slide N+1 has ADDITIONAL content beyond slide N

    This is common in presentations where bullet points appear one at a time.

    Args:
        slides: List of parsed slides

    Returns:
        Updated list of slides with incremental build markers set
    """
    if len(slides) < 2:
        return slides

    for i in range(1, len(slides)):
        current_slide = slides[i]
        previous_slide = slides[i - 1]

        # Check if titles match (or are both None/empty)
        current_title = (current_slide.title or "").strip()
        previous_title = (previous_slide.title or "").strip()

        if current_title != previous_title:
            continue  # Different topics, not an incremental build

        # Get text content for comparison
        current_text = current_slide.raw_markdown.strip()
        previous_text = previous_slide.raw_markdown.strip()

        # Check if current slide contains all previous content
        if not previous_text or not current_text:
            continue

        # Use SequenceMatcher to check if previous content is a substring/subset
        similarity = SequenceMatcher(None, previous_text, current_text).ratio()

        # Check if current slide starts with or contains most of previous slide
        if similarity > 0.7 and len(current_text) > len(previous_text):
            # This looks like an incremental build
            current_slide.is_incremental_build = True
            current_slide.previous_slide_index = previous_slide.slide_index

            # Extract the NEW content (diff)
            new_content = extract_new_content(previous_text, current_text)
            current_slide.new_content_only = new_content

            print(f"   🔄 Detected incremental build: Slide {i} builds on Slide {i-1}")
            print(f"      Previous had {len(previous_text)} chars, current has {len(current_text)} chars")
            print(f"      New content: {new_content[:100]}..." if len(new_content) > 100 else f"      New content: {new_content}")

    return slides


def extract_new_content(previous_text: str, current_text: str) -> str:
    """
    Extract the NEW content that appears in current but not in previous.

    This is a simple heuristic:
    1. If current starts with previous, return the remainder
    2. Otherwise, try to find the common prefix and return the diff

    Args:
        previous_text: Text from previous slide
        current_text: Text from current slide

    Returns:
        The new content as a string
    """
    # Normalize whitespace
    prev_lines = [line.strip() for line in previous_text.split('\n') if line.strip()]
    curr_lines = [line.strip() for line in current_text.split('\n') if line.strip()]

    # Find lines that are NEW (not in previous)
    prev_set = set(prev_lines)
    new_lines = [line for line in curr_lines if line not in prev_set]

    return '\n'.join(new_lines)
