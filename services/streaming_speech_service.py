# In: services/streaming_speech_service.py

import logging
import asyncio
import threading
import numpy as np
import time
import json
from typing import List, Optional, Tuple
import azure.cognitiveservices.speech as speechsdk # type: ignore
from logic.session_models import StreamingSessionState
from logic.audio_models import AzurePronunciationReport
from pydantic import ValidationError
from config import AZURE_SPEECH_KEY, AZURE_SPEECH_REGION


class StreamingAudioService:
    """
    Enhanced streaming audio service that combines POC real-time processing
    with production-ready Azure configuration and error handling.
    
    Integrates:
    - POC's real-time audio queue processing
    - Enhanced Azure Speech SDK configuration  
    - Smart fragment consolidation logic
    - Production-ready resource management
    """
    
    def __init__(self):
        """Initialize Azure Speech Service with enhanced configuration"""
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
            
            # Enhanced configuration from your service
            self.speech_config.request_word_level_timestamps()
            self.speech_config.output_format = speechsdk.OutputFormat.Detailed
            self.speech_config.set_profanity(speechsdk.ProfanityOption.Raw)
            # After creating speech_config, add silence tolerance:
            self.speech_config.set_property(speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, "3000")
            self.speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "5000")
            # self.speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "3000"
            
            logging.info("Enhanced Azure Speech Service initialized successfully")
            
        except Exception as e:
            logging.error(f"Error initializing Azure Speech Service: {e}", exc_info=True)
            self.speech_config = None

    def setup_azure_recognizer(self, session_state: StreamingSessionState) -> bool:
        """
        Setup Azure recognizer with enhanced configuration and event handlers
        Combines POC's event handling with your service's robust configuration
        """
        try:
            if not self.speech_config:
                logging.error("Speech config not initialized, cannot start session")
                session_state.streaming.last_error = "Azure configuration invalid"
                return False
                
            # 1. Create push stream and recognizer (from your service)
            push_stream = speechsdk.audio.PushAudioInputStream()
            audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
            
            # 2. Configure pronunciation assessment (enhanced from your service)
            pronunciation_config = speechsdk.PronunciationAssessmentConfig(
                reference_text="",  # Empty for conversational speech
                grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
                granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
                enable_miscue=False
            )
            pronunciation_config.enable_prosody_assessment()
            pronunciation_config.apply_to(recognizer)
            
            # 3. Setup enhanced event handlers (combines POC + your service logic)
            def on_recognized(evt: speechsdk.SpeechRecognitionEventArgs):
                """Handle finalized utterances with enhanced processing"""
                if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                    utterance = evt.result.text.strip()
                    fragment_count = len(session_state.streaming.session_transcript_fragments)
                    logging.info(f"API: Azure.fragment_received | status=success | fragment_num={fragment_count + 1}")
                    logging.info(f"[{session_state.streaming.webrtc_id}] RECOGNIZED: '{utterance}'")
                    
                    if utterance:
                        # Extract and store JSON result (from your service approach)
                        json_result = evt.result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
                        if json_result:
                            try:
                                pronunciation_data = json.loads(json_result)
                                session_state.streaming.session_transcript_fragments.append(pronunciation_data)
                                logging.info(f"[{session_state.streaming.webrtc_id}] Pronunciation data extracted and stored")
                            except json.JSONDecodeError as e:
                                logging.error(f"Failed to parse JSON result: {e}")
                        
                        # Update current utterance buffer for real-time display
                        session_state.streaming.current_utterance_buffer = utterance
                        
                elif evt.result.reason == speechsdk.ResultReason.Canceled:
                    # Enhanced error handling from your service
                    cancellation = evt.result.cancellation_details
                    error_msg = f"Recognition Canceled: {cancellation.reason} - {cancellation.error_details}"
                    logging.error(f"[{session_state.streaming.webrtc_id}] {error_msg}")
                    session_state.streaming.last_error = cancellation.error_details
                    session_state.streaming.is_recording = False
                    
                elif evt.result.reason == speechsdk.ResultReason.NoMatch:
                    logging.warning(f"[{session_state.streaming.webrtc_id}] No speech could be recognized")

            def on_recognizing(evt: speechsdk.SpeechRecognitionEventArgs):
                """Handle partial recognition updates (POC functionality)"""
                session_state.streaming.current_utterance_buffer = evt.result.text
                logging.debug(f"[{session_state.streaming.webrtc_id}] Partial: '{evt.result.text}'")

            # Connect event handlers
            recognizer.recognized.connect(on_recognized)
            recognizer.recognizing.connect(on_recognizing)
            
            # Store components in session state
            session_state.streaming.push_stream = push_stream
            session_state.streaming.recognizer = recognizer

            logging.info(f"[{session_state.streaming.webrtc_id}] Azure recognizer setup successful")
            return True
            
        except Exception as e:
            logging.error(f"[{session_state.streaming.webrtc_id}] Failed to setup Azure recognizer: {e}")
            session_state.streaming.last_error = str(e)
            return False

    def start_recording(self, session_state: StreamingSessionState) -> Tuple[bool, str]:
        """
        Start recording with enhanced retry logic and resource management
        """
        start_time = time.time()
        session_state.streaming.retry_count = 0
        
        for attempt in range(session_state.streaming.max_retries + 1):
            try:
                # Setup recognizer with enhanced configuration
                if self.setup_azure_recognizer(session_state):
                    # Start Azure recognition
                    api_start = time.time()
                    logging.info(f"API: Azure.start_continuous_recognition | status=starting")
                    session_state.streaming.recognizer.start_continuous_recognition() # type: ignore
                    api_duration = time.time() - api_start
                    logging.info(f"API: Azure.start_continuous_recognition | status=success | duration={api_duration:.2f}s")
                    
                    logging.info(f"STATE: is_recording changed from False to True")
                    session_state.streaming.is_recording = True
                    logging.info(f"STATE: is_active changed from False to True")
                    session_state.streaming.is_active = True
                    # Initialize session timing and counters (from your service)
                    session_state.streaming.recording_start_time = time.time()
                    session_state.streaming.audio_chunks_processed = 0
                    
                    # Reset session data for new utterance
                    session_state.streaming.session_transcript_fragments = []
                    session_state.streaming.current_utterance_buffer = ""
                    session_state.streaming.final_pronunciation_json = None
                    session_state.streaming.audio_buffer = []
                    session_state.streaming.last_error = None
                    session_state.streaming.audio_queue = asyncio.Queue() 
                    
                    # Start enhanced audio consumer thread
                    self._start_consumer_thread(session_state)

                    elapsed = time.time() - start_time
                    logging.info(f"[{session_state.streaming.webrtc_id}] Recording started (attempt {attempt + 1})")
                    logging.info(f"TIMING: start_recording completed in {elapsed:.2f}s")
                    return True, "Recording started..."
                
            except Exception as e:
                session_state.streaming.retry_count += 1
                error_msg = f"Recording start attempt {attempt + 1} failed: {e}"
                logging.warning(f"[{session_state.streaming.webrtc_id}] {error_msg}")
                session_state.streaming.last_error = str(e)
                
                if attempt < session_state.streaming.max_retries:
                    time.sleep(1)  # Brief delay before retry
                    continue
        
        # All retries failed
        final_error = f"Failed to start recording after {session_state.streaming.max_retries + 1} attempts"
        if session_state.streaming.last_error:
            final_error += f": {session_state.streaming.last_error}"
            
        return False, final_error

    def stop_recording(self, session_state: StreamingSessionState) -> Tuple[bool, str, Optional[AzurePronunciationReport]]:
        """
        Stop recording and consolidate results using enhanced fragment processing
        """
        start_time = time.time()
        try:
            if not session_state.streaming.is_recording:
                logging.warning(f"[{session_state.streaming.webrtc_id}] Stop called but not recording")
                return False, "Not currently recording", None
                
            # Flush remaining audio buffer (POC logic)
            self._flush_audio_buffer(session_state)
            
            # Give Azure a moment to process final audio
            time.sleep(0.5)
            logging.info("[stop_recording ] waiting 500ms for final processing")
            
            # Stop Azure recognition and cleanup (your service's approach)
            if session_state.streaming.recognizer:
                api_start = time.time()
                logging.info(f"API: Azure.stop_continuous_recognition | status=starting")
                session_state.streaming.recognizer.stop_continuous_recognition()
                api_duration = time.time() - api_start
                logging.info(f"API: Azure.stop_continuous_recognition | status=success | duration={api_duration:.2f}s")
            
            logging.info(f"STATE: is_recording changed from True to False")
            session_state.streaming.is_recording = False
            
            # Enhanced fragment consolidation from your service
            pronunciation_report = self._consolidate_results(session_state)
            
            if pronunciation_report:
                # Build transcript from validated pronunciation report
                final_transcript = pronunciation_report.display_text
                logging.info(f"[{session_state.streaming.webrtc_id}] Session finalized: '{final_transcript}'")
                elapsed = time.time() - start_time
                logging.info(f"TIMING: stop_recording completed in {elapsed:.2f}s")
                return True, final_transcript, pronunciation_report
            else:
                # Fallback to partial results if available
                partial_transcript = session_state.streaming.current_utterance_buffer or "(No speech detected)"
                logging.warning(f"[{session_state.streaming.webrtc_id}] No validated results, using partial: '{partial_transcript}'")
                elapsed = time.time() - start_time
                logging.info(f"TIMING: stop_recording completed in {elapsed:.2f}s")
                return False, partial_transcript, None
                
        except Exception as e:
            error_msg = f"Failed to stop recording: {e}"
            logging.error(f"[{session_state.streaming.webrtc_id}] {error_msg}")
            session_state.streaming.last_error = str(e)
            return False, error_msg, None
        finally:
            # Always cleanup resources
            session_state.cleanup_streaming_resources()
            # ADD: Signal that session can be removed
            # logging.info(f"STATE: is_active changed from True to False")
            session_state.streaming.is_active = False

    def _consolidate_results(self, session_state: StreamingSessionState) -> Optional[AzurePronunciationReport]:
        """
        Smart consolidation of recognition fragments using your service's logic
        """
        start_time = time.time()
        fragments = session_state.streaming.session_transcript_fragments
        if not fragments:
            logging.warning(f"[{session_state.streaming.webrtc_id}] No speech fragments to consolidate")
            return None

        try:
            # Build complete transcript from all fragments
            complete_utterance_parts = []
            all_words = []
            total_duration = 0
            
            for fragment in fragments:
                if "DisplayText" in fragment:
                    complete_utterance_parts.append(fragment["DisplayText"].strip())
                
                # Accumulate duration
                total_duration += fragment.get("Duration", 0)
                
                # Collect ALL words with their pronunciation data
                if "NBest" in fragment and fragment["NBest"]:
                    fragment_words = fragment["NBest"][0].get("Words", [])
                    all_words.extend(fragment_words)
            
            # Build complete transcript
            complete_transcript = " ".join(complete_utterance_parts)
            
            # Create consolidated report using first fragment as template
            final_fragment = fragments[0].copy()
            final_fragment["DisplayText"] = complete_transcript
            final_fragment["Duration"] = total_duration
            
            # Update NBest with consolidated data
            if "NBest" in final_fragment and final_fragment["NBest"]:
                final_fragment["NBest"][0]["Words"] = all_words
                final_fragment["NBest"][0]["Lexical"] = complete_transcript
                final_fragment["NBest"][0]["Display"] = complete_transcript
                final_fragment["NBest"][0]["ITN"] = complete_transcript
                final_fragment["NBest"][0]["MaskedITN"] = complete_transcript
                
                # Keep the original PronunciationAssessment from first fragment
                # Individual word/phoneme scores are preserved in the Words array
            
            # Validate with Pydantic
            final_json_string = json.dumps(final_fragment)
            validated_report = AzurePronunciationReport.model_validate_json(final_json_string)

            elapsed = time.time() - start_time
            logging.info(f"[{session_state.streaming.webrtc_id}] Successfully consolidated {len(fragments)} fragments with {len(all_words)} total words")
            logging.info(f"METRICS: fragments_consolidated={len(fragments)} total_words={len(all_words)} (context: consolidation)")
            logging.info(f"TIMING: _consolidate_results completed in {elapsed:.2f}s")
            return validated_report

        except ValidationError as e:
            logging.error(f"[{session_state.streaming.webrtc_id}] Pydantic validation failed: {e}")
            return None
        except Exception as e:
            logging.error(f"[{session_state.streaming.webrtc_id}] Unexpected error during consolidation: {e}")
            return None

    def _flush_audio_buffer(self, session_state: StreamingSessionState):
        """Flush any remaining audio in buffer (POC logic)"""
        if (session_state.streaming.audio_buffer and 
            len(session_state.streaming.audio_buffer) > 0 and 
            session_state.streaming.push_stream):
            
            chunk = np.array(session_state.streaming.audio_buffer)
            pcm = chunk.astype(np.int16).tobytes()
            session_state.streaming.push_stream.write(pcm)
            session_state.streaming.audio_buffer = []
            logging.debug(f"[{session_state.streaming.webrtc_id}] Flushed {len(chunk)} remaining samples")

    def _start_consumer_thread(self, session_state: StreamingSessionState):
        """Start enhanced audio consumer thread with resource management"""
        def consumer_target():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._consume_audio_loop(session_state))
            except Exception as e:
                logging.error(f"[{session_state.streaming.webrtc_id}] Consumer thread error: {e}")
            finally:
                loop.close()
        
        thread = threading.Thread(target=consumer_target, daemon=True)
        thread.start()
        logging.info(f"🧵 [{session_state.streaming.webrtc_id}] Enhanced consumer thread started")

    async def _consume_audio_loop(self, session_state: StreamingSessionState):
        """
        OPTIMIZED audio consumer with batching and async processing
        
        KEY CHANGES:
        1. Increased chunk size from 30ms → 200ms (reduces API overhead)
        2. Added intelligent batching to process multiple chunks together
        3. Implemented queue pressure relief to prevent backing up
        4. Added performance monitoring and adaptive processing
        """
        start_time = time.time()
        logging.info(f"[{session_state.streaming.webrtc_id}] Starting OPTIMIZED audio consumer")
        
        # CHANGE 1: Larger chunk size for better Azure performance
        target_samples = int(16000 * 0.5)  # 200ms chunks - optimal for Azure
        
        # CHANGE 2: Add batching variables
        batch_buffer = []
        max_batch_size = 8  # Process up to 5 chunks at once
        last_process_time = time.time()
        batch_timeout = 0.1  # 100ms max wait for batching
        
        # CHANGE 3: Performance monitoring
        queue_warnings = 0
        performance_stats = {
            'chunks_processed': 0,
            'batches_sent': 0,
            'queue_overflows': 0,
            'avg_queue_size': 0.0
        }
        
        try:
            logging.info(f"[{session_state.streaming.webrtc_id}] Consumer starting: recording={session_state.streaming.is_recording}, active={session_state.streaming.is_active}")
            
            while session_state.streaming.is_active and session_state.streaming.is_recording:
                try:
                    # CHANGE 4: Enhanced timeout and resource checks
                    current_time = time.time()
                    if (session_state.streaming.recording_start_time and 
                        current_time - session_state.streaming.recording_start_time > session_state.streaming.max_recording_seconds):
                        logging.warning(f"[{session_state.streaming.webrtc_id}] Recording time limit reached")
                        session_state.streaming.is_recording = False
                        break
                    
                    # CHANGE 5: Queue pressure monitoring and relief
                    queue_size = session_state.streaming.audio_queue.qsize()
                    performance_stats['avg_queue_size'] = (performance_stats['avg_queue_size'] + queue_size) / 2
                    
                    # CRITICAL: Queue pressure relief
                    if queue_size > 20:  # Queue backing up critically
                        # logging.warning(f"CRITICAL queue backup: {queue_size} items - applying pressure relief")
                        performance_stats['queue_overflows'] += 1
                        
                        # Emergency drain: process multiple items quickly
                        emergency_batch = []
                        drain_count = min(queue_size - 10, 15)  # Drain down to 10 items
                        
                        for _ in range(drain_count):
                            try:
                                emergency_audio = session_state.streaming.audio_queue.get_nowait()
                                emergency_batch.extend(emergency_audio)
                                session_state.streaming.audio_queue.task_done()
                            except asyncio.QueueEmpty:
                                break
                        
                        # Process emergency batch immediately
                        if emergency_batch:
                            session_state.streaming.audio_buffer.extend(emergency_batch)
                            await self._process_audio_buffer_optimized(session_state, target_samples, force_flush=True)
                            # logging.info(f"Emergency processed {len(emergency_batch)} samples from {drain_count} chunks")
                        continue
                    
                    elif queue_size > 10:  # Moderate backup - warn but continue
                        # if queue_warnings % 20 == 0:  # Throttled warning
                            # logging.warning(f"Audio queue backing up: {queue_size} items (warning #{queue_warnings + 1})")
                        queue_warnings += 1
                    
                    # CHANGE 6: Adaptive timeout based on queue pressure
                    # If queue is building up, process faster
                    if queue_size > 5:
                        timeout = 0.05  # 50ms - faster processing
                    elif queue_size > 2:
                        timeout = 0.1   # 100ms - normal processing  
                    else:
                        timeout = 0.5   # 500ms - relaxed when queue is empty
                    
                    # Wait for audio data with adaptive timeout
                    try:
                        audio_data = await asyncio.wait_for(
                            session_state.streaming.audio_queue.get(), 
                            timeout=timeout
                        )
                        
                        # CHANGE 7: Batch processing logic
                        batch_buffer.append(audio_data)
                        session_state.streaming.audio_queue.task_done()
                        
                        # Process batch when:
                        # - Batch is full, OR
                        # - Queue is backing up (>5 items), OR  
                        # - Timeout reached (100ms since last process)
                        should_process = (
                            len(batch_buffer) >= max_batch_size or
                            queue_size > 5 or
                            (current_time - last_process_time) > batch_timeout
                        )
                        
                        if should_process and session_state.streaming.is_recording:
                            # CHANGE 8: Process entire batch at once
                            batch_audio = []
                            for audio_chunk in batch_buffer:
                                batch_audio.extend(audio_chunk)
                            
                            session_state.streaming.audio_buffer.extend(batch_audio)
                            await self._process_audio_buffer_optimized(session_state, target_samples)
                            
                            # Update stats
                            performance_stats['chunks_processed'] += len(batch_buffer)
                            performance_stats['batches_sent'] += 1
                            
                            # Reset batch
                            batch_buffer.clear()
                            last_process_time = current_time
                            
                            # Log performance periodically
                            if performance_stats['batches_sent'] % 50 == 0:
                                avg_queue = performance_stats['avg_queue_size']
                                logging.info(f"Performance: {performance_stats['batches_sent']} batches, "
                                        f"avg queue: {avg_queue:.1f}, overflows: {performance_stats['queue_overflows']}")
                    
                    except asyncio.TimeoutError:
                        # CHANGE 9: Process any pending batch on timeout
                        if batch_buffer and session_state.streaming.is_recording:
                            batch_audio = []
                            for audio_chunk in batch_buffer:
                                batch_audio.extend(audio_chunk)
                            
                            session_state.streaming.audio_buffer.extend(batch_audio)
                            await self._process_audio_buffer_optimized(session_state, target_samples)
                            
                            batch_buffer.clear()
                            last_process_time = current_time
                            performance_stats['batches_sent'] += 1
                        continue
                        
                except Exception as e:
                    logging.error(f"[{session_state.streaming.webrtc_id}] Error in audio consumer: {e}")
                    break
                    
        except Exception as e:
            logging.error(f"[{session_state.streaming.webrtc_id}] Fatal error in consumer loop: {e}")
        finally:
            # Process any final batch
            if batch_buffer:
                try:
                    final_audio = []
                    for audio_chunk in batch_buffer:
                        final_audio.extend(audio_chunk)
                    session_state.streaming.audio_buffer.extend(final_audio)
                    await self._process_audio_buffer_optimized(session_state, target_samples, force_flush=True)
                except Exception as e:
                    logging.error(f"Error processing final batch: {e}")

            elapsed = time.time() - start_time
            logging.info(f"[{session_state.streaming.webrtc_id}] OPTIMIZED audio consumer stopped")
            logging.info(f"Final stats: {performance_stats}")
            logging.info(f"TIMING: _consume_audio_loop completed in {elapsed:.2f}s")

    # CHANGE 10: Add new optimized buffer processing method
    async def _process_audio_buffer_optimized(self, session_state: StreamingSessionState, target_samples: int, force_flush: bool = False):
        """
        Optimized audio buffer processing with intelligent chunking
        
        WHY THIS HELPS:
        - Processes larger chunks (200ms vs 30ms)
        - Uses async processing to prevent blocking
        - Implements smart buffer management
        """
        if not session_state.streaming.push_stream:
            return
            
        buffer_size = len(session_state.streaming.audio_buffer)
        
        # Process if we have enough samples OR force flush
        if buffer_size >= target_samples or (force_flush and buffer_size > 0):
            try:
                if force_flush:
                    # Flush everything
                    chunk = np.array(session_state.streaming.audio_buffer)
                    session_state.streaming.audio_buffer = []
                else:
                    # Process optimal chunk size
                    chunk = np.array(session_state.streaming.audio_buffer[:target_samples])
                    session_state.streaming.audio_buffer = session_state.streaming.audio_buffer[target_samples:]
                
                # CHANGE 11: Async processing to prevent blocking
                pcm = chunk.astype(np.int16).tobytes()
                
                # Use asyncio to prevent blocking the consumer thread
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,  # Use default thread pool
                    session_state.streaming.push_stream.write,
                    pcm
                )
                
                # Track processing for resource management
                session_state.streaming.audio_chunks_processed += 1

                logging.debug(f"Processed {len(chunk)} samples "
                            f"(chunk #{session_state.streaming.audio_chunks_processed})")
                
            except Exception as e:
                logging.error(f"Error processing audio buffer: {e}")

    def queue_audio_data(self, audio_data: List[float], session_state: StreamingSessionState):
        """
        Queue audio data for processing with enhanced validation
        Used by the FastRTC handler to feed audio into the streaming pipeline
        """
        if not session_state.streaming.is_recording:
            return  # Silently drop audio if not recording
            
        try:
            # Monitor queue size - if it's backing up, we're losing audio
            queue_size = session_state.streaming.audio_queue.qsize()
            # CHANGE 13: Implement smart dropping to prevent complete backup
            if queue_size > 50:  # Queue at maximum
                # Drop this frame but log it
                logging.error("Queue full - dropping frame to prevent backup")
                return
            elif queue_size > 30:
                # Warn but still accept
                logging.warning(f"Queue high: {queue_size} items")
            session_state.streaming.audio_queue.put_nowait(audio_data)
            logging.debug(f"Queued {len(audio_data)} samples (queue: {queue_size + 1})")
        except asyncio.QueueFull:
            logging.error(f"Queue full, dropping frame")
        except Exception as e:
            logging.error(f"[{session_state.streaming.webrtc_id}] Error queuing audio: {e}")