"""Base interface for TTS providers."""
from abc import ABC, abstractmethod
from pathlib import Path


class TTSProvider(ABC):
    """Abstract base class for text-to-speech providers."""

    @abstractmethod
    async def generate_audio(
        self,
        text: str,
        output_path: str | Path,
        voice: str | None = None
    ) -> Path:
        """
        Generate audio from text.

        Args:
            text: The text to convert to speech
            output_path: Where to save the audio file
            voice: Optional voice ID/name to use

        Returns:
            Path to the generated audio file
        """
        pass

    @abstractmethod
    def get_available_voices(self) -> list[str]:
        """
        Get list of available voice IDs.

        Returns:
            List of voice identifiers
        """
        pass
