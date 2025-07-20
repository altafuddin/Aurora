# In: logic/chat_logic.py
from typing import List
from .chat_models import ChatTurn
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

# --- Main chat function ---
def chat_function(
    user_audio_filepath: str,
    chat_history: List[ChatTurn],
    speech_service,
    llm_service,
    tts_service
):
    """
    Handles the core logic for the audio-aware Natural Chat Mode.

    Args:
        user_audio_filepath: Path to the user's audio file.
        chat_history: List of previous ChatTurn objects.
        speech_service: An instance of the speech service to process audio.
        llm_service: An instance of the LLM service to get AI responses.
        tts_service: An instance of the TTS service to synthesize AI responses.

    Returns:        
        A tuple containing:
            - display_history: List of tuples for Gradio display.
            - ai_audio_path: Path to the synthesized AI response audio.
            - updated chat_history: The updated list of ChatTurn objects.
    """
    if not user_audio_filepath:
        # Reformat history for display even if there's no audio
        display_history = format_history_for_gradio(chat_history)
        return display_history, None, chat_history

    # --- 1. Get the validated Pydantic object from Azure ---
    report: AzurePronunciationReport | None = speech_service.get_pronunciation_assessment(user_audio_filepath)

    # --- 2. Handle potential errors from the service ---
    if not report or report.recognition_status != "Success":
        error_message = "Sorry, I couldn't recognize any speech. Please try again."
        if report: # If there's a report, there might be more specific error info
            error_message = f"Audio Error: {report.recognition_status}"
        
        # 1. Add the user's failed attempt to the history
        user_turn = ChatTurn(text="(No speech detected)")
        chat_history.append(user_turn)
        
        # 2. Add the error message as the AI's response in a new turn
        ai_turn = ChatTurn(text=error_message)
        chat_history.append(ai_turn)
        
        # 3. Reformat history for display
        display_history = format_history_for_gradio(chat_history)
        return display_history, None, chat_history

    # --- 3. Process the User's Turn using the validated data ---
    user_transcript = report.display_text
    
    user_turn = ChatTurn(
        text=user_transcript,
        pronunciation_report= report # Store the entire validated Pydantic object
    )
    chat_history.append(user_turn)

    # --- 3. DETERMINE WHICH PROMPT TO USE (NEW LOGIC) ---
    final_ai_response = None
    num_user_turns = (len(chat_history) + 1) // 2
    
    # Check if it's a feedback turn (e.g., every 3rd turn)
    if num_user_turns > 1 and num_user_turns % FEEDBACK_INTERVAL == 0:
        print(f"DEBUG: Turn {num_user_turns}, checking for feedback point...")
        
        recent_reports = [
            turn.pronunciation_report for turn in chat_history 
            if turn.pronunciation_report is not None
        ][-FEEDBACK_INTERVAL:]  # This ensures we only get the last 3 (or fewer) reports
        actionable_point = find_actionable_feedback_point(recent_reports)
        
        if actionable_point:
            print(f"DEBUG: Actionable feedback point found: {actionable_point}")
            # If a point is found, create the special "Feedback Sandwich" prompt
            # We need to format the history for the prompt's context section
            history_for_prompt = "\n".join([f"User: {turn.text}" if i%2==0 else f"Aurora: {turn.text}" for i, turn in enumerate(chat_history)])
            
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
            for i, turn in enumerate(chat_history)
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
    ai_audio_path = tts_service.synthesize_speech(cleaned_text)

    ai_turn = ChatTurn(text=final_ai_response)
    chat_history.append(ai_turn)

    # --- 6. Format Final History for Gradio Display ---
    display_history = format_history_for_gradio(chat_history)

    return display_history, ai_audio_path, chat_history
