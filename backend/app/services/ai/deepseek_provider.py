"""DeepSeek AI provider implementation for cost-effective narration."""
from typing import List, Dict, Any
from openai import OpenAI

from app.models import SlideContent, ImageContent
from app.services.ai.base import AIProvider
from app.config import settings


class DeepSeekProvider(AIProvider):
    """
    AI provider implementation using DeepSeek Chat.

    DeepSeek is extremely cost-effective for narration generation:
    - Input: $0.27 per 1M tokens
    - Output: $1.10 per 1M tokens

    Uses OpenAI-compatible API for easy integration.
    """

    def __init__(self, api_key: str | None = None, model: str = "deepseek-chat"):
        """
        Initialize DeepSeek provider.

        Args:
            api_key: DeepSeek API key (defaults to settings)
            model: Model to use (defaults to deepseek-chat)
        """
        self.api_key = api_key or settings.deepseek_api_key
        self.model = model

        # DeepSeek uses OpenAI-compatible API
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com"
        )

        # Token tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    async def analyze_structure(self, slides: List[SlideContent]) -> Dict[str, Any]:
        """
        Not implemented for DeepSeek - use Claude Sonnet for analysis.

        DeepSeek is optimized for narration generation, not structural analysis.
        """
        raise NotImplementedError(
            "DeepSeek provider is for narration only. "
            "Use ClaudeProvider for structural analysis."
        )

    async def analyze_images(
        self, images: List[ImageContent], slide_context: List[SlideContent]
    ) -> Dict[str, Any]:
        """
        Not implemented for DeepSeek - use Claude Sonnet for vision.

        DeepSeek doesn't have native vision capabilities.
        """
        raise NotImplementedError(
            "DeepSeek provider doesn't support vision analysis. "
            "Use ClaudeProvider for image analysis."
        )

    async def generate_narration(
        self,
        slide: SlideContent,
        global_plan: Dict[str, Any],
        previous_narration_summary: str | None,
        related_slides: List[SlideContent] | None = None,
    ) -> str:
        """
        Generate pedagogical narration for a single slide using DeepSeek.

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

        # Call DeepSeek via OpenAI-compatible API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.3,  # Slightly higher for more natural language
        )

        # Track tokens
        self.total_input_tokens += response.usage.prompt_tokens
        self.total_output_tokens += response.usage.completion_tokens

        return response.choices[0].message.content.strip()

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
