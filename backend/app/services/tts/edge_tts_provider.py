"""Edge TTS provider implementation (FREE!)."""
import asyncio
from pathlib import Path
import edge_tts
import re
from xml.sax.saxutils import escape

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

    def _to_ssml(self, text: str) -> str:
        """Convert plain text into SSML with more natural pacing and emphasis."""
        sentence_pattern = re.compile(r'[^.!?]+[.!?]|[^.!?]+$')
        sentences = [s.strip() for s in sentence_pattern.findall(text) if s.strip()]
        ssml_sentences = []

        def contour(escaped_sentence: str) -> str:
            # Add a stronger pitch contour for expressiveness.
            parts = re.split(r'([,;:])', escaped_sentence, maxsplit=1)
            if len(parts) >= 3:
                head = parts[0] + parts[1]
                tail = parts[2]
                return (
                    f"<prosody pitch='+6%' volume='+1dB'>{head}</prosody>"
                    f"<prosody pitch='-4%'>{tail}</prosody>"
                )
            mid = len(escaped_sentence) // 2
            return (
                f"<prosody pitch='+6%' volume='+1dB'>{escaped_sentence[:mid]}</prosody>"
                f"<prosody pitch='-4%'>{escaped_sentence[mid:]}</prosody>"
            )

        for sentence in sentences:
            escaped = escape(sentence, {'"': '&quot;'})
            # Emphasize quoted terms.
            escaped = re.sub(
                r'&quot;([^&]+?)&quot;',
                r'<emphasis level="moderate">\1</emphasis>',
                escaped
            )
            # Emphasize all-caps terms (acronyms, key terms).
            escaped = re.sub(
                r'\b([A-Z]{3,})\b',
                r'<emphasis level="moderate">\1</emphasis>',
                escaped
            )
            # Short pauses after commas/semicolons/colons (avoid 1,000).
            escaped = re.sub(r'(?<!\d),(?!\d)', r',<break time="90ms"/>', escaped)
            escaped = re.sub(r';', r';<break time="120ms"/>', escaped)
            escaped = re.sub(r':', r':<break time="120ms"/>', escaped)

            # Slow down math-heavy sentences slightly.
            if re.search(
                r'\b(equals|equal|less than|greater than|sum|integral|derivative|matrix|vector|transpose|squared|cubed|to the|over|divided by)\b',
                sentence,
                re.IGNORECASE
            ):
                escaped = f"<prosody rate='92%'>{escaped}</prosody>"

            escaped = contour(escaped)
            ssml_sentences.append(f"<s>{escaped}</s>")

        body = " <break time='180ms'/> ".join(ssml_sentences)
        return f"<speak><prosody rate='104%'>{body}</prosody></speak>"

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

        # Generate audio with word timing using SubMaker
        ssml = self._to_ssml(text)
        submaker = edge_tts.SubMaker()

        try:
            communicate = edge_tts.Communicate(ssml, voice_to_use)
            with open(str(output_path), "wb") as audio_file:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_file.write(chunk["data"])
                    elif chunk["type"] in ["WordBoundary", "SentenceBoundary"]:
                        submaker.feed(chunk)
        except Exception:
            # Retry once with the same safe SSML.
            communicate = edge_tts.Communicate(ssml, voice_to_use)
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
