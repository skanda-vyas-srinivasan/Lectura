"""Global Context Builder for lecture analysis.

This service orchestrates the complete analysis of a lecture deck,
building a comprehensive understanding before any narration is generated.
"""
import asyncio
import time
from typing import List, Dict, Any, Optional
from app.models import (
    SlideContent,
    ImageContent,
    GlobalContextPlan,
    Section,
    KeyDiagram,
    SectionNarrationStrategy,
    SlideNarrationStrategy
)
from app.services.ai import AIProvider, ClaudeProvider
from app.config import settings


class GlobalContextBuilder:
    """
    Builds a complete understanding of a lecture deck.

    Runs in two stages:
    1. Structural Analysis - Analyze all slide text to understand sections, topics, objectives
    2. Visual Analysis - Analyze images to identify key diagrams

    The result is a GlobalContextPlan that serves as canonical context
    for all subsequent narration generation.
    """

    def __init__(self, ai_provider: Optional[AIProvider] = None):
        """
        Initialize the builder.

        Args:
            ai_provider: AI provider to use (defaults to ClaudeProvider from settings)
        """
        self.ai_provider = ai_provider or ClaudeProvider()

    async def build_context(
        self,
        slides: List[SlideContent],
        progress_callback: Optional[callable] = None
    ) -> GlobalContextPlan:
        """
        Build complete global context for a lecture.

        Args:
            slides: List of all slides in the deck
            progress_callback: Optional callback for progress updates
                               Should accept (stage: str, progress: float)

        Returns:
            GlobalContextPlan with complete lecture understanding
        """
        if not slides:
            raise ValueError("Cannot build context from empty slide list")

        total_slides = len(slides)
        total_images = sum(len(slide.images) for slide in slides)
        print(f"🧠 ContextBuilder: start | slides={total_slides} images={total_images}")
        start_time = time.monotonic()

        # Stage 1: Structural Analysis (70% of work)
        if progress_callback:
            progress_callback("structural_analysis", 0.0)

        stage_start = time.monotonic()
        print("🧠 ContextBuilder: structural_analysis start")
        structural_analysis = await self.ai_provider.analyze_structure(slides)
        print(
            "🧠 ContextBuilder: structural_analysis done "
            f"({time.monotonic() - stage_start:.2f}s)"
        )

        if progress_callback:
            progress_callback("structural_analysis", 1.0)

        # Stage 2: Visual Analysis (30% of work)
        if progress_callback:
            progress_callback("visual_analysis", 0.0)

        # Collect all images from all slides
        all_images = []
        for slide in slides:
            all_images.extend(slide.images)

        # Run vision analysis if there are images
        visual_analysis = {}
        if all_images:
            stage_start = time.monotonic()
            print(f"🧠 ContextBuilder: visual_analysis start | images={len(all_images)}")
            visual_analysis = await self.ai_provider.analyze_images(all_images, slides)
            print(
                "🧠 ContextBuilder: visual_analysis done "
                f"({time.monotonic() - stage_start:.2f}s)"
            )
        else:
            print("🧠 ContextBuilder: visual_analysis skipped (no images)")

        if progress_callback:
            progress_callback("visual_analysis", 1.0)

        # Stage 3: Synthesis (combine results)
        if progress_callback:
            progress_callback("synthesis", 0.0)

        stage_start = time.monotonic()
        print("🧠 ContextBuilder: synthesis start")
        global_plan = self._synthesize_plan(slides, structural_analysis, visual_analysis)
        print(
            "🧠 ContextBuilder: synthesis done "
            f"({time.monotonic() - stage_start:.2f}s)"
        )

        if progress_callback:
            progress_callback("synthesis", 1.0)

        # Stage 4: Build Section Narration Strategies (NEW - for avoiding repetition)
        if progress_callback:
            progress_callback("section_strategies", 0.0)

        stage_start = time.monotonic()
        print("🧠 ContextBuilder: section_strategies start")
        section_strategies = await self._build_section_strategies(slides, global_plan)
        global_plan.section_narration_strategies = section_strategies
        print(
            "🧠 ContextBuilder: section_strategies done "
            f"({time.monotonic() - stage_start:.2f}s)"
        )

        if progress_callback:
            progress_callback("section_strategies", 1.0)

        print(
            "🧠 ContextBuilder: complete "
            f"({time.monotonic() - start_time:.2f}s)"
        )
        return global_plan

    def _synthesize_plan(
        self,
        slides: List[SlideContent],
        structural: Dict[str, Any],
        visual: Dict[str, Any]
    ) -> GlobalContextPlan:
        """
        Combine structural and visual analysis into a GlobalContextPlan.

        Args:
            slides: Original slides
            structural: Results from structural analysis
            visual: Results from visual analysis

        Returns:
            Complete GlobalContextPlan
        """
        # Parse sections from structural analysis
        sections = []
        max_slide_idx = len(slides) - 1  # Last valid slide index
        for sec_data in structural.get("sections", []):
            # Clamp section boundaries to valid slide indices
            start = max(0, min(sec_data.get("start_slide", 0), max_slide_idx))
            end = max(0, min(sec_data.get("end_slide", 0), max_slide_idx))

            sections.append(Section(
                title=sec_data.get("title", "Untitled Section"),
                start_slide=start,
                end_slide=end,
                summary=sec_data.get("summary", ""),
                key_concepts=sec_data.get("key_concepts", [])
            ))

        # Parse key diagrams from visual analysis
        key_diagrams = []
        for diag_data in visual.get("key_diagrams", []):
            key_diagrams.append(KeyDiagram(
                slide_idx=diag_data.get("slide_idx", 0),
                description=diag_data.get("description", ""),
                purpose=diag_data.get("purpose", ""),
                concepts_illustrated=diag_data.get("concepts_illustrated", [])
            ))

        # Collect all special content from slides
        all_special_contents = []
        for slide in slides:
            all_special_contents.extend(slide.special_contents)

        # Build cross-references map (slide_index -> [related_slide_indices])
        cross_refs_raw = structural.get("cross_references", {})
        cross_references = {}
        for key, value in cross_refs_raw.items():
            # Keys might be strings from JSON, convert to int
            # Handle formats like "5", "Slide 5", etc.
            if isinstance(key, str):
                # Extract digits from string (handles "5", "Slide 5", etc.)
                import re
                match = re.search(r'\d+', key)
                if match:
                    slide_idx = int(match.group())
                else:
                    continue  # Skip invalid keys
            else:
                slide_idx = int(key) if isinstance(key, float) else key

            # Convert value list to integers (handle floats like 1.1, 2.5, strings like "Section 1.4")
            if isinstance(value, list):
                cleaned_values = []
                for v in value:
                    try:
                        if isinstance(v, (int, float)):
                            cleaned_values.append(int(v))
                        elif isinstance(v, str):
                            # Extract first number from string (handles "5", "1.4", "Section 2.3", etc.)
                            import re
                            match = re.search(r'\d+', v)
                            if match:
                                cleaned_values.append(int(match.group()))
                        else:
                            cleaned_values.append(int(v))
                    except (ValueError, TypeError):
                        # Skip values that can't be converted
                        continue
                value = cleaned_values

            cross_references[slide_idx] = value

        # Create the global plan
        plan = GlobalContextPlan(
            lecture_title=structural.get("lecture_title", "Untitled Lecture"),
            total_slides=len(slides),
            sections=sections,
            topic_progression=structural.get("topic_progression", []),
            learning_objectives=structural.get("learning_objectives", []),
            terminology=structural.get("terminology", {}),
            prerequisites=structural.get("prerequisites", []),
            cross_references=cross_references,
            instructional_style=structural.get("instructional_style", "mixed"),
            audience_level=structural.get("audience_level", "intermediate"),
            key_diagrams=key_diagrams,
            special_contents=all_special_contents
        )

        return plan

    async def _build_section_strategies(
        self,
        slides: List[SlideContent],
        global_plan: GlobalContextPlan
    ) -> List[SectionNarrationStrategy]:
        """
        Build slide-by-slide narration strategies for each section.

        This ensures each slide knows its role and avoids repeating content
        already covered in previous slides.

        Args:
            slides: All slides in the deck
            global_plan: The synthesized global context plan

        Returns:
            List of SectionNarrationStrategy objects
        """
        strategies = []
        print(
            "🧠 ContextBuilder: build_section_strategies "
            f"sections={len(global_plan.sections)} slides={len(slides)}"
        )

        # Check if there are slides before the first section (intro slides)
        first_section_start = global_plan.sections[0].start_slide if global_plan.sections else len(slides)

        if first_section_start > 0:
            # Create a "Front Matter" section for intro slides
            intro_slides = slides[0:first_section_start]
            print(
                "🧠 ContextBuilder: intro section "
                f"slides=0..{first_section_start - 1}"
            )

            # Create simple strategies for intro slides
            intro_slide_strategies = []
            for i, slide in enumerate(intro_slides):
                role = "introduce"
                if slide.slide_type.value == "title":
                    role = "introduce"
                    key_points = ["Welcome students", "Introduce lecture topic"]
                elif "outline" in (slide.title or "").lower():
                    role = "introduce"
                    key_points = ["Preview lecture topics", "Set expectations"]
                else:
                    role = "transition"
                    key_points = ["Transition to main content"]

                intro_slide_strategies.append(SlideNarrationStrategy(
                    slide_index=i,
                    role=role,
                    concepts_to_introduce=[],
                    concepts_to_build_upon=[],
                    key_points=key_points,
                    avoid_repeating=[]
                ))

            # Create intro section strategy
            intro_strategy = SectionNarrationStrategy(
                section_index=0,  # Will be 0, and we'll increment others
                section_title="Introduction",
                start_slide=0,
                end_slide=first_section_start - 1,
                narrative_arc="Welcome students and introduce the lecture topic",
                slide_strategies=intro_slide_strategies
            )

            strategies.append(intro_strategy)

        # Adjust section index offset if we added intro section
        section_idx_offset = 1 if first_section_start > 0 else 0

        for section_idx, section in enumerate(global_plan.sections):
            # Get slides for this section
            section_slides = []
            for i in range(section.start_slide, section.end_slide + 1):
                if i < len(slides):
                    section_slides.append(slides[i])

            if not section_slides:
                print(
                    "🧠 ContextBuilder: section skipped (no slides) "
                    f"section_index={section_idx} title={section.title!r}"
                )
                continue  # Skip empty sections

            # Ask AI to create slide-by-slide strategy for this section
            stage_start = time.monotonic()
            print(
                "🧠 ContextBuilder: section strategy start "
                f"section_index={section_idx} slides={len(section_slides)} "
                f"title={section.title!r}"
            )
            strategy_response = await self.ai_provider.create_section_narration_strategy(
                section=section,
                section_slides=section_slides,
                global_context=global_plan
            )
            print(
                "🧠 ContextBuilder: section strategy done "
                f"section_index={section_idx} "
                f"({time.monotonic() - stage_start:.2f}s)"
            )

            # Parse response into SlideNarrationStrategy objects
            slide_strategies = []
            for slide_strat_data in strategy_response.get("slide_strategies", []):
                slide_strategies.append(SlideNarrationStrategy(
                    slide_index=slide_strat_data.get("slide_index", 0),
                    role=slide_strat_data.get("role", "elaborate"),
                    concepts_to_introduce=slide_strat_data.get("concepts_to_introduce", []),
                    concepts_to_build_upon=slide_strat_data.get("concepts_to_build_upon", []),
                    key_points=slide_strat_data.get("key_points", []),
                    avoid_repeating=slide_strat_data.get("avoid_repeating", [])
                ))
            print(
                "🧠 ContextBuilder: section strategy parsed "
                f"section_index={section_idx} slide_strategies={len(slide_strategies)}"
            )

            # Create section strategy
            section_strategy = SectionNarrationStrategy(
                section_index=section_idx + section_idx_offset,  # Offset by 1 if intro exists
                section_title=section.title,
                start_slide=section.start_slide,
                end_slide=section.end_slide,
                narrative_arc=strategy_response.get("narrative_arc", ""),
                slide_strategies=slide_strategies
            )

            strategies.append(section_strategy)

        return strategies

    async def build_context_with_stages(
        self,
        slides: List[SlideContent]
    ) -> Dict[str, Any]:
        """
        Build context and return intermediate results for debugging/inspection.

        Args:
            slides: List of all slides

        Returns:
            Dictionary with:
                - global_plan: Final GlobalContextPlan
                - structural_analysis: Raw structural analysis
                - visual_analysis: Raw visual analysis
                - token_usage: Token counts if available
        """
        print(
            "🧠 ContextBuilder: build_context_with_stages start "
            f"slides={len(slides)}"
        )
        # Run structural analysis
        structural_analysis = await self.ai_provider.analyze_structure(slides)

        # Collect images
        all_images = []
        for slide in slides:
            all_images.extend(slide.images)

        # Run visual analysis
        visual_analysis = {}
        if all_images:
            visual_analysis = await self.ai_provider.analyze_images(all_images, slides)

        # Synthesize
        global_plan = self._synthesize_plan(slides, structural_analysis, visual_analysis)

        # Get token usage if provider supports it
        token_usage = {}
        if hasattr(self.ai_provider, 'get_token_usage'):
            token_usage = self.ai_provider.get_token_usage()

        return {
            "global_plan": global_plan,
            "structural_analysis": structural_analysis,
            "visual_analysis": visual_analysis,
            "token_usage": token_usage
        }
