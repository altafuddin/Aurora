# In: logic/chat_logic.py
from typing import List
from .chat_models import ChatTurn
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
        # No audio was recorded, return the state unchanged.
        return chat_history, None, chat_history

    # --- 1. Get Audio Analysis from Azure ---
    assessment_result = speech_service.get_pronunciation_assessment(user_audio_filepath)

    if not assessment_result or "error" in assessment_result:
        # If the assessment fails, add an error message to the chat and stop.
        error_message = assessment_result.get("error", "Audio analysis failed.")
        chat_history.append(ChatTurn(text=f"Error: {error_message}"))
        # We need to reformat for display even on error
        display_history = []
        for i in range(0, len(chat_history), 2):
            user_msg = chat_history[i].text
            ai_msg = chat_history[i+1].text if (i+1) < len(chat_history) else None
            display_history.append((user_msg, ai_msg))
        return display_history, None, chat_history

    # --- 2. Process User's Turn ---
    user_transcript = assessment_result.get("DisplayText", "Sorry, I couldn't understand.")
    
    # Create a new ChatTurn object to store this turn's data
    user_turn = ChatTurn(
        text=user_transcript,
        pronunciation_report=assessment_result # Store the full report
    )
    chat_history.append(user_turn)

    # --- 3. Generate AI's Response ---
    # Prepare text-only history for the LLM
    text_history_for_llm = [
        {"role": "user" if i % 2 == 0 else "model", "parts": [{"text": turn.text}]}
        for i, turn in enumerate(chat_history)
    ]
    
    ai_response_text = llm_service.get_response(
        chat_history=text_history_for_llm[:-1], # History before user's current message
        user_prompt=user_transcript
    )
    
    # Add the AI's response to the history as a new turn
    ai_turn = ChatTurn(text=ai_response_text)
    chat_history.append(ai_turn)
    
    # --- 4. Synthesize Audio for AI's Response ---
    # Clean the text for TTS
    ai_response_text = clean_text_for_speech(ai_response_text)
    ai_audio_path = tts_service.synthesize_speech(ai_response_text)

    # --- 5. Format History for Gradio Display ---
    # The chatbot component expects a list of (user_msg, ai_msg) tuples.
    display_history = []
    for i in range(0, len(chat_history), 2):
        user_msg = chat_history[i].text
        ai_msg = chat_history[i+1].text if (i+1) < len(chat_history) else None
        display_history.append((user_msg, ai_msg))

    if chat_history:
      print("DEBUG: Last user turn object:", chat_history[-2])
    return display_history, ai_audio_path, chat_history