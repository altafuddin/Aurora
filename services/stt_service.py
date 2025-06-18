# <-- AssemblyAI Adapter: handles all STT interaction
import assemblyai as aai
from config import ASSEMBLYAI_API_KEY
import sys

class AssemblyAITranscriber:
    def __init__(self):
        """
        Initializes the AssemblyAI transcriber.
        """
        if not ASSEMBLYAI_API_KEY:
            # This check is crucial for clear error messages at startup.
            print("FATAL ERROR: ASSEMBLYAI_API_KEY is not set. Please check your .env file.", file=sys.stderr)
            self.transcriber = None
            return
            
        aai.settings.api_key = ASSEMBLYAI_API_KEY
        self.transcriber = aai.Transcriber()
        # print("--- AssemblyAI Transcriber Initialized Successfully ---")

    def transcribe(self, audio_file_path: str) -> str:
        """
        Transcribes the given audio file.
        Returns the transcribed text or an error message.
        """
        if self.transcriber is None:
            return "Error: AssemblyAI service is not initialized due to missing API key."

        if not audio_file_path:
            return "Error: No audio file provided."
                
        if aai.settings.api_key is None:
            print("CRITICAL DEBUG: aai.settings.api_key is None just before transcription!")
        
        try:
            transcript = self.transcriber.transcribe(audio_file_path)

            if transcript.status == aai.TranscriptStatus.error:
                return f"Error: {transcript.error}"
            else:
                return transcript.text if transcript.text is not None else "Nothing transcribed."
        except Exception as e:
            print(f"An unexpected error occurred during transcription: {e}", file=sys.stderr)
            return "Error: An unexpected error occurred during transcription."