# In: services/azure_speech_service.py

import azure.cognitiveservices.speech as speechsdk
import json
import time
import logging
import wave
import os
import tempfile
from typing import List, Optional
from config import AZURE_SPEECH_KEY, AZURE_SPEECH_REGION
from logic.audio_models import AzurePronunciationReport, NBestResult, WordResult, PhonemeResult
from pydantic import ValidationError

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    logging.warning("pydub not available, using fallback chunking method")

class AzureSpeechService:
    def __init__(self):
        """
        Initializes the Azure Speech Service client.
        """
        if not all([AZURE_SPEECH_KEY, AZURE_SPEECH_REGION]):
            logging.critical("AZURE_SPEECH_KEY or AZURE_SPEECH_REGION is not set.")
            self.speech_config = None
            return

        try:
            self.speech_config = speechsdk.SpeechConfig(
                subscription=AZURE_SPEECH_KEY, 
                region=AZURE_SPEECH_REGION
            )

            self.speech_config.speech_recognition_language = "en-US"            
            
            # Enable detailed word-level timing and confidence scores
            self.speech_config.request_word_level_timestamps()
            self.speech_config.output_format = speechsdk.OutputFormat.Detailed
            
            # Add profanity filtering off (sometimes filters valid words)
            self.speech_config.set_profanity(speechsdk.ProfanityOption.Raw)
            
            logging.info("--- Azure Speech Service Initialized Successfully ---")
        except Exception as e:
            logging.error(f"Error initializing Azure Speech Service: {e}", exc_info=True)
            self.speech_config = None

    def get_pronunciation_assessment(self, audio_filepath: str) -> Optional[AzurePronunciationReport]:
        """
        Main method that automatically chooses between simple and chunked processing
        based on audio duration. This is your drop-in replacement.
        """
        if not self.speech_config:
            logging.error("Speech config not initialized")
            return None

        try:
            # Get audio duration
            duration = self._get_audio_duration(audio_filepath)
            if duration is None:
                logging.error("Could not determine audio duration")
                return None

            logging.info(f"Audio duration: {duration:.2f} seconds")

            # Choose processing method based on duration
            if duration <= 25:  # Use simple method for short audio
                logging.info("Using simple recognition for short audio")
                return self._process_single_audio(audio_filepath)
            else:  # Use chunked method for long audio
                logging.info("Using chunked recognition for long audio")
                return self._process_chunked_audio(audio_filepath)

        except Exception as e:
            logging.error(f"Error in pronunciation assessment: {e}", exc_info=True)
            return None

    def _get_audio_duration(self, filepath: str) -> Optional[float]:
        """Get audio duration in seconds"""
        try:
            with wave.open(filepath, 'rb') as wav_file:
                frames = wav_file.getnframes()
                sample_rate = wav_file.getframerate()
                duration = frames / float(sample_rate)
                return duration
        except Exception as e:
            logging.error(f"Error getting audio duration: {e}")
            return None

    def _process_single_audio(self, audio_filepath: str) -> Optional[AzurePronunciationReport]:
        """Process audio using single recognition (for short audio)"""
        try:
            # Simple file-based audio config
            audio_config = speechsdk.audio.AudioConfig(filename=audio_filepath)

            # Create speech recognizer
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config, #type: ignore
                audio_config=audio_config
            )

            # Configure pronunciation assessment
            pronunciation_config = speechsdk.PronunciationAssessmentConfig(
                grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
                granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
                enable_miscue=False
            )
            
            # Enable prosody assessment
            pronunciation_config.enable_prosody_assessment()
            pronunciation_config.enable_content_assessment_with_topic("")
            pronunciation_config.apply_to(speech_recognizer)

            logging.info("Starting single recognition with pronunciation assessment...")
            
            # Perform single recognition
            result = speech_recognizer.recognize_once()
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                logging.info(f"Recognized: {result.text}")
                
                # Get the detailed JSON result
                pronunciation_result_json = result.properties.get(
                    speechsdk.PropertyId.SpeechServiceResponse_JsonResult
                )
                
                if pronunciation_result_json:
                    result_data = json.loads(pronunciation_result_json)
                    
                    if self._validate_result_structure(result_data):
                        report = AzurePronunciationReport.model_validate_json(json.dumps(result_data))
                        logging.info("✅ Single recognition completed successfully")
                        return report
                    else:
                        logging.error("Result structure validation failed")
                        return None
                else:
                    logging.error("No pronunciation result JSON found")
                    return None
                    
            else:
                self._log_recognition_failure(result)
                return None

        except Exception as e:
            logging.error(f"Error in single audio processing: {e}", exc_info=True)
            return None

    def _process_chunked_audio(self, audio_filepath: str) -> Optional[AzurePronunciationReport]:
        """Process long audio by splitting into chunks"""
        try:
            # Split audio into chunks
            chunk_files = self._split_audio_into_chunks(audio_filepath, chunk_duration=15)
            
            if not chunk_files:
                logging.error("Failed to create audio chunks")
                return None

            logging.info(f"Created {len(chunk_files)} audio chunks")

            # Process each chunk
            chunk_results = []
            for i, chunk_file in enumerate(chunk_files):
                logging.info(f"Processing chunk {i+1}/{len(chunk_files)}")
                
                chunk_result = self._process_single_audio(chunk_file)
                if chunk_result:
                    chunk_results.append(chunk_result)
                else:
                    logging.warning(f"Failed to process chunk {i+1}")

            # Cleanup temporary chunk files
            self._cleanup_chunk_files(chunk_files)

            if not chunk_results:
                logging.error("No chunks were successfully processed")
                return None

            # Combine all chunk results into a single report
            combined_result = self._combine_chunk_results(chunk_results)
            logging.info(f"✅ Successfully combined {len(chunk_results)} chunks")
            return combined_result

        except Exception as e:
            logging.error(f"Error in chunked audio processing: {e}", exc_info=True)
            return None

    def _split_audio_into_chunks(self, audio_filepath: str, chunk_duration: int = 15) -> List[str]:
        """Split audio file into smaller chunks"""
        chunk_files = []
        
        try:
            if PYDUB_AVAILABLE:
                # Use pydub for better audio handling
                audio = AudioSegment.from_wav(audio_filepath)
                chunk_length_ms = chunk_duration * 1000
                
                for i in range(0, len(audio), chunk_length_ms):
                    chunk = audio[i:i + chunk_length_ms]
                    
                    # Create temporary file
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                        chunk_path = temp_file.name
                    
                    # Export chunk
                    chunk.export(chunk_path, format="wav", parameters=["-ar", "16000", "-ac", "1"])
                    chunk_files.append(chunk_path)
                    
                logging.info(f"Created {len(chunk_files)} chunks using pydub")
                
            else:
                # Fallback: use wave library (more limited)
                chunk_files = self._split_audio_with_wave(audio_filepath, chunk_duration)
                
        except Exception as e:
            logging.error(f"Error splitting audio: {e}")
            return []
            
        return chunk_files

    def _split_audio_with_wave(self, audio_filepath: str, chunk_duration: int) -> List[str]:
        """Fallback method to split audio using wave library"""
        chunk_files = []
        
        try:
            with wave.open(audio_filepath, 'rb') as wav_file:
                params = wav_file.getparams()
                sample_rate = params.framerate
                chunk_frames = sample_rate * chunk_duration
                
                chunk_num = 0
                while True:
                    frames = wav_file.readframes(chunk_frames)
                    if not frames:
                        break
                    
                    # Create chunk file
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                        chunk_path = temp_file.name
                    
                    with wave.open(chunk_path, 'wb') as chunk_file:
                        chunk_file.setparams(params)
                        chunk_file.writeframes(frames)
                    
                    chunk_files.append(chunk_path)
                    chunk_num += 1
                    
                logging.info(f"Created {len(chunk_files)} chunks using wave library")
                
        except Exception as e:
            logging.error(f"Error in wave-based splitting: {e}")
            return []
            
        return chunk_files

    def _combine_chunk_results(self, chunk_results: List[AzurePronunciationReport]) -> AzurePronunciationReport:
        """Combine multiple chunk results into a single comprehensive report"""
        try:
            # Use the first chunk as the base structure
            base_result = chunk_results[0]
            
            # Combine display text from all chunks
            combined_text = " ".join([chunk.display_text for chunk in chunk_results])
            
            # Calculate combined duration
            total_duration = sum([chunk.duration for chunk in chunk_results])
            
            # Combine all NBest results
            combined_nbest = []
            all_words = []
            
            # Collect all words and scores from all chunks
            all_fluency_scores = []
            all_accuracy_scores = []
            all_prosody_scores = []
            all_completeness_scores = []
            all_pron_scores = []
            
            for chunk in chunk_results:
                if chunk.primary_result:
                    # Collect words from this chunk
                    all_words.extend(chunk.primary_result.words)
                    
                    # Collect scores for averaging
                    assessment = chunk.primary_result.assessment
                    all_fluency_scores.append(assessment.fluency_score)
                    all_accuracy_scores.append(assessment.accuracy_score)
                    all_completeness_scores.append(assessment.completeness_score)
                    all_pron_scores.append(assessment.pron_score)
                    
                    if assessment.prosody_score is not None:
                        all_prosody_scores.append(assessment.prosody_score)
            
            # Calculate average scores
            avg_fluency = sum(all_fluency_scores) / len(all_fluency_scores)
            avg_accuracy = sum(all_accuracy_scores) / len(all_accuracy_scores)
            avg_completeness = sum(all_completeness_scores) / len(all_completeness_scores)
            avg_pron = sum(all_pron_scores) / len(all_pron_scores)
            avg_prosody = sum(all_prosody_scores) / len(all_prosody_scores) if all_prosody_scores else None
            
            # Create combined NBest result
            combined_assessment = {
                "AccuracyScore": avg_accuracy,
                "FluencyScore": avg_fluency,
                "CompletenessScore": avg_completeness,
                "PronScore": avg_pron
            }
            
            if avg_prosody is not None:
                combined_assessment["ProsodyScore"] = avg_prosody
            
            combined_nbest_item = {
                "Confidence": base_result.primary_result.confidence, #type: ignore
                "Display": combined_text,
                "PronunciationAssessment": combined_assessment,
                "Words": [word.model_dump(by_alias=True) for word in all_words]
            }
            
            # Create the final combined result
            combined_result_dict = {
                "Id": base_result.id,
                "RecognitionStatus": "Success",
                "DisplayText": combined_text,
                "Offset": base_result.offset,
                "Duration": total_duration,
                "NBest": [combined_nbest_item]
            }
            
            # Add SNR if available
            if base_result.snr is not None:
                combined_result_dict["SNR"] = base_result.snr
            
            # Validate and return the combined result
            combined_json = json.dumps(combined_result_dict)
            combined_report = AzurePronunciationReport.model_validate_json(combined_json)
            
            logging.info(f"Successfully combined chunks: {len(all_words)} total words, "
                        f"avg scores - Fluency: {avg_fluency:.1f}, Accuracy: {avg_accuracy:.1f}")
            
            return combined_report
            
        except Exception as e:
            logging.error(f"Error combining chunk results: {e}")
            # Fallback: return the first chunk result
            return chunk_results[0]

    def _validate_result_structure(self, result_data: dict) -> bool:
        """Validate that the result has the required structure"""
        try:
            if result_data.get("RecognitionStatus") != "Success":
                logging.error(f"Recognition status: {result_data.get('RecognitionStatus')}")
                return False
                
            if "NBest" not in result_data or not result_data["NBest"]:
                logging.error("No NBest data found")
                return False
                
            nbest = result_data["NBest"][0]
            if "Words" not in nbest or not nbest.get("Words"):
                logging.error("No Words data found in NBest")
                return False
                
            if "PronunciationAssessment" not in nbest:
                logging.error("No PronunciationAssessment found in NBest")
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"Error validating result structure: {e}")
            return False

    def _log_recognition_failure(self, result):
        """Log detailed information about recognition failure"""
        if result.reason == speechsdk.ResultReason.NoMatch:
            logging.error("No speech could be recognized")
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            logging.error(f"Speech recognition canceled: {cancellation_details.reason}")
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                logging.error(f"Error details: {cancellation_details.error_details}")

    def _cleanup_chunk_files(self, chunk_files: List[str]):
        """Clean up temporary chunk files"""
        for chunk_file in chunk_files:
            try:
                os.unlink(chunk_file)
            except Exception as e:
                logging.warning(f"Failed to delete chunk file {chunk_file}: {e}")

    def test_basic_recognition(self, audio_filepath: str) -> str: #type: ignore
        """Test basic speech recognition without pronunciation assessment"""
        if not self.speech_config:
            return "Speech config not initialized"

        try:
            audio_config = speechsdk.audio.AudioConfig(filename=audio_filepath)
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )

            logging.info("Testing basic recognition...")
            result = speech_recognizer.recognize_once()
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                logging.info(f"SUCCESS: Recognized text: {result.text}")
                return f"SUCCESS: {result.text}"
            elif result.reason == speechsdk.ResultReason.NoMatch:
                return "ERROR: No speech recognized"
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                error_msg = f"ERROR: {cancellation_details.error_details}" if cancellation_details.reason == speechsdk.CancellationReason.Error else "ERROR: Recognition canceled"
                return error_msg
                
        except Exception as e:
            logging.error(f"Error in basic recognition test: {e}", exc_info=True)
            return f"EXCEPTION: {str(e)}"