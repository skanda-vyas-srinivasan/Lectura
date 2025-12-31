"""Text-to-Speech services for the lecture system."""

from app.services.tts.base import TTSProvider
from app.services.tts.edge_tts_provider import EdgeTTSProvider
from app.services.tts.polly_provider import PollyTTSProvider

__all__ = ["TTSProvider", "EdgeTTSProvider", "PollyTTSProvider"]
