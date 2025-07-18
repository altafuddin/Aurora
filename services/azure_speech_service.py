# In: services/azure_speech_service.py

import azure.cognitiveservices.speech as speechsdk
import json
import sys
from config import AZURE_SPEECH_KEY, AZURE_SPEECH_REGION
from logic.audio_models import AzurePronunciationReport
from pydantic import ValidationError


class AzureSpeechService:
    def __init__(self):
        """
        Initializes the Azure Speech Service client.
        """
        if not all([AZURE_SPEECH_KEY, AZURE_SPEECH_REGION]):
            print("FATAL ERROR: AZURE_SPEECH_KEY or AZURE_SPEECH_REGION is not set.", file=sys.stderr)
            self.speech_config = None
            return

        try:
            self.speech_config = speechsdk.SpeechConfig(
                subscription=AZURE_SPEECH_KEY, 
                region=AZURE_SPEECH_REGION
            )
            print("--- Azure Speech Service Initialized Successfully ---")
        except Exception as e:
            print(f"Error initializing Azure Speech Service: {e}", file=sys.stderr)
            self.speech_config = None

    def get_pronunciation_assessment(self, audio_filepath: str) -> AzurePronunciationReport | None:
        """
        Performs "unscripted" pronunciation assessment on an audio file.

        This single API call returns both the transcribed text and a detailed
        pronunciation analysis report.

        Args:
            audio_filepath: The path to the user's audio file.

        Returns:
            A parsed and validated Pydantic model.
        """
        if not self.speech_config:
            return None

        try:
            # --- Configuration for the audio input ---
            audio_config = speechsdk.audio.AudioConfig(filename=audio_filepath)

            # --- Configuration for the Pronunciation Assessment ---
            # We specify grading system, granularity, and enable fluency/accuracy scores.
            pronunciation_config = speechsdk.PronunciationAssessmentConfig(
                grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
                granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
                enable_miscue=False # We are not comparing to a reference script
            )
            pronunciation_config.enable_prosody_assessment() # Optional: gets rhythm/intonation data

            # --- Create the main Speech Recognizer ---
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
            
            # Apply the pronunciation config to the recognizer
            pronunciation_config.apply_to(speech_recognizer)

            # --- Start the single-shot recognition and assessment ---
            print("LOG: Sending audio to Azure for transcription and assessment...")
            result = speech_recognizer.recognize_once()

            # --- Process the result ---
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                print("LOG: Received successful response from Azure.")
                # The result is a JSON string stored in the properties.
                pronunciation_result_json = result.properties.get(
                    speechsdk.PropertyId.SpeechServiceResponse_JsonResult
                )
                # --- Use Pydantic for Validation ---
                if pronunciation_result_json is not None:
                    report = AzurePronunciationReport.model_validate_json(pronunciation_result_json)
                    print("LOG: Azure response successfully parsed and validated.")
                    return report
                else:
                    print("ERROR: No JSON result returned from Azure Speech Service.", file=sys.stderr)
                    return None
            elif result.reason == speechsdk.ResultReason.NoMatch:
                print("LOG: Azure Speech could not recognize any speech.", file=sys.stderr)
                return None
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                print(f"ERROR: Azure Speech recognition canceled. Reason: {cancellation_details.reason}", file=sys.stderr)
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    print(f"Error details: {cancellation_details.error_details}", file=sys.stderr)
                return None
            
            return None

        # --- Correct Error Handling for Validation ---
        except ValidationError as e:
            print(f"FATAL ERROR: Pydantic validation failed for Azure response. The API structure may have changed. Details: {e}", file=sys.stderr)
            return None
        # ---------------------------------------------
        except Exception as e:
            print(f"An unexpected error occurred in AzureSpeechService: {e}", file=sys.stderr)
            return None