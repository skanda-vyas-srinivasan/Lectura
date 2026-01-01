"""Edge TTS provider implementation (FREE!)."""
import asyncio
from pathlib import Path
import edge_tts
import re

from app.services.tts.base import TTSProvider


class EdgeTTSProvider(TTSProvider):
    """
    TTS provider using Microsoft Edge TTS (completely FREE!).

    Features:
    - No API key needed
    - Good quality voices
    - Multiple languages supported
    - Fast generation
    """

    # Popular English voices
    DEFAULT_VOICES = {
        "male": "en-US-GuyNeural",
        "female": "en-US-JennyNeural",
        "male_uk": "en-GB-RyanNeural",
        "female_uk": "en-GB-SoniaNeural",
    }

    def __init__(self, voice: str = "en-US-GuyNeural"):
        """
        Initialize Edge TTS provider.

        Args:
            voice: Voice ID to use (defaults to male US voice)
        """
        self.voice = voice
        self._debug_dumped = False

    def _normalize_text(self, text: str) -> str:
        """Normalize text for Edge TTS without SSML."""
        return re.sub(r'\s+', ' ', text).strip()

    async def generate_audio(
        self,
        text: str,
        output_path: str | Path,
        voice: str | None = None
    ) -> dict:
        """
        Generate audio from text using Edge TTS with word-level timing.

        Args:
            text: The text to convert to speech
            output_path: Where to save the audio file (.mp3)
            voice: Optional voice ID (uses default if not provided)

        Returns:
            dict: Contains 'timings' list with word-level timing info
        """
        output_path = Path(output_path)
        voice_to_use = voice or self.voice

        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate audio with word timing using SubMaker (plain text; no SSML)
        plain_text = self._normalize_text(text)
        submaker = edge_tts.SubMaker()

        try:
            communicate = edge_tts.Communicate(
                plain_text,
                voice_to_use,
                rate="+4%",
                pitch="+0Hz",
                volume="+0%",
            )
            with open(str(output_path), "wb") as audio_file:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_file.write(chunk["data"])
                    elif chunk["type"] in ["WordBoundary", "SentenceBoundary"]:
                        submaker.feed(chunk)
        except Exception:
            # Retry once with the same safe text.
            communicate = edge_tts.Communicate(
                plain_text,
                voice_to_use,
                rate="+4%",
                pitch="+0Hz",
                volume="+0%",
            )
            with open(str(output_path), "wb") as audio_file:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_file.write(chunk["data"])
                    elif chunk["type"] in ["WordBoundary", "SentenceBoundary"]:
                        submaker.feed(chunk)

        # Extract sentence-level timings from SubMaker cues
        # Edge TTS only provides sentence boundaries, so we show full sentences
        word_timings = []
        for cue in submaker.cues:
            # Get sentence timing
            start_seconds = cue.start.total_seconds()

            # Return whole sentence as a single "word" timing
            # This makes subtitles show the full sentence at once
            word_timings.append({
                "word": cue.content.strip(),
                "start_time": start_seconds
            })

        return {"timings": word_timings}

    def get_available_voices(self) -> list[str]:
        """
        Get list of available Edge TTS voices.

        Returns:
            List of popular voice identifiers
        """
        return list(self.DEFAULT_VOICES.values())

    @staticmethod
    async def list_all_voices():
        """
        List ALL available Edge TTS voices.

        Returns:
            List of voice objects with detailed info
        """
        voices = await edge_tts.list_voices()
        return voices

    @staticmethod
    def get_voice_by_language(language: str = "en") -> str:
        """
        Get a default voice for a given language.

        Args:
            language: Language code (e.g., 'en', 'es', 'fr')

        Returns:
            Voice ID for that language
        """
        language_defaults = {
            "en": "en-US-GuyNeural",
            "es": "es-ES-AlvaroNeural",
            "fr": "fr-FR-HenriNeural",
            "de": "de-DE-ConradNeural",
            "it": "it-IT-DiegoNeural",
            "pt": "pt-BR-AntonioNeural",
            "zh": "zh-CN-YunxiNeural",
            "ja": "ja-JP-KeitaNeural",
            "ko": "ko-KR-InJoonNeural",
        }
        return language_defaults.get(language, "en-US-GuyNeural")
