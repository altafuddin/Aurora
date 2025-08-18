# In: logic/session_models.py

import time  # For session timing calculations
import logging
from dataclasses import dataclass, field
from typing import List, Optional
import asyncio
import azure.cognitiveservices.speech as speechsdk # type: ignore
from .chat_models import ChatTurn
import threading

# --- StreamingState Dataclass ---
@dataclass
class StreamingState:
    """
    Holds all the transient components and flags needed for a single
    real-time streaming session with Azure.
    """
    # Azure SDK components that need careful lifecycle management
    recognizer: Optional[speechsdk.SpeechRecognizer] = None
    push_stream: Optional[speechsdk.audio.PushAudioInputStream] = None

    # Audio processing
    audio_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    audio_buffer: List[float] = field(default_factory=list)
        
    # State flags and data buffers
    webrtc_id: Optional[str] = None
    is_recording: bool = False
    session_transcript_fragments: List[dict] = field(default_factory=list)
    current_utterance_buffer: str = ""  # Buffer for in-progress speech
    final_pronunciation_json: Optional[dict] = None
    pronunciation_reports_cache: List[dict] = field(default_factory=list)  # For multi-utterance sessions
    current_pronunciation_report: Optional[dict] = None

    # Session management
    is_active: bool = True
    recording_start_time: Optional[float] = None
    max_recording_seconds: int = 600  # 10 minutes
    retry_count: int = 0
    max_retries: int = 3
    last_error: Optional[str] = None
    audio_chunks_processed: int = 0  # Track processing load

    # Consumer task management
    consumer_task: Optional[asyncio.Task] = None
    
    def reset_for_new_utterance(self):
        """Reset utterance-specific data while preserving session state"""
        self.session_transcript_fragments = []
        self.current_utterance_buffer = ""
        self.pronunciation_reports_cache = []
        self.current_pronunciation_report = None
        self.audio_buffer = []
        self.retry_count = 0

# --- StreamingSessionState Dataclass ---
@dataclass
class StreamingSessionState:
    """
    The main, comprehensive state object for a single user session in the
    Natural Chat mode. It contains both the long-term chat history and the
    transient state for the current streaming operation.
    """
    # Existing chat functionality
    chat_history: List[ChatTurn] = field(default_factory=list)
    streaming: StreamingState = field(default_factory=StreamingState)
    
    def cleanup_streaming_resources(self):
        """
        Safely stops and cleans up Azure SDK components to prevent resource leaks.
        This method should be called when a session ends or an error occurs.
        """
        logging.info("Cleaning up streaming resources...")
        if self.streaming.recognizer:
            try:
                # Stop recognition and disconnect callbacks to prevent memory leaks
                self.streaming.recognizer.stop_continuous_recognition()
                cleanup_timeout = threading.Timer(5.0, lambda: logging.warning("Recognizer cleanup timeout"))
                cleanup_timeout.start()
                try:
                    self.streaming.recognizer.recognized.disconnect_all()
                    self.streaming.recognizer.recognizing.disconnect_all() 
                    self.streaming.recognizer.canceled.disconnect_all()
                    self.streaming.recognizer.session_stopped.disconnect_all()
                    cleanup_timeout.cancel()
                finally:
                    cleanup_timeout.cancel()
                logging.info("Azure recognizer stopped and disconnected.")
            except Exception as e:
                logging.error(f"Error stopping recognizer: {e}", exc_info=True)
        
        if self.streaming.push_stream:
            try:
                self.streaming.push_stream.close()
                logging.info("Azure push stream closed.")
            except Exception as e:
                logging.error(f"Error closing push stream: {e}", exc_info=True)
        
        # Reset the streaming state object
        # self.streaming = StreamingState()
        logging.info(f"Session reset complete. Chat history preserved: {len(self.chat_history)} turns")

    def is_session_healthy(self) -> bool:
        """
        Validates streaming session health for proactive error handling.
        Returns False if session needs reset/cleanup.
        """
        # Check for resource exhaustion
        if self.streaming.audio_chunks_processed > 10000:  # Reasonable limit
            logging.warning("Session processed too many audio chunks, may need reset")
            return False
            
        # Check for stuck connections
        if (self.streaming.recording_start_time and 
            time.time() - self.streaming.recording_start_time > self.streaming.max_recording_seconds):
            logging.warning("Session exceeded maximum duration")
            return False
            
        return True