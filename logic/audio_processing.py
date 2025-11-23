# In: logic/audio_processing.py
from fastrtc import StreamHandler
import logging
import numpy as np
from scipy import signal
from logic.session_manager import session_manager


# Add to audio_processing.py before queuing
def has_speech(audio_data, threshold=0.01):
    """Check if audio frame contains speech (energy above threshold)"""
    return np.max(np.abs(audio_data)) > threshold

class AuroraStreamHandler(StreamHandler):
    """
    Stateless handler that routes incoming audio to the correct session's queue
    by looking up the active session in the global session manager.
    """
    def __init__(self):
        super().__init__()
        self.chunk_counter = 0
    
    def receive(self, frame):
        sr, audio_arr = frame
        
        # 1. Lookup active session
        active_sessions = session_manager.get_active_recording_sessions()
        
        if active_sessions:
            # Use the first active session as fallback
            session_hash = active_sessions[0]
            session_state = session_manager.get_session(session_hash)
            
            if session_state:
                # 2. Check queue pressure first
                try:
                    queue_size = session_state.streaming.audio_queue.qsize()

                    if queue_size > 45:  # Critical pressure(assumed by chatbot)
                        logging.error(f"Queue overflow ({queue_size}) - dropping frame")
                        return
                
                except Exception as e:
                    logging.error(f"Error checking queue size: {e}")
                    return
                
                # 3. Flatten audio
                audio_data = audio_arr.flatten()

                # 4. Check for speech before resampling
                if not has_speech(audio_data):
                    logging.debug("Silence detected - skipping frame")
                    return

                # 5. Resample to 16kHz if needed
                if sr != 16000:
                    # Proper resampling instead of broken integer division
                    target_length = int(len(audio_data) * 16000 / sr)

                    if target_length > 0:
                        # Using scipy.signal.resample for faster, better quality instead of np.interp
                        audio_data = signal.resample(audio_data, target_length)
                        logging.debug(f"Resampled from {sr}Hz to 16kHz: {len(audio_arr.flatten())} → {len(audio_data)} samples")
                    else:
                        logging.warning(f"Invalid resampling: {sr}Hz → 16kHz resulted in 0 samples")
                        return
                    
                # 6. Enqueue processed audio
                try:
                    session_state.streaming.audio_queue.put_nowait(audio_data.tolist())
                    self.chunk_counter += 1
                    
                    # Log every 10th chunk with queue size
                    if self.chunk_counter % 10 == 0:
                        logging.debug(f"METRICS: audio_chunks_received={self.chunk_counter} queue_size={queue_size + 1} (context: audio_processing)")
                    
                    # logging.debug(f"Queued {len(audio_data)} samples from {sr}Hz (queue: {session_state.streaming.audio_queue.qsize()})")

                    if queue_size > 30 and queue_size % 5 == 0:
                        logging.warning(f"Audio queue high pressure: {queue_size} items")

                    logging.debug(f"Queued {len(audio_data)} samples (queue: {queue_size + 1})")

                except Exception as e:
                    logging.error(f"DROPPED AUDIO: {e}")  # Queue full, drop frame
                
               
    def emit(self):
        return None
    
    def copy(self):
        new_handler = AuroraStreamHandler()
        new_handler.chunk_counter = 0
        return new_handler
