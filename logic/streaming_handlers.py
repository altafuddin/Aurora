# In: logic/streaming_handlers.py
import gradio as gr # type: ignore
from .session_manager import session_manager
from .chat_logic import chat_function, format_history_for_gradio

def start_recording_handler(request: gr.Request, llm_service, tts_service, streaming_service):
    """Start recording handler, creating and managing the session."""
    session_hash = request.session_hash
    session_state = session_manager.get_or_create_session(session_hash)

    # Set session context for service logging and error tracking
    session_state.streaming.webrtc_id = session_hash

    # Start the background consumer thread and other setup from the POC
    success, message = streaming_service.start_recording(session_state)
    
    if success:
        return gr.update(visible=False), gr.update(visible=True), message
    else:
        return gr.update(visible=True), gr.update(visible=False), message

def stop_recording_handler(request: gr.Request, llm_service, tts_service, streaming_service):
    """Stop recording and process results."""
    session_hash = request.session_hash
    session_state = session_manager.get_session(session_hash)

    if not session_state:
        return gr.update(visible=True), gr.update(visible=False), "Error: No session found.", {}, None

    success, transcript, report = streaming_service.stop_recording(session_state)
    
    if success:
        display_history, ai_audio_path, _ = chat_function(
            session_state=session_state,
            pronunciation_report=report,
            user_transcript=transcript,
            llm_service=llm_service,
            tts_service=tts_service
        )
        # Let the service handle cleanup timing
        session_manager.remove_session(session_hash)
        return gr.update(visible=True), gr.update(visible=False), "Ready to record", display_history, ai_audio_path
    else:
        session_manager.remove_session(session_hash)
        error_message = transcript if transcript else "Recording failed"
        return gr.update(visible=True), gr.update(visible=False), error_message, format_history_for_gradio(session_state.chat_history), None