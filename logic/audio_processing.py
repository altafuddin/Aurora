# In: logic/audio_processing.py
from fastrtc import StreamHandler # type: ignore
import logging
import numpy as np
from .session_manager import session_manager


# Add to audio_processing.py before queuing
def has_speech(audio_data, threshold=0.01):
    return np.max(np.abs(audio_data)) > threshold

class AuroraStreamHandler(StreamHandler):
    """
    A stateless handler that routes incoming audio to the correct session's queue
    by looking up the active session in the global session manager.
    """
    def receive(self, frame):
        sr, audio_arr = frame
        
        # This is the lookup mechanism from the working POC.
        active_sessions = session_manager.get_active_recording_sessions()
        
        if active_sessions:
            # Use the first active session as fallback
            session_hash = active_sessions[0]
            session_state = session_manager.get_session(session_hash)
            
            if session_state:
                # Audio processing
                # Resample audio
                audio_data = audio_arr.flatten()
                if sr != 16000:
                    # FIXED: Proper resampling instead of broken integer division
                    target_length = int(len(audio_data) * 16000 / sr)
                    if target_length > 0:
                        indices = np.linspace(0, len(audio_data) - 1, target_length)
                        audio_data = np.interp(indices, np.arange(len(audio_data)), audio_data)
                        logging.debug(f"🔄 Resampled from {sr}Hz to 16kHz: {len(audio_arr.flatten())} → {len(audio_data)} samples")
                    else:
                        logging.warning(f"⚠️ Invalid resampling: {sr}Hz → 16kHz resulted in 0 samples")
                        return
                
                # Enhanced queue management with pressure relief
                try:
                    queue_size = session_state.streaming.audio_queue.qsize()

                    # Match the service's queue pressure logic
                    if queue_size > 45:  # Near maximum - drop frame
                        logging.error("Queue near full - dropping frame to prevent backup")
                        return
                    elif queue_size > 30:   # High pressure - warn but continue
                        if queue_size % 5 == 0:   # Throttled logging
                            logging.warning(f"⚠️ Audio queue high pressure: {queue_size} items")
                    elif queue_size > 15:  # Moderate pressure - log occasionally
                        if queue_size % 10 == 0:   # less frequent logging
                            # logging.warning(f"⚠️ Audio queue backing up: {queue_size} items")
                            pass

                    if has_speech(audio_data):
                        session_state.streaming.audio_queue.put_nowait(audio_data.tolist())

                    logging.debug(f"📥 Queued {len(audio_data)} samples from {sr}Hz (queue: {queue_size + 1})")
                except Exception as e:
                    logging.error(f"❌ DROPPED AUDIO: {e}")  # Queue full, drop frame

    def emit(self):
        return None
    
    def copy(self):
        return AuroraStreamHandler()
