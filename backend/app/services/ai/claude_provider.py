"""Claude AI provider implementation."""
import json
import base64
from typing import List, Dict, Any
from anthropic import Anthropic

from app.models import SlideContent, ImageContent
from app.services.ai.base import AIProvider
from app.config import settings


class ClaudeProvider(AIProvider):
    """
    AI provider implementation using Claude (Anthropic).

    Uses Claude's long context (200K tokens) and vision capabilities
    for analyzing lecture slides.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        """
        Initialize Claude provider.

        Args:
            api_key: Anthropic API key (defaults to settings)
            model: Model to use (defaults to settings)
        """
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.claude_model
        self.client = Anthropic(api_key=self.api_key)

        # Token tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    async def analyze_structure(self, slides: List[SlideContent]) -> Dict[str, Any]:
        """
        Analyze the structural aspects of the lecture deck.

        Uses Claude to understand:
        - Sections and topic progression
        - Learning objectives
        - Terminology
        - Cross-references
        - Instructional style

        Args:
            slides: List of all slides in the deck

        Returns:
            Dictionary with structural analysis
        """
        # Build a text representation of all slides
        deck_text = self._build_deck_text(slides)

        # Create the analysis prompt
        prompt = self._build_structural_prompt(deck_text, len(slides))

        # Call Claude
        response = self.client.messages.create(
            model=self.model,
            max_tokens=16000,
            temperature=0.1,  # Low temperature for analytical tasks
            messages=[{"role": "user", "content": prompt}],
        )

        # Track tokens
        self.total_input_tokens += response.usage.input_tokens
        self.total_output_tokens += response.usage.output_tokens

        # Parse the JSON response
        response_text = response.content[0].text

        # Extract JSON from the response (handle markdown code blocks)
        json_text = self._extract_json(response_text)

        try:
            result = json.loads(json_text)
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse JSON response: {e}")
            print(f"Response: {response_text[:500]}")
            # Return minimal structure
            result = {
                "sections": [],
                "topic_progression": [],
                "learning_objectives": [],
                "terminology": {},
                "prerequisites": [],
                "cross_references": {},
                "instructional_style": "mixed",
                "audience_level": "intermediate",
            }

        return result

    async def analyze_images(
        self, images: List[ImageContent], slide_context: List[SlideContent]
    ) -> Dict[str, Any]:
        """
        Analyze visual content using Claude's vision capabilities.

        Args:
            images: List of images to analyze
            slide_context: Associated slide content for context

        Returns:
            Dictionary with image analysis including key diagrams
        """
        if not images:
            return {"key_diagrams": []}

        # Limit to first 20 images to avoid token limits
        # (Can batch process more in production)
        images_to_analyze = images[:20]

        # Build vision prompt with images
        content_blocks = [
            {
                "type": "text",
                "text": self._build_vision_prompt(len(images_to_analyze)),
            }
        ]

        # Add images
        for idx, img in enumerate(images_to_analyze):
            # Add image
            if img.image_data:
                content_blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": f"image/{img.format}",
                        "data": img.image_data,
                    },
                })

            # Add context about which slide this is from
            slide_idx = img.extracted_from_slide
            slide_context_text = ""
            if slide_idx < len(slide_context):
                slide = slide_context[slide_idx]
                slide_context_text = f"Slide {slide_idx + 1}: {slide.title or '(No title)'}"

            content_blocks.append({
                "type": "text",
                "text": f"\n[Image {idx + 1} from {slide_context_text}]\n",
            })

        # Call Claude with vision
        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            temperature=0.1,
            messages=[{"role": "user", "content": content_blocks}],
        )

        # Track tokens
        self.total_input_tokens += response.usage.input_tokens
        self.total_output_tokens += response.usage.output_tokens

        # Parse response
        response_text = response.content[0].text

        # Extract key diagrams from the analysis
        key_diagrams = self._parse_vision_response(response_text, images_to_analyze)

        return {"key_diagrams": key_diagrams}

    async def generate_narration(
        self,
        slide: SlideContent,
        global_plan: Dict[str, Any],
        previous_narration_summary: str | None,
        related_slides: List[SlideContent] | None = None,
    ) -> str:
        """
        Generate pedagogical narration for a single slide.

        Args:
            slide: The current slide to narrate
            global_plan: The complete lecture understanding (global context)
            previous_narration_summary: Summary of the previous slide's narration
            related_slides: Optional related slides for additional context

        Returns:
            Generated narration text (200-300 words)
        """
        prompt = self._build_narration_prompt(
            slide, global_plan, previous_narration_summary, related_slides
        )

        # Call Claude
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            temperature=0.3,  # Slightly higher for more natural language
            messages=[{"role": "user", "content": prompt}],
        )

        # Track tokens
        self.total_input_tokens += response.usage.input_tokens
        self.total_output_tokens += response.usage.output_tokens

        return response.content[0].text.strip()

    def _build_deck_text(self, slides: List[SlideContent]) -> str:
        """Build a text representation of the entire deck."""
        parts = []

        for slide in slides:
            parts.append(f"\n{'='*60}")
            parts.append(f"SLIDE {slide.slide_index + 1}")
            parts.append(f"{'='*60}")

            if slide.title:
                parts.append(f"Title: {slide.title}")

            if slide.special_contents:
                parts.append("\nSpecial Content:")
                for special in slide.special_contents:
                    number_str = f" {special.number}" if special.number else ""
                    parts.append(f"  [{special.content_type.upper()}{number_str}] {special.content}")

            if slide.bullet_points:
                parts.append("\nBullet Points:")
                for bullet in slide.bullet_points:
                    parts.append(f"  • {bullet}")

            if slide.body_text:
                parts.append(f"\nContent:\n{slide.body_text}")

            if slide.images:
                parts.append(f"\n[Contains {len(slide.images)} image(s)]")

        return "\n".join(parts)

    def _build_structural_prompt(self, deck_text: str, num_slides: int) -> str:
        """Build the prompt for structural analysis."""
        return f"""You are analyzing a lecture presentation to understand its pedagogical structure.

Below is the complete slide deck with {num_slides} slides. Each slide is marked with its number and contains the extracted text content.

{deck_text}

Please analyze this lecture and provide a comprehensive structural understanding. Return your analysis as a JSON object with the following structure:

{{
  "lecture_title": "Inferred title of the lecture",
  "sections": [
    {{
      "title": "Section name",
      "start_slide": 0,
      "end_slide": 10,
      "summary": "Brief summary of this section",
      "key_concepts": ["concept1", "concept2"]
    }}
  ],
  "topic_progression": ["Topic 1", "Topic 2", "Topic 3"],
  "learning_objectives": ["What students should learn"],
  "terminology": {{"term": "definition"}},
  "prerequisites": ["Required prior knowledge"],
  "cross_references": {{"5": [3, 7]}},
  "instructional_style": "theoretical|practical|mixed",
  "audience_level": "beginner|intermediate|advanced"
}}

Focus on:
1. Identifying major sections (look for section headers, topic changes)
2. Understanding the learning progression (what concepts build on others)
3. Extracting key terminology (especially from definitions, theorems, corollaries)
4. Finding cross-references (when slides reference earlier concepts)
5. Determining the teaching approach and target audience

Return ONLY the JSON object, no additional text."""

    def _build_vision_prompt(self, num_images: int) -> str:
        """Build the prompt for vision analysis."""
        return f"""You are analyzing diagrams and images from a lecture presentation.

Below are {num_images} images extracted from various slides. For each image, analyze:

1. What does the image depict? (diagram, graph, equation, table, etc.)
2. What is its pedagogical purpose? (illustrate a concept, show an example, prove a theorem)
3. What key concepts does it illustrate?
4. Is this a "key diagram" that's central to understanding the lecture?

For each image, provide:
- A clear description of what's shown
- The pedagogical purpose
- Key concepts illustrated
- Whether it's a critical diagram

Focus on diagrams that are essential for understanding the material, not decorative images."""

    def _build_narration_prompt(
        self,
        slide: SlideContent,
        global_plan: Dict[str, Any],
        previous_summary: str | None,
        related_slides: List[SlideContent] | None,
    ) -> str:
        """Build the prompt for narration generation."""

        # Extract relevant context from global plan
        sections = global_plan.get("sections", [])
        current_section = None
        for section in sections:
            if section["start_slide"] <= slide.slide_index <= section["end_slide"]:
                current_section = section
                break

        section_context = ""
        if current_section:
            section_context = f"Current Section: {current_section['title']}\n"

        prev_context = ""
        if previous_summary:
            prev_context = f"Previous Slide Summary: {previous_summary}\n"

        special_content_text = ""
        if slide.special_contents:
            special_content_text = "\nSpecial Content on This Slide:\n"
            for special in slide.special_contents:
                number_str = f" {special.number}" if special.number else ""
                special_content_text += f"[{special.content_type.upper()}{number_str}] {special.content}\n"

        return f"""You are an expert lecturer preparing narration for a slide presentation.

GLOBAL LECTURE CONTEXT:
- Title: {global_plan.get('lecture_title', 'Unknown')}
- Learning Objectives: {', '.join(global_plan.get('learning_objectives', [])[:3])}
- {section_context}
- Audience Level: {global_plan.get('audience_level', 'intermediate')}
- Style: {global_plan.get('instructional_style', 'mixed')}

SLIDE POSITION:
- Slide {slide.slide_index + 1} of {global_plan.get('total_slides', '?')}

{prev_context}

CURRENT SLIDE CONTENT:
Title: {slide.title or '(No title)'}

{slide.body_text}

{special_content_text}

{"Images: " + str(len(slide.images)) + " diagram(s) present" if slide.images else ""}

YOUR TASK:
Generate natural, pedagogical narration for this slide as if you are lecturing live.

REQUIREMENTS:
1. Explain concepts, don't just read the slide
2. Reference prior material when relevant
3. Prepare students for what's coming next
4. Be faithful to the slide's content - don't improvise unrelated material
5. Don't repeat what was thoroughly covered in previous slides
6. Use conversational academic language
7. If there are diagrams, describe and explain them

CRITICAL - PRIVACY & TTS COMPATIBILITY:
8. DO NOT mention specific instructor names, professor names, or teaching assistants
9. DO NOT mention specific universities or institutions
10. Keep narration generic and reusable (e.g., "Welcome to this course on Linear Optimization" NOT "Welcome to ISyE 525 at UW-Madison")
11. Convert ALL mathematical notation to spoken form for text-to-speech:
    - LaTeX like \\mathbb{{R}}^n → "n-dimensional real space" or "R to the power of n"
    - Symbols like \\max → "maximize", \\min → "minimize"
    - c^T x → "c transpose times x"
    - \\in → "in" or "belongs to"
    - \\leq → "less than or equal to"
    - Fractions like \\frac{{a}}{{b}} → "a over b" or "a divided by b"
    - DO NOT include any LaTeX syntax in the output

LENGTH: Aim for 150-250 words (about 1-1.5 minutes of speaking).

Generate the narration now (narration text only, no preamble):"""

    def _extract_json(self, text: str) -> str:
        """Extract JSON from markdown code blocks if present."""
        # Check if response is wrapped in markdown code block
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            return text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            return text[start:end].strip()
        return text.strip()

    def _parse_vision_response(
        self, response_text: str, images: List[ImageContent]
    ) -> List[Dict[str, Any]]:
        """Parse the vision analysis response into key diagrams."""
        # For now, simple parsing
        # In production, could use structured output or more sophisticated parsing
        key_diagrams = []

        # Split by image markers
        sections = response_text.split("Image ")

        for i, section in enumerate(sections[1:], 1):  # Skip first split
            if i > len(images):
                break

            img = images[i - 1]

            # Extract description (first paragraph)
            lines = section.strip().split('\n')
            description = ' '.join(lines[1:5]) if len(lines) > 1 else section[:200]

            key_diagrams.append({
                "slide_idx": img.extracted_from_slide,
                "description": description.strip(),
                "purpose": "Illustrates key concept",  # Could parse this better
                "concepts_illustrated": [],
            })

        return key_diagrams

    def get_token_usage(self) -> Dict[str, int]:
        """Get total token usage."""
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
        }

    def reset_token_counter(self):
        """Reset token counters."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
