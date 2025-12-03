# In: logic/streaming_handlers.py
import gradio as gr # type: ignore
import logging
from .session_manager import session_manager
from .chat_logic import chat_function, format_history_for_gradio

logger = logging.getLogger(__name__)

def start_recording_handler(request: gr.Request, llm_service, tts_service, streaming_service):
    """Start recording handler, creating and managing the session."""
    session_hash = request.session_hash
    logger.info(f"[start_recording_handler] Called for session_hash: {session_hash}")

    if session_hash:
        logger.debug(f"[start_recording_handler] Getting or creating session for hash: {session_hash}")
        session_state = session_manager.get_or_create_session(session_hash)
        logger.debug(f"[start_recording_handler] Session state obtained")

    # Set session context for service logging and error tracking
    session_state.streaming.webrtc_id = session_hash
    logger.debug(f"[start_recording_handler] Set webrtc_id to session_hash")

    # Start the background consumer thread and other setup from the POC
    logger.info(f"[start_recording_handler] Starting recording via streaming_service")
    success, message = streaming_service.start_recording(session_state)
    logger.info(f"[start_recording_handler] Recording start result - success: {success}, message: {message}")

    if success:
        logger.info(f"[start_recording_handler] Recording started successfully, updating UI")
        return gr.update(visible=False), gr.update(visible=True), message
    else:
        logger.warning(f"[start_recording_handler] Recording start failed: {message}")
        return gr.update(visible=True), gr.update(visible=False), message

def stop_recording_handler(request: gr.Request, llm_service, tts_service, streaming_service):
    """Stop recording and process results."""
    session_hash = request.session_hash
    logger.info(f"[stop_recording_handler] Called for session_hash: {session_hash}")

    if session_hash:
        logger.debug(f"[stop_recording_handler] Getting session for hash: {session_hash}")
        session_state = session_manager.get_session(session_hash)

    if not session_state:
        logger.error(f"[stop_recording_handler] No session state found for hash: {session_hash}")
        return gr.update(visible=True), gr.update(visible=False), "Error: No session found.", {}, None

    logger.info(f"[stop_recording_handler] Stopping recording via streaming_service")
    success, transcript, report = streaming_service.stop_recording(session_state)
    logger.info(f"[stop_recording_handler] Recording stop result - success: {success}, transcript length: {len(transcript) if transcript else 0}")

    if success and session_hash:
        logger.info(f"[stop_recording_handler] Recording successful, calling chat_function")
        display_history, ai_audio_path, _ = chat_function(
            session_state=session_state,
            pronunciation_report=report,
            user_transcript=transcript,
            llm_service=llm_service,
            tts_service=tts_service
        )
        logger.debug(f"[stop_recording_handler] Chat function completed, ai_audio_path: {ai_audio_path}")

        # Let the service handle cleanup timing
        logger.info(f"[stop_recording_handler] Removing session: {session_hash}")
        # session_manager.remove_session(session_hash)
        logger.info(f"[stop_recording_handler] Successfully completed, returning results")
        return gr.update(visible=True), gr.update(visible=False), "Ready to record", display_history, ai_audio_path
    else:
        logger.warning(f"[stop_recording_handler] Recording failed or no session_hash")
        if session_hash:
            logger.info(f"[stop_recording_handler] Removing session after failure: {session_hash}")
            # session_manager.remove_session(session_hash)
        error_message = transcript if transcript else "Recording failed"
        logger.error(f"[stop_recording_handler] Returning error: {error_message}")
        return gr.update(visible=True), gr.update(visible=False), error_message, format_history_for_gradio(session_state.chat_history), None