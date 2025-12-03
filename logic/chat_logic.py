# In: logic/chat_logic.py
import logging
import time
from typing import List, Optional, Tuple
from .chat_models import ChatTurn
from .session_models import StreamingSessionState
from .audio_models import AzurePronunciationReport
from .feedback_logic import find_actionable_feedback_point
from .prompts import create_in_conversation_feedback_prompt, create_conversational_prompt
from utils.text_cleaner import clean_text_for_speech

FEEDBACK_INTERVAL = 3

# ---  FUNCTION to keep the code clean ---
def format_history_for_gradio(chat_history: List[ChatTurn]) -> List[tuple[str, str]]:
    """
    Converts our list of ChatTurn objects into the list of dictionaries
    that the Gradio Chatbot component expects.
    """
    messages = []
    for i, turn in enumerate(chat_history):
        role = "user" if i % 2 == 0 else "assistant"
        messages.append({"role": role, "content": turn.text})
    return messages

# --- Main streaming-only chat function ---
def chat_function(
    session_state: StreamingSessionState,
    pronunciation_report: AzurePronunciationReport | None,
    user_transcript: str | None,
    llm_service,
    tts_service
) -> Tuple[List, Optional[str], StreamingSessionState]:
    """
    Handles the core logic for streaming audio-aware Natural Chat Mode.
    STREAMING-ONLY - No file-based fallback.

    Args:
        session_state: StreamingSessionState containing chat history and streaming state.
        pronunciation_report: Pre-processed Azure pronunciation assessment data from streaming.
        user_transcript: Extracted user speech text from streaming.
        llm_service: An instance of the LLM service to get AI responses.
        tts_service: An instance of the TTS service to synthesize AI responses.

    Returns:        
        A tuple containing:
            - display_history: List of tuples for Gradio display.
            - ai_audio_path: Path to the synthesized AI response audio.
            - updated session_state: The updated StreamingSessionState.
    """
    start_time = time.time()
    if not pronunciation_report or not user_transcript:
        # Reformat history for display even if there's no valid input
        display_history = format_history_for_gradio(session_state.chat_history)
        return display_history, None, session_state

    # --- 1. Use the pre-processed pronunciation report from streaming ---
    report = pronunciation_report

    # --- 2. Handle potential errors from the service ---
    if not report or report.recognition_status != "Success":
        error_message = "Sorry, I couldn't recognize any speech. Please try again."
        if report: # If there's a report, there might be more specific error info
            error_message = f"Audio Error: {report.recognition_status}"
        
        # 1. Add the user's failed attempt to the history
        user_turn = ChatTurn(text="(No speech detected)")
        session_state.chat_history.append(user_turn)
        
        # 2. Add the error message as the AI's response in a new turn
        ai_turn = ChatTurn(text=error_message)
        session_state.chat_history.append(ai_turn)
        
        # 3. Reformat history for display
        display_history = format_history_for_gradio(session_state.chat_history)
        return display_history, None, session_state

    # --- 3. Process the User's Turn using the validated data ---
    if user_transcript != report.display_text:
        logging.warning(f"Transcript mismatch: provided='{user_transcript}' vs report='{report.display_text}'")
        user_transcript = report.display_text  # Trust the report for consistency
    
    user_turn = ChatTurn(
        text=user_transcript,
        pronunciation_report= report # Store the entire validated Pydantic object
    )
    session_state.chat_history.append(user_turn)

    # --- 3. DETERMINE WHICH PROMPT TO USE (IDENTICAL LOGIC) ---
    final_ai_response = None
    num_user_turns = (len(session_state.chat_history) + 1) // 2
    
    # Check if it's a feedback turn (e.g., every 3rd turn)
    if num_user_turns > 1 and num_user_turns % FEEDBACK_INTERVAL == 0:
        print(f"DEBUG: Turn {num_user_turns}, checking for feedback point...")
        
        recent_reports = [
            turn.pronunciation_report for turn in session_state.chat_history 
            if turn.pronunciation_report is not None
        ][-FEEDBACK_INTERVAL:]  # This ensures we only get the last 3 (or fewer) reports
        actionable_point = find_actionable_feedback_point(recent_reports)
        
        if actionable_point:
            print(f"DEBUG: Actionable feedback point found: {actionable_point}")
            # If a point is found, create the special "Feedback Sandwich" prompt
            # We need to format the history for the prompt's context section
            history_for_prompt = "\n".join([f"User: {turn.text}" if i%2==0 else f"Aurora: {turn.text}" for i, turn in enumerate(session_state.chat_history)])
            
            prompt = create_in_conversation_feedback_prompt(
                chat_history_text=history_for_prompt,
                feedback_point=actionable_point
            )
            # Make ONE special API call for the integrated response
            final_ai_response = llm_service.get_response(full_prompt=prompt, chat_history=None)
            user_turn.feedback_tip = final_ai_response # Store the generated tip

    # --- 4. IF NO FEEDBACK WAS GENERATED, GET A NORMAL RESPONSE ---
    if not final_ai_response:
        # Prepare the persona prompt for the conversational LLM
        persona_prompt = create_conversational_prompt()
        # Prepare history for the normal conversational LLM
        text_history_for_llm = [
            {"role": "user" if i % 2 == 0 else "model", "parts": [{"text": turn.text}]}
            for i, turn in enumerate(session_state.chat_history)
        ]
        
        # Combine the persona prompt with the user's transcript
        full_prompt_for_conversation = f"{persona_prompt}\n\nUser: {user_transcript}"
        
        # Make the standard API call
        final_ai_response = llm_service.get_response(
            # The history should not include the latest user message
            chat_history=text_history_for_llm[:-1], 
            full_prompt=full_prompt_for_conversation
        )
    
    # --- 5. Synthesize Audio for AI's Response ---
    cleaned_text = clean_text_for_speech(final_ai_response)
    # ai_audio_path = tts_service.synthesize_speech(cleaned_text)
    ai_audio_path = None


    ai_turn = ChatTurn(text=final_ai_response)
    session_state.chat_history.append(ai_turn)

    # --- 6. Format Final History for Gradio Display ---
    display_history = format_history_for_gradio(session_state.chat_history)

    elapsed = time.time() - start_time
    logging.info(f"TIMING: chat_function completed in {elapsed:.2f}s")
    return display_history, ai_audio_path, session_state