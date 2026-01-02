"""AWS Polly TTS provider with neural voices."""
import boto3
import os
import re
from typing import Dict, Any
from xml.sax.saxutils import escape
from botocore.exceptions import ClientError


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
        Generate audio from text using AWS Polly with word timings.

        Args:
            text: Text to convert to speech
            output_path: Path to save the audio file

        Returns:
            Dictionary with timing information
        """
        def to_ssml(raw_text: str) -> str:
            sentence_pattern = re.compile(r'[^.!?]+[.!?]|[^.!?]+$')
            sentences = [s.strip() for s in sentence_pattern.findall(raw_text) if s.strip()]
            ssml_sentences = []

            for sentence in sentences:
                escaped = escape(sentence, {'"': '&quot;'})
                escaped = re.sub(r'(?<!\d),(?!\d)', r',<break time="75ms"/>', escaped)
                escaped = re.sub(r';', r';<break time="105ms"/>', escaped)
                escaped = re.sub(r':', r':<break time="105ms"/>', escaped)

                rate = "102%"
                if re.search(
                    r'\b(equals|equal|less than|greater than|sum|integral|derivative|matrix|vector|transpose|squared|cubed|to the|over|divided by)\b',
                    sentence,
                    re.IGNORECASE
                ):
                    rate = "92%"

                ssml_sentences.append(f"<s><prosody rate='{rate}'>{escaped}</prosody></s>")

            body = " <break time='150ms'/> ".join(ssml_sentences)
            return f"<speak>{body}</speak>"

        def to_simple_ssml(raw_text: str) -> str:
            escaped = escape(raw_text, {'"': '&quot;'})
            return f"<speak>{escaped}</speak>"

        ssml = to_ssml(text)
        text_type = "ssml"
        engine = self.engine

        def synthesize(ssml_payload: str):
            return self.client.synthesize_speech(
                Text=ssml_payload,
                TextType=text_type,
                OutputFormat='mp3',
                VoiceId=self.voice_id,
                Engine=engine
            )

        def chunk_text(raw_text: str, max_chars: int = 2500) -> list[str]:
            sentence_pattern = re.compile(r'[^.!?]+[.!?]|[^.!?]+$')
            sentences = [s.strip() for s in sentence_pattern.findall(raw_text) if s.strip()]
            chunks = []
            current = []
            current_len = 0
            for sentence in sentences:
                if current and current_len + len(sentence) + 1 > max_chars:
                    chunks.append(" ".join(current))
                    current = []
                    current_len = 0
                current.append(sentence)
                current_len += len(sentence) + 1
            if current:
                chunks.append(" ".join(current))
            return chunks

        # Generate audio
        chunked = False
        try:
            audio_response = synthesize(ssml)
            audio_bytes = audio_response['AudioStream'].read()
        except ClientError as exc:
            error_message = str(exc)
            if "TextLengthExceededException" in error_message:
                chunked = True
                audio_bytes = b""
                for chunk in chunk_text(text):
                    chunk_ssml = to_ssml(chunk)
                    chunk_audio = synthesize(chunk_ssml)['AudioStream'].read()
                    audio_bytes += chunk_audio
            elif "InvalidSsmlException" in error_message or "Unsupported Neural feature" in error_message:
                ssml = to_simple_ssml(text)
                if engine == "neural":
                    engine = "standard"
                audio_response = synthesize(ssml)
                audio_bytes = audio_response['AudioStream'].read()
            else:
                raise

        # Save audio stream to file
        with open(output_path, 'wb') as f:
            f.write(audio_bytes)

        # Get speech marks for word-level timing
        if chunked:
            return {"timings": [], "timings_unavailable": True}

        marks_response = self.client.synthesize_speech(
            Text=ssml,
            TextType=text_type,
            OutputFormat='json',
            VoiceId=self.voice_id,
            Engine=engine,
            SpeechMarkTypes=['sentence']  # Get sentence boundaries
        )

        # Parse speech marks (newline-delimited JSON)
        word_timings = []
        marks_data = marks_response['AudioStream'].read().decode('utf-8')

        for line in marks_data.strip().split('\n'):
            if line:
                import json
                mark = json.loads(line)
                if mark['type'] == 'sentence':
                    word_timings.append({
                        "word": mark['value'],
                        "start_time": mark['time'] / 1000.0  # Convert ms to seconds
                    })

        return {"timings": word_timings}

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
