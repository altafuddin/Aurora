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

            # QUICK FIXES FOR BETTER BANGLADESHI ENGLISH RECOGNITION:
            
            # 1. Set language to Indian English (closest to Bangladeshi English patterns)
            self.speech_config.speech_recognition_language = "en-IN"
            
            # 2. Enable detailed word-level timing and confidence scores
            self.speech_config.request_word_level_timestamps()
            self.speech_config.output_format = speechsdk.OutputFormat.Detailed
            
            # 3. Add profanity filtering off (sometimes filters valid words)
            self.speech_config.set_profanity(speechsdk.ProfanityOption.Raw)
            
            # 4. Enable phrase hints for common words that might be misrecognized
            # You can add common Bangladeshi English words/phrases here
            # phrase_list_grammar = speechsdk.PhraseListGrammar.from_recognizer(None)
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

            # Optional: Enable prosody assessment for rhythm/intonation data
            pronunciation_config.enable_prosody_assessment() # Optional: gets rhythm/intonation data

            # Enable content assessment for more detailed feedback
            pronunciation_config.enable_content_assessment_with_topic("")

            # --- Create the main Speech Recognizer ---
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )

            # IMPROVEMENT: Add phrase hints for better recognition
            phrase_list_grammar = speechsdk.PhraseListGrammar.from_recognizer(speech_recognizer)
            

                        # Add common words that might be mispronounced by Bangladeshi speakers
            common_words = [
                "actually", "generally", "specifically", "particularly", 
                "university", "development", "government", "technology",
                "available", "important", "different", "necessary",
                "education", "experience", "opportunity", "environment"
            ]
            
            for word in common_words:
                phrase_list_grammar.addPhrase(word)
                
            # Apply the pronunciation config to the recognizer
            pronunciation_config.apply_to(speech_recognizer)

            # Add timeout and retry logic
            speech_recognizer.session_started.connect(lambda evt: print(f"LOG: Recognition session started: {evt}"))
            speech_recognizer.session_stopped.connect(lambda evt: print(f"LOG: Recognition session stopped: {evt}"))

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
                    # IMPROVEMENT: Log the raw JSON for debugging
                    print(f"LOG: Raw Azure JSON response length: {len(pronunciation_result_json)} characters")

                    report = AzurePronunciationReport.model_validate_json(pronunciation_result_json)
                    print("LOG: Azure response successfully parsed and validated.")
                    return report
                else:
                    print("ERROR: No JSON result returned from Azure Speech Service.", file=sys.stderr)
                    return None
            elif result.reason == speechsdk.ResultReason.NoMatch:
                print("LOG: Azure Speech could not recognize any speech.", file=sys.stderr)
                print(f"LOG: NoMatch details: {result.no_match_details}")
                return None
            
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                print(f"ERROR: Azure Speech recognition canceled. Reason: {cancellation_details.reason}", file=sys.stderr)
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    print(f"Error details: {cancellation_details.error_details}", file=sys.stderr)
                    # print(f"Error code: {cancellation_details.error_code}")
                return None
            
            return None

        # --- Correct Error Handling for Validation ---
        except ValidationError as e:
            print(f"FATAL ERROR: Pydantic validation failed for Azure response. The API structure may have changed. Details: {e}", file=sys.stderr)
            if 'pronunciation_result_json' in locals() and pronunciation_result_json:
                print(f"Raw JSON that failed validation: {pronunciation_result_json[:500]}...")
            return None
        # ---------------------------------------------
        except Exception as e:
            print(f"An unexpected error occurred in AzureSpeechService: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return None