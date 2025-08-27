# In: logic/ielts_handlers.py

import gradio as gr #type:ignore
import logging
from .session_manager import session_manager
from .ielts_models import SessionPhase
from .ielts_logic import (
    start_ielts_test, process_answer, continue_to_next_part,
    generate_feedback, generate_final_report, reset_test, format_transcript_text
)

# --- Test Initialization Handler ---
def start_ielts_test_handler(request: gr.Request, question_bank):
    try:
        session_state = session_manager.get_or_create_session(request.session_hash)
        if not session_state:
            return (
                gr.update(visible=True),  # Show Start button
                gr.update(visible=False), # Hide Reset button
                gr.update(visible=False), # Hide Test interface
                "Error: No active IELTS test found. Please start a new test.", # question_display
                "", # Clear transcript display
                gr.update(visible=False)   # Hide recording interface
            )

        # Create a new, fresh IELTS test state
        new_ielts_state = start_ielts_test(question_bank)
        session_state.ielts_test_state = new_ielts_state
        if not new_ielts_state or not new_ielts_state.current_question_text:
            return (
                gr.update(visible=True),  # Show Start button
                gr.update(visible=False), # Hide Reset button
                gr.update(visible=False), # Hide Test interface
                "Error: Failed to initialize IELTS test.", # question_display
                "", # Clear transcript display
                gr.update(visible=False)   # Hide recording interface
            )

        # Prepare UI updates
        formatted_question = f"**Part 1: {new_ielts_state.questions['part1']['topic']}**\n\n{new_ielts_state.current_question_text}" #type: ignore
        
        return (
            gr.update(visible=False), # Hide Start button
            gr.update(visible=True),  # Show Reset button
            gr.update(visible=True),  # Show Test interface
            formatted_question,
            "", # Clear transcript display
            gr.update(visible=True)   # Show recording interface
        )
    except Exception as e:
        logging.error(f"Error in start_ielts_test_handler: {e}")
        return (
            gr.update(visible=True),  # Show Start button
            gr.update(visible=False), # Hide Reset button
            gr.update(visible=False), # Hide Test interface
            f"Error: {e}", # question_display
            "", # Clear transcript display
            gr.update(visible=False)   # Hide recording interface
        )

def start_ielts_answer_handler(request: gr.Request, streaming_service):
    """
    Handles the 'Start Answer' button click for the IELTS mode.
    Gets the user's session and initiates the real-time audio stream.
    """
    session_hash = request.session_hash
    logging.info(f"[{session_hash}] Starting IELTS answer recording.")
    session_state = session_manager.get_session(session_hash)        

    if not session_state or not session_state.ielts_test_state:
        logging.error(f"[{session_hash}] Attempted to start IELTS answer without an active test session.")
        return (
            gr.update(visible=True), # start answer button
            gr.update(visible=False), # stop answer button
            "Error: No active IELTS test found. Please start a new test." # status display
        )
    
    if session_state.ielts_test_state.session_phase != SessionPhase.IN_PROGRESS:
        return (
            gr.update(visible=False), # start answer button
            gr.update(visible=False), # stop answer button
            "Error: IELTS test is not in progress." # status display
        )
    logging.info(f"[{session_hash}] Session state: {session_state.ielts_test_state}")

    # Set a unique ID for logging context
    session_state.streaming.webrtc_id = f"{session_hash}-ielts"

    success, message = streaming_service.start_recording(session_state)
    
    # Update the UI to show that recording is active
    if success:
        logging.info(f"[{session_hash}] Recording started: {session_state.streaming.is_recording} And State: {session_state.ielts_test_state}")
        return (
            gr.update(visible=False), # start answer button
            gr.update(visible=True),  # stop answer button
            "Status: Recording answer..." # status display
        )
    else:
        return (
            gr.update(visible=True), # start answer button
            gr.update(visible=False), # stop answer button
            f"Error: {message}" # status display
        )


def stop_ielts_answer_handler(request: gr.Request, streaming_service):
    """
    Handles the 'Stop Answer' button click for the IELTS mode.
    Stops the stream, gets the final report, and calls the core IELTS logic.
    """
    session_hash = request.session_hash
    session_state = session_manager.get_session(session_hash)

    if not session_state or not session_state.ielts_test_state:
        logging.error(f"[{session_hash}] Attempted to stop IELTS answer without an active test session.")
        # This return needs to match all the outputs for the button click
        return (
            "Error: No active test session.", # question display
            "", # transcript_display
            gr.update(visible=False), # recording_interface
            gr.update(visible=False), # feedback_buttons
            gr.update(visible=False), # start answer button
            gr.update(visible=False), # stop answer button
            "Status: Recording Failed, Try again", # status display
        )

    # --- 1. Finalize the audio stream and get the report ---
    success, final_transcript, report = streaming_service.stop_recording(session_state)

    if not success or not report:
        error_message = final_transcript or "Failed to process audio."
        logging.error(f"[{session_hash}] Streaming service failed to return a valid report. Error: {error_message}")
        ielts_state = session_state.ielts_test_state
        return (
            ielts_state.current_question_text, # question display
            "Error: " + error_message, # transcript display
            gr.update(visible=True),   # recording_interface
            gr.update(), # feedback_buttons
            gr.update(visible=False), # start answer button
            gr.update(visible=True), # stop answer button
            "Status: Recording Failed, Try again" # status display
        )


    # --- 2. Call our refactored core IELTS logic function ---
    # The `process_answer` function will handle the state updates and determine the next UI state.
    updated_ielts_state = process_answer(session_state.ielts_test_state, report)

    # Update the main session state with the new IELTS state
    session_state.ielts_test_state = updated_ielts_state

    full_transcript_display = format_transcript_text(updated_ielts_state.answers)
    
    # Determine visibility based on the new state's phase
    is_part_over = updated_ielts_state.session_phase == SessionPhase.PART_ENDED
    
    # --- 3. Return all necessary UI updates ---
    # We return the values from `process_answer` and also reset the recording buttons.
    return (
        updated_ielts_state.current_question_text, # question display
        full_transcript_display, # transcript display
        gr.update(visible=not is_part_over), # Hide recording interface if part is over
        gr.update(visible=is_part_over),     # Show feedback buttons if part is over
        gr.update(visible=True),             # Show Start Answer button
        gr.update(visible=False),            # Hide Stop Answer button
        "Status: Ready to answer"  # Status message
    )

# --- Other UI Button Handlers ---
def continue_to_next_part_handler(request: gr.Request):
    session_state = session_manager.get_session(request.session_hash)
    if not session_state or not session_state.ielts_test_state: 
        return (
            "Error: No active test session.", # question display
            "", # transcript display
            gr.update(visible=False), # recording_interface
            gr.update(visible=False), # feedback_buttons
            gr.update(visible=False), # feedback display
            gr.update(visible=False)  # final report button
        )

    # Call the pure logic function
    updated_ielts_state = continue_to_next_part(session_state.ielts_test_state) #type: ignore
    session_state.ielts_test_state = updated_ielts_state

    full_transcript_display = format_transcript_text(updated_ielts_state.answers)
    is_test_over = updated_ielts_state.session_phase == SessionPhase.TEST_COMPLETED

    return (
        updated_ielts_state.current_question_text, 
        full_transcript_display, 
        gr.update(visible=not is_test_over), # Hide recording if test is over
        gr.update(visible=False),            # Always hide feedback buttons on continue
        gr.update(value="", visible=False),       # Clear the feedback display
        gr.update(visible=is_test_over)      # Show final report button if test is over
    )

def generate_feedback_handler(request: gr.Request, llm_service):
    session_state = session_manager.get_session(request.session_hash)

    if not session_state or not session_state.ielts_test_state: 
        yield "Error: Session not found.", gr.update(), gr.update()
        return

    # Yield a loading state first
    yield (
        gr.update(value="Generating feedback, please wait...", visible=True), # For ielts_feedback_display
        gr.update(interactive=False, visible=True), # Disable feedback button to prevent double-clicks
        gr.update(interactive=False, visible=True)  # Disable continue button
    )

    # This is a generator, so we yield from it
    for (updated_state, feedback_display, get_part_feedback_button, continue_to_next_part_button) in \
        generate_feedback(session_state.ielts_test_state, llm_service):
        session_state.ielts_test_state = updated_state
        yield feedback_display, get_part_feedback_button, continue_to_next_part_button

def generate_final_report_handler(request: gr.Request, llm_service):
    session_state = session_manager.get_session(request.session_hash)

    if not session_state or not session_state.ielts_test_state: 
        yield gr.update(value="Error: Session not found.", visible=True), gr.update(interactive=False)
        return

    for (updated_state, feedback_display, generate_final_report_button) in \
        generate_final_report(session_state.ielts_test_state, llm_service):
        session_state.ielts_test_state = updated_state
        yield feedback_display, generate_final_report_button

def reset_test_handler(request: gr.Request):
    session_state = session_manager.get_session(request.session_hash)
    if session_state:
        session_state.ielts_test_state = None # Clear the IELTS state
    return reset_test() # reset_test returns a tuple of UI updates