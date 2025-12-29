"""Abstract base class for AI providers (model-agnostic design)."""
from abc import ABC, abstractmethod
from typing import Dict, List, Any
from app.models.slide import SlideContent, ImageContent


class AIProvider(ABC):
    """
    Abstract interface for AI providers.

    This allows swapping between Claude, OpenAI, Gemini, or any other model
    without changing the core application logic.
    """

    @abstractmethod
    async def analyze_structure(self, slides: List[SlideContent]) -> Dict[str, Any]:
        """
        Analyze the structural aspects of the lecture deck.

        Args:
            slides: List of all slides in the deck

        Returns:
            Dictionary containing:
                - sections: List of section metadata
                - topic_progression: Ordered list of topics
                - learning_objectives: Inferred learning goals
                - terminology: Key terms and definitions
                - cross_references: Inter-slide relationships
                - instructional_style: Teaching approach
                - audience_level: Target audience
        """
        pass

    @abstractmethod
    async def analyze_images(
        self, images: List[ImageContent], slide_context: List[SlideContent]
    ) -> Dict[str, Any]:
        """
        Analyze visual content using vision capabilities.

        Args:
            images: List of images to analyze
            slide_context: Associated slide content for context

        Returns:
            Dictionary containing:
                - key_diagrams: List of important visual elements with descriptions
        """
        pass

    @abstractmethod
    async def create_section_narration_strategy(
        self,
        section: Any,  # Section model
        section_slides: List[SlideContent],
        global_context: Any  # GlobalContextPlan model
    ) -> Dict[str, Any]:
        """
        Create a slide-by-slide narration strategy for a section.

        This ensures each slide knows its role and avoids repeating content.

        Args:
            section: The section to create strategy for
            section_slides: All slides in this section
            global_context: The complete global context plan

        Returns:
            Dictionary containing:
                - narrative_arc: Overall progression for this section
                - slide_strategies: List of per-slide strategies with:
                    - slide_index: Slide number
                    - role: 'introduce', 'elaborate', 'example', 'transition', 'conclude'
                    - concepts_to_introduce: New concepts in THIS slide
                    - concepts_to_build_upon: Concepts from previous slides
                    - key_points: 2-3 main points to cover
                    - avoid_repeating: Content already covered (don't repeat)
        """
        pass

    @abstractmethod
    async def generate_section_narrations(
        self,
        section_slides: List[SlideContent],
        section_strategy: Any,  # SectionNarrationStrategy
        global_plan: Dict[str, Any],
    ) -> Dict[int, str]:
        """
        Generate narrations for ALL slides in a section as ONE continuous narrative.

        This ensures smooth flow without treating each slide independently.

        Args:
            section_slides: All slides in this section
            section_strategy: The section's narration strategy
            global_plan: The complete global context

        Returns:
            Dictionary mapping slide_index -> narration_text
        """
        pass

    @abstractmethod
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
        pass
