# <-- Google TTS Adapter: handles all TTS interaction
# In: services/tts_service.py

from google.cloud import texttospeech
import sys
import os

class GoogleTTS:
    def __init__(self):
        """
        Initializes the Google Cloud Text-to-Speech client.
        """
        try:
            self.client = texttospeech.TextToSpeechClient()
            # A natural, friendly-sounding voice
            self.voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Studio-O" # A high-quality WaveNet voice
            )
            self.audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            print("--- Google TTS Service Initialized Successfully ---")
        except Exception as e:
            print(f"FATAL ERROR: Could not initialize Google TTS. Check credentials.", file=sys.stderr)
            print(f"Error details: {e}", file=sys.stderr)
            self.client = None

    def synthesize_speech(self, text: str, output_filepath: str = "output.mp3") -> str:
        """
        Synthesizes speech from text and saves it to a file.

        Args:
            text: The text to synthesize.
            output_filepath: The path to save the MP3 file.

        Returns:
            The path to the created audio file, or None if an error occurred.
        """
        if not self.client:
            return None

        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)
            response = self.client.synthesize_speech(
                input=synthesis_input, voice=self.voice, audio_config=self.audio_config
            )
            
            with open(output_filepath, "wb") as out:
                out.write(response.audio_content)
            
            return output_filepath
        except Exception as e:
            print(f"Error during speech synthesis: {e}", file=sys.stderr)
            return None