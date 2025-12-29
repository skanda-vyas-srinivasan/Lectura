"""Gemini AI provider implementation using Google's Gemini 2.0 Flash (free tier)."""
import json
from typing import List, Dict, Any
import google.generativeai as genai

from app.models import SlideContent, ImageContent
from app.services.ai.base import AIProvider
from app.config import settings


class GeminiProvider(AIProvider):
    """
    AI provider implementation using Google Gemini 2.0 Flash.

    Gemini 2.0 Flash offers excellent free tier:
    - 1,500 requests per day (free!)
    - 15 requests per minute
    - Native vision support (multimodal)
    - 1M token context window
    - Good quality for both analysis and narration

    Perfect for prototyping and testing.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-2.5-flash"
    ):
        """
        Initialize Gemini provider.

        Args:
            api_key: Google AI API key (defaults to settings)
            model: Model to use (defaults to gemini-1.5-flash)
        """
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = model

        # Configure the API
        genai.configure(api_key=self.api_key)

        # Create the model
        self.model = genai.GenerativeModel(self.model_name)

        # Token tracking (Gemini API provides usage metadata)
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    async def analyze_structure(self, slides: List[SlideContent]) -> Dict[str, Any]:
        """
        Analyze the structural aspects of the lecture deck.

        Uses Gemini 2.0 Flash to understand:
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

        # Call Gemini
        response = self.model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.1,  # Low for analytical tasks
                "max_output_tokens": 16000,
            }
        )

        # Track tokens
        if hasattr(response, 'usage_metadata'):
            self.total_input_tokens += response.usage_metadata.prompt_token_count
            self.total_output_tokens += response.usage_metadata.candidates_token_count

        # Parse the JSON response
        response_text = response.text

        # Extract JSON from the response (handle markdown code blocks)
        json_text = self._extract_json(response_text)

        # Fix common JSON escape issues (LaTeX backslashes, etc.)
        json_text = self._fix_json_escapes(json_text)

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
        Analyze visual content using Gemini's native vision capabilities.

        Gemini 2.0 Flash has excellent multimodal support!

        Args:
            images: List of images to analyze
            slide_context: Associated slide content for context

        Returns:
            Dictionary with image analysis including key diagrams
        """
        if not images:
            return {"key_diagrams": []}

        # Limit to first 20 images to avoid token limits
        images_to_analyze = images[:20]

        # Build vision prompt
        prompt_text = self._build_vision_prompt(len(images_to_analyze))

        # Prepare content parts (text + images)
        content_parts = [prompt_text]

        # Add images (Gemini accepts base64 images directly)
        for idx, img in enumerate(images_to_analyze):
            if img.image_data:
                # Add context about which slide this is from
                slide_idx = img.extracted_from_slide
                slide_context_text = ""
                if slide_idx < len(slide_context):
                    slide = slide_context[slide_idx]
                    slide_context_text = f"Slide {slide_idx + 1}: {slide.title or '(No title)'}"

                content_parts.append(f"\n[Image {idx + 1} from {slide_context_text}]\n")

                # Add the image
                import base64
                image_bytes = base64.b64decode(img.image_data)
                content_parts.append({
                    "mime_type": f"image/{img.format}",
                    "data": image_bytes
                })

        # Call Gemini with vision
        response = self.model.generate_content(
            content_parts,
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 8000,
            }
        )

        # Track tokens
        if hasattr(response, 'usage_metadata'):
            self.total_input_tokens += response.usage_metadata.prompt_token_count
            self.total_output_tokens += response.usage_metadata.candidates_token_count

        # Parse response
        response_text = response.text

        # Extract key diagrams from the analysis
        key_diagrams = self._parse_vision_response(response_text, images_to_analyze)

        return {"key_diagrams": key_diagrams}

    async def create_section_narration_strategy(
        self,
        section: Any,
        section_slides: List[SlideContent],
        global_context: Any
    ) -> Dict[str, Any]:
        """
        Create slide-by-slide narration strategy for a section to avoid repetition.

        Args:
            section: Section object with title, start/end slides, summary, key concepts
            section_slides: All slides in this section
            global_context: GlobalContextPlan with full lecture understanding

        Returns:
            Dictionary with narrative_arc and slide_strategies
        """
        # Build prompt for section strategy
        prompt = f"""You are an expert educational content strategist. Create a slide-by-slide narration strategy for this lecture section to ensure smooth narrative flow WITHOUT REPETITION.

**SECTION INFORMATION:**
Title: {section.title}
Summary: {section.summary}
Key Concepts: {', '.join(section.key_concepts)}
Slides in section: {section.start_slide + 1} to {section.end_slide + 1} (total: {len(section_slides)} slides)

**SLIDE CONTENT IN THIS SECTION:**
"""
        for i, slide in enumerate(section_slides):
            slide_num = section.start_slide + i
            prompt += f"\n--- Slide {slide_num + 1} ---\n"
            prompt += f"Title: {slide.title or '(No title)'}\n"
            if slide.bullet_points:
                prompt += f"Bullets: {', '.join(slide.bullet_points[:5])}\n"
            if slide.special_contents:
                prompt += f"Special Content: {len(slide.special_contents)} items (definitions, theorems, etc.)\n"
            prompt += "\n"

        prompt += f"""
**YOUR TASK:**
Create a detailed slide-by-slide narration strategy that ensures each slide has a DISTINCT role in the narrative progression.

Return a JSON object with:
1. "narrative_arc": Overall narrative progression for this section (2-3 sentences)
2. "slide_strategies": Array of objects, one per slide, with:
   - "slide_index": Slide number (0-indexed)
   - "role": ONE of: "introduce", "elaborate", "example", "connect", "conclude"
   - "concepts_to_introduce": Array of NEW concepts introduced in THIS slide only
   - "concepts_to_build_upon": Array of concepts from PREVIOUS slides to reference
   - "key_points": Array of 2-3 main points to cover in narration for THIS slide
   - "avoid_repeating": Array of specific content already covered in previous slides (be explicit!)

**CRITICAL RULES:**
1. Each slide must have a UNIQUE role - don't repeat introductions!
2. Slide 1 introduces, slides 2+ build upon what came before
3. "avoid_repeating" must list SPECIFIC content from previous slides (e.g., "definition of affine combination already given in slide 1")
4. If multiple slides cover same concept, first slide INTRODUCES, later slides ELABORATE/APPLY/CONNECT
5. Be VERY explicit about what NOT to repeat

Return ONLY valid JSON, no other text.
"""

        # Call Gemini
        response = self.model.generate_content(prompt)

        # Track tokens
        if hasattr(response, 'usage_metadata'):
            self.total_input_tokens += response.usage_metadata.prompt_token_count
            self.total_output_tokens += response.usage_metadata.candidates_token_count

        # Parse JSON response
        response_text = response.text.strip()
        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        try:
            strategy_data = json.loads(response_text)
            return strategy_data
        except json.JSONDecodeError as e:
            print(f"⚠️  Warning: Failed to parse section strategy JSON: {e}")
            print(f"   Response: {response_text[:200]}...")
            # Return empty strategy as fallback
            return {
                "narrative_arc": "Progressive exploration of key concepts.",
                "slide_strategies": []
            }

    async def generate_section_narrations(
        self,
        section_slides: List[SlideContent],
        section_strategy: Any,
        global_plan: Dict[str, Any],
    ) -> Dict[int, str]:
        """
        Generate ALL narrations for a section as ONE continuous narrative.

        This prevents the "fresh start" problem where each slide is treated independently.
        """
        # Build continuous narration prompt
        prompt = f"""You are an expert lecturer delivering a live lecture. You will narrate an ENTIRE SECTION continuously, as if speaking to students in real-time.

**SECTION CONTEXT:**
Section: {section_strategy['section_title']}
Narrative Arc: {section_strategy['narrative_arc']}
Slides in section: {section_strategy['start_slide'] + 1} to {section_strategy['end_slide'] + 1}

**LECTURE CONTEXT:**
- Title: {global_plan.get('lecture_title', 'Unknown')}
- Audience: {global_plan.get('audience_level', 'intermediate')}

**CRITICAL INSTRUCTIONS:**
1. Write ONE CONTINUOUS NARRATION covering all {len(section_slides)} slides in this section
2. Flow naturally from slide to slide as if lecturing live
3. DO NOT treat each slide as a fresh start - maintain narrative continuity
4. Use transitions like "Now let's", "Moving on", "Building on this" between slides
5. Mark slide boundaries with "### SLIDE X ###" on its own line
6. **MATCH NARRATION LENGTH TO CONTENT**:
   - Title slides: ~20-40 words (just welcome and state topic)
   - Outline slides: ~50-100 words (briefly list topics, don't elaborate)
   - Section headers: ~15-30 words (just transition: "Moving on to...")
   - Content slides: ~150-250 words (explain concepts in detail)
7. **BE PROFESSIONAL AND CONCISE** - Don't add unnecessary fluff or embellishment
8. **INCREMENTAL BUILDS**: If a slide is marked as "[INCREMENTAL BUILD]":
   - ONLY narrate the NEW content that just appeared
   - Keep it brief (~50-100 words)
   - DO NOT repeat content from the previous slide
   - DO NOT say "on this same slide" - it's obvious from context

**SLIDE-BY-SLIDE STRATEGY:**
"""

        for slide_strat in section_strategy.get('slide_strategies', []):
            prompt += f"""
Slide {slide_strat['slide_index'] + 1}:
- Role: {slide_strat['role'].upper()}
- Introduce: {', '.join(slide_strat.get('concepts_to_introduce', [])) or 'None'}
- Build upon: {', '.join(slide_strat.get('concepts_to_build_upon', [])) or 'None'}
- Key points: {'; '.join(slide_strat.get('key_points', []))}
- AVOID REPEATING: {'; '.join(slide_strat.get('avoid_repeating', [])) or 'Nothing'}
"""

        prompt += f"""

**SLIDE CONTENT:**
"""
        for i, slide in enumerate(section_slides):
            slide_num = section_strategy['start_slide'] + i

            # Determine slide type for narration guidance
            slide_type_hint = ""
            if slide.slide_type.value == "title":
                slide_type_hint = "[TITLE SLIDE - Keep very brief, ~20-40 words]"
            elif "outline" in (slide.title or "").lower():
                slide_type_hint = "[OUTLINE SLIDE - Concise list, ~50-100 words]"
            elif slide.slide_type.value == "section_header" or (not slide.body_text.strip() or len(slide.body_text.strip()) < 100):
                slide_type_hint = "[SECTION HEADER - Brief transition, ~15-30 words]"

            # Check if this is an incremental build
            if slide.is_incremental_build:
                prompt += f"""
### SLIDE {slide_num + 1} ### [INCREMENTAL BUILD - SAME SLIDE AS SLIDE {slide.previous_slide_index + 1}]
⚠️ THIS SLIDE BUILDS ON PREVIOUS SLIDE - DO NOT RE-EXPLAIN PREVIOUS CONTENT!
Title: {slide.title or '(No title)'} (SAME AS BEFORE)
NEW CONTENT ONLY: {slide.new_content_only or 'N/A'}

NARRATION: Continue naturally and ONLY explain the NEW content that appeared (~50-100 words). Do NOT say "on this same slide".
"""
            else:
                prompt += f"""
### SLIDE {slide_num + 1} ### {slide_type_hint}
Title: {slide.title or '(No title)'}
Content: {slide.body_text[:500] if slide.body_text else 'N/A'}
Bullets: {', '.join(slide.bullet_points[:3]) if slide.bullet_points else 'None'}
"""

        prompt += """

**YOUR TASK:**
Write a continuous narration for this entire section. Start narrating Slide 1, then naturally flow to Slide 2, then Slide 3, etc.
Mark each slide's narration with "### SLIDE X ###" on its own line BEFORE that slide's narration.

NARRATION RULES:
- NO instructor names, universities, or personal info
- **EVERYTHING you say must be natural, speakable English** - as if you're talking to students in person

**CRITICAL: Convert ALL notation to natural speech. Examples:**
- NEVER say "x underscore 1" → SAY "x one" or "x sub one"
- NEVER say "x caret 2" → SAY "x squared"
- NEVER say "r caret n" → SAY "r to the n" or "r to the power of n"
- NEVER say "f parenthesis x parenthesis" → SAY "f of x"
- NEVER say "g of x plus h" → SAY "g of the quantity x plus h"
- NEVER say "theta" (Greek letter name) → SAY "theta" (pronounced naturally)
- NEVER say "element of" or "in symbol" → SAY "is in" or "belongs to"
- NEVER say "sum from i equals 1 to n" → SAY "the sum from i equals one to n"
- NEVER say "backslash" or "LaTeX commands" → Just speak the math naturally
- **NEVER use backticks (`) or any markdown formatting** → Just write plain spoken English
- **NO code formatting, NO backticks around variables or math** → Write everything as natural speech
- Subscripts: x₁ is "x one" or "x sub one", NOT "x subscript one"
- Superscripts (powers): x² is "x squared", 2⁵ is "two to the fifth", NOT "x caret 2"
- Superscripts (labels): x¹, x² can be "x one", "x two" if they're labeling variables (context-dependent)
- Function notation: f(x) is "f of x", g(t) is "g of t", h(x,y) is "h of x and y"

This applies to ANY subject: math, physics, biology, chemistry, computer science, etc.
Think: "How would I say this out loud to a student sitting across from me?"

**EXAMPLES - WRONG vs RIGHT:**

❌ WRONG: "Consider the vector *x sub 1* and *i sub q*..."
✅ RIGHT: "Consider the vector x one and i sub q..."

❌ WRONG: "The function `f(x) = x²` represents..."
✅ RIGHT: "The function f of x equals x squared represents..."

❌ WRONG: "We have *x* ∈ R^n where..."
✅ RIGHT: "We have x in R to the n where..."

❌ WRONG: "Let's examine **Definition 2.1**: An affine combination..."
✅ RIGHT: "Let's examine definition two point one: An affine combination..."

❌ WRONG: "The constraint is a'x ≤ b..."
✅ RIGHT: "The constraint is a transpose x is less than or equal to b..."

**CRITICAL: NO markdown (*bold*, `code`, **emphasis**), NO symbols (≤, ∈, ∀), NO technical notation - ONLY natural spoken English.**

Begin narrating now:
"""

        # Generate continuous narration
        response = self.model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.4,
                "max_output_tokens": 4000,
            }
        )

        # Track tokens
        if hasattr(response, 'usage_metadata'):
            self.total_input_tokens += response.usage_metadata.prompt_token_count
            self.total_output_tokens += response.usage_metadata.candidates_token_count

        # Parse response to extract individual slide narrations
        full_narration = response.text.strip()

        # Split by slide markers
        import re
        slide_pattern = r'### SLIDE (\d+) ###\s*\n(.*?)(?=### SLIDE \d+ ###|$)'
        matches = re.findall(slide_pattern, full_narration, re.DOTALL)

        # Build result dict
        narrations = {}
        for slide_num_str, narration_text in matches:
            slide_idx = int(slide_num_str) - 1  # Convert to 0-indexed
            narrations[slide_idx] = narration_text.strip()

        return narrations

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

        # Call Gemini
        response = self.model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.3,  # Slightly higher for natural language
                "max_output_tokens": 2000,
            }
        )

        # Track tokens
        if hasattr(response, 'usage_metadata'):
            self.total_input_tokens += response.usage_metadata.prompt_token_count
            self.total_output_tokens += response.usage_metadata.candidates_token_count

        return response.text.strip()

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

        # NEW: Extract section narration strategy for this slide
        strategy_context = ""
        section_strategies = global_plan.get("section_narration_strategies", [])
        for section_strategy in section_strategies:
            if section_strategy["start_slide"] <= slide.slide_index <= section_strategy["end_slide"]:
                # Found the section this slide belongs to
                for slide_strategy in section_strategy.get("slide_strategies", []):
                    if slide_strategy["slide_index"] == slide.slide_index:
                        # Found the strategy for THIS specific slide!
                        strategy_context = f"""
**NARRATION STRATEGY FOR THIS SLIDE (CRITICAL - FOLLOW THIS):**
Role in Section: {slide_strategy.get('role', 'elaborate').upper()}
Concepts to INTRODUCE in this slide: {', '.join(slide_strategy.get('concepts_to_introduce', [])) or 'None - build on previous'}
Concepts to BUILD UPON from previous slides: {', '.join(slide_strategy.get('concepts_to_build_upon', [])) or 'None'}
Key Points to Cover: {'; '.join(slide_strategy.get('key_points', []))}
AVOID REPEATING: {'; '.join(slide_strategy.get('avoid_repeating', [])) or 'Nothing specific'}

⚠️  CRITICAL: If "avoid_repeating" lists content, DO NOT re-explain it! Just reference it briefly if needed.
"""
                        break
                break

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
{strategy_context}

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

    def _fix_json_escapes(self, json_text: str) -> str:
        """Fix common JSON escape issues from LLM responses."""
        import re

        # Ultra aggressive: just remove all backslashes
        # LaTeX notation like \alpha, \subseteq shouldn't be in JSON responses anyway
        json_text = json_text.replace('\\', '')

        return json_text

    def _parse_vision_response(
        self, response_text: str, images: List[ImageContent]
    ) -> List[Dict[str, Any]]:
        """Parse the vision analysis response into key diagrams."""
        # Simple parsing - extract key information
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
