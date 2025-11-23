# In: logic/session_manager.py
import threading
import time
import logging
from typing import Dict, List
from .session_models import StreamingSessionState

class SessionManager:
    """A thread-safe, global registry for active user streaming sessions."""
    def __init__(self):
        self._sessions: Dict[str, StreamingSessionState] = {}
        self._lock = threading.Lock()

    def get_or_create_session(self, session_hash: str) -> StreamingSessionState:
        with self._lock:
            if session_hash not in self._sessions:
                logging.info(f"Creating NEW session for {session_hash}")
                self._sessions[session_hash] = StreamingSessionState()
                logging.info(f"METRICS: active_sessions={len(self._sessions)} (context: session created)")
            else:
                logging.info(f"Reusing session for {session_hash} with {len(self._sessions[session_hash].chat_history)} turns")
            return self._sessions[session_hash]
    
    def create_session(self, session_hash: str) -> StreamingSessionState:
        with self._lock:
            if session_hash not in self._sessions:
                logging.warning(f"Creating NEW session for {session_hash} - chat history will be lost!")
                self._sessions[session_hash] = StreamingSessionState()
            else:
                logging.info(f"Reusing existing session for {session_hash} with {len(self._sessions[session_hash].chat_history)} turns")
            return self._sessions[session_hash]

    def get_session(self, session_hash: str) -> StreamingSessionState | None:
        with self._lock:
            return self._sessions.get(session_hash)
    
    def get_first_active_session(self) -> StreamingSessionState | None:
        """Finds the first session that is currently recording (POC method)."""
        with self._lock:
            for state in self._sessions.values():
                if state.streaming.is_recording:
                    return state
        return None
    
    def get_active_recording_sessions(self) -> List[str]:
        """Return all currently recording session hashes"""
        with self._lock:
            return [hash for hash, state in self._sessions.items() 
                    if state.streaming.is_recording and state.streaming.is_active]

    def remove_session(self, session_hash: str):
        with self._lock:
            if session_hash in self._sessions:
                del self._sessions[session_hash]
                logging.info(f"METRICS: active_sessions={len(self._sessions)} (context: session removed)")

    def cleanup_old_sessions(self, max_age_seconds: int = 3600):
        """Remove sessions older than max_age_seconds"""
        with self._lock:
            current_time = time.time()
            to_remove = []
            for session_hash, session in self._sessions.items():
                if current_time - session.created_at > max_age_seconds:
                    to_remove.append(session_hash)
            
            for session_hash in to_remove:
                logging.info(f"Cleaning up old session: {session_hash}")
                # Ensure resources are cleaned up before removing
                if self._sessions[session_hash]:
                     self._sessions[session_hash].cleanup_streaming_resources()
                del self._sessions[session_hash]
            
            if to_remove:
                logging.info(f"METRICS: active_sessions={len(self._sessions)} (context: {len(to_remove)} old sessions cleaned up)")

# Create the single, global instance
session_manager = SessionManager()