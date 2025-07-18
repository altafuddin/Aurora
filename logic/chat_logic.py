# In: logic/chat_logic.py
from typing import List
from .chat_models import ChatTurn
from .audio_models import AzurePronunciationReport
from utils.text_cleaner import clean_text_for_speech


def chat_function(
    user_audio_filepath: str,
    chat_history: List[ChatTurn],
    speech_service,
    llm_service,
    tts_service
):
    """
    Handles the core logic for the audio-aware Natural Chat Mode.
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
        
        chat_history.append(ChatTurn(text=error_message))
        display_history = format_history_for_gradio(chat_history)
        return display_history, None, chat_history

    # --- 3. Process the User's Turn using the validated data ---
    user_transcript = report.display_text
    
    user_turn = ChatTurn(
        text=user_transcript,
        pronunciation_report= report # Store the entire validated Pydantic object
    )
    chat_history.append(user_turn)

    # --- 4. Generate AI's Conversational Response ---
    text_history_for_llm = [
        {"role": "user" if i % 2 == 0 else "model", "parts": [{"text": turn.text}]}
        for i, turn in enumerate(chat_history)
    ]
    
    ai_response_text = llm_service.get_response(
        chat_history=text_history_for_llm[:-1],
        user_prompt=user_transcript
    )
    
    # Add the AI's response to the history
    ai_turn = ChatTurn(text=ai_response_text)
    chat_history.append(ai_turn)
    
    # --- 5. Synthesize Audio for AI's Response ---
    cleaned_text = clean_text_for_speech(ai_response_text)
    ai_audio_path = tts_service.synthesize_speech(cleaned_text)

    # --- 6. Format Final History for Gradio Display ---
    display_history = format_history_for_gradio(chat_history)

    return display_history, ai_audio_path, chat_history

# --- ADD THIS NEW HELPER FUNCTION to keep the code clean ---
def format_history_for_gradio(chat_history: List[ChatTurn]) -> List[tuple[str, str]]:
    """
    Converts our list of ChatTurn objects into the list of tuples
    that the Gradio Chatbot component expects.
    """
    display_history = []
    for i in range(0, len(chat_history), 2):
        user_msg = chat_history[i].text
        # Check if an AI message exists for this turn
        ai_msg = chat_history[i+1].text if (i+1) < len(chat_history) else None
        display_history.append((user_msg, ai_msg))
    return display_history