"""AWS Polly TTS provider with neural voices."""
import boto3
import os
from typing import Dict, Any


class PollyTTSProvider:
    """AWS Polly TTS provider with high-quality neural voices."""

    def __init__(
        self,
        voice_id: str = "Matthew",
        engine: str = "neural",
        aws_access_key_id: str = None,
        aws_secret_access_key: str = None,
        aws_region: str = "us-east-1"
    ):
        """
        Initialize AWS Polly TTS provider.

        Args:
            voice_id: Polly voice ID (e.g., "Matthew", "Joanna", "Salli")
            engine: Voice engine - "neural" (better quality) or "standard"
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key
            aws_region: AWS region
        """
        self.voice_id = voice_id
        self.engine = engine

        # Initialize boto3 client with explicit credentials
        self.client = boto3.client(
            'polly',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )

    async def generate_audio(self, text: str, output_path: str) -> Dict[str, Any]:
        """
        Generate audio from text using AWS Polly.

        Args:
            text: Text to convert to speech
            output_path: Path to save the audio file

        Returns:
            Dictionary with timing information (empty for now)
        """
        # Call Polly to synthesize speech
        response = self.client.synthesize_speech(
            Text=text,
            OutputFormat='mp3',
            VoiceId=self.voice_id,
            Engine=self.engine
        )

        # Save audio stream to file
        with open(output_path, 'wb') as f:
            f.write(response['AudioStream'].read())

        # Note: Polly doesn't provide word-level timing in standard synthesis
        # Would need SpeechMarkTypes for that, but adds complexity
        return {"timings": []}

    def get_available_voices(self) -> list:
        """Get list of available Polly voices."""
        response = self.client.describe_voices(Engine=self.engine)
        return [
            {
                "id": voice["Id"],
                "name": voice["Name"],
                "gender": voice["Gender"],
                "language": voice["LanguageCode"]
            }
            for voice in response["Voices"]
        ]
