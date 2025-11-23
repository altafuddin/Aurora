# <-- Google TTS Adapter: handles all TTS interaction
# In: services/tts_service.py

from google.cloud import texttospeech
import sys
import os
import tempfile
import uuid
import time
import logging

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

    def synthesize_speech(self, text: str, output_filepath: str = None) -> str:
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

        char_count = len(text)
        start_time = time.time()
        try:
            logging.info(f"API: GoogleTTS.synthesize_speech | status=starting | chars={char_count}")
            # If no output path specified, create a unique temp file
            if output_filepath is None:
                # Create unique filename in /tmp directory
                unique_id = str(uuid.uuid4())[:8]
                output_filepath = f"/tmp/tts_output_{unique_id}.mp3"
            
            # Ensure we're writing to /tmp if no full path given
            if not output_filepath.startswith('/'):
                filename = os.path.basename(output_filepath)
                output_filepath = f"/tmp/{filename}"
            
            synthesis_input = texttospeech.SynthesisInput(text=text)
            response = self.client.synthesize_speech(
                input=synthesis_input, voice=self.voice, audio_config=self.audio_config
            )
            
            with open(output_filepath, "wb") as out:
                out.write(response.audio_content)
            
            elapsed = time.time() - start_time
            logging.info(f"API: GoogleTTS.synthesize_speech | status=success | duration={elapsed:.2f}s | chars={char_count}")
            print(f"✅ TTS audio saved to: {output_filepath}")
            return output_filepath
            
        except Exception as e:
            elapsed = time.time() - start_time
            logging.error(f"API: GoogleTTS.synthesize_speech | status=error | duration={elapsed:.2f}s | chars={char_count} | error={str(e)}")
            print(f"Error during speech synthesis: {e}", file=sys.stderr)
            return None