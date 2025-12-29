"""Google Cloud TTS provider - High quality, generous free tier."""
from google.cloud import texttospeech_v1beta1 as texttospeech
from google.oauth2 import service_account
import os
from pathlib import Path


class GoogleTTSProvider:
    """
    Google Cloud Text-to-Speech provider.

    Free tier: 4 million characters/month (Standard voices)
    WaveNet/Neural2: 1 million characters/month free

    Way better quality than Edge TTS, sounds much more natural.
    """

    def __init__(self, voice_name: str = "en-US-Neural2-J", language_code: str = "en-US", credentials_path: str = None):
        """
        Initialize Google Cloud TTS.

        Args:
            voice_name: Voice to use
                       Good options:
                       - en-US-Neural2-J (male, natural)
                       - en-US-Neural2-F (female, natural)
                       - en-US-Neural2-C (female, clear)
                       - en-US-Neural2-D (male, professional)
            language_code: Language code (default: en-US)
            credentials_path: Path to service account JSON file
        """
        # Load credentials from file
        if credentials_path and Path(credentials_path).exists():
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            self.client = texttospeech.TextToSpeechClient(credentials=credentials)
        else:
            # Try default credentials
            self.client = texttospeech.TextToSpeechClient()

        self.voice_name = voice_name
        self.language_code = language_code

    async def generate_audio(self, text: str, output_path: str) -> dict:
        """
        Generate audio from text using Google Cloud TTS with word-level timing (v1beta1).

        Args:
            text: Text to convert to speech
            output_path: Path to save the audio file (MP3)

        Returns:
            dict: Word-level timing information
        """
        import re

        # Split text into words and create SSML with marks for each word
        words = text.split()
        ssml_parts = ['<speak>']

        for i, word in enumerate(words):
            # Add mark before each word for timing
            ssml_parts.append(f'<mark name="word_{i}"/>{word}')

        ssml_parts.append('</speak>')
        ssml_text = ' '.join(ssml_parts)

        # Set up the synthesis input with SSML
        synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)

        # Build the voice request
        voice = texttospeech.VoiceSelectionParams(
            language_code=self.language_code,
            name=self.voice_name
        )

        # Select the audio encoding
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0.0
        )

        # Construct the request with timepoint data enabled (v1beta1)
        request = texttospeech.SynthesizeSpeechRequest(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
            enable_time_pointing=[texttospeech.SynthesizeSpeechRequest.TimepointType.SSML_MARK]
        )

        # Perform the text-to-speech request
        response = self.client.synthesize_speech(request=request)

        # Write the response to the output file
        with open(output_path, 'wb') as out:
            out.write(response.audio_content)

        # Extract word timings and map back to actual words
        word_timings = []
        if hasattr(response, 'timepoints') and response.timepoints:
            for timepoint in response.timepoints:
                # Extract word index from mark name (word_0, word_1, etc.)
                match = re.match(r'word_(\d+)', timepoint.mark_name)
                if match:
                    word_idx = int(match.group(1))
                    if word_idx < len(words):
                        word_timings.append({
                            "word": words[word_idx],
                            "start_time": timepoint.time_seconds
                        })

        return {"timings": word_timings}
