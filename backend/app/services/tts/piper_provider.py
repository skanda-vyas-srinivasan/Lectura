"""Piper TTS provider - Free, local, better quality than Edge TTS."""
import subprocess
from pathlib import Path
import tempfile
import os


class PiperTTSProvider:
    """
    Piper TTS provider using local neural TTS.

    - 100% free and unlimited
    - Runs locally (no API calls)
    - Better quality than Edge TTS
    - Fast generation
    """

    def __init__(self, voice: str = "en_US-amy-medium"):
        """
        Initialize Piper TTS.

        Args:
            voice: Voice model to use
                   Popular options:
                   - en_US-amy-medium (female, clear)
                   - en_US-ryan-medium (male, clear)
                   - en_US-libritts-high (very high quality but slower)
        """
        self.voice = voice
        self.model_dir = Path.home() / ".local" / "share" / "piper-voices"
        self.model_dir.mkdir(parents=True, exist_ok=True)

        # Download voice model if not exists
        self._ensure_model()

    def _ensure_model(self):
        """Download voice model if not present."""
        model_file = self.model_dir / f"{self.voice}.onnx"
        config_file = self.model_dir / f"{self.voice}.onnx.json"

        if not model_file.exists() or not config_file.exists():
            print(f"📥 Downloading Piper voice model: {self.voice}...")
            base_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{self.voice.replace('_', '-').replace('-', '/', 1)}"

            # Download model
            subprocess.run([
                "curl", "-L", "-o", str(model_file),
                f"{base_url}.onnx"
            ], check=True)

            # Download config
            subprocess.run([
                "curl", "-L", "-o", str(config_file),
                f"{base_url}.onnx.json"
            ], check=True)

            print(f"✅ Voice model downloaded!")

    async def generate_audio(self, text: str, output_path: str) -> None:
        """
        Generate audio from text using Piper TTS.

        Args:
            text: Text to convert to speech
            output_path: Path to save the audio file
        """
        model_file = self.model_dir / f"{self.voice}.onnx"

        # Use piper command line tool
        # piper reads from stdin and outputs to stdout
        with open(output_path, 'wb') as f:
            process = subprocess.Popen(
                ['piper', '--model', str(model_file), '--output_file', output_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            stdout, stderr = process.communicate(input=text.encode('utf-8'))

            if process.returncode != 0:
                raise Exception(f"Piper TTS failed: {stderr.decode('utf-8')}")
