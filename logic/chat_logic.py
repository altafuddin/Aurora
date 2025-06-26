# In: logic/chat_logic.py

from utils.text_cleaner import clean_text_for_speech

def chat_function(user_audio, chat_history_state, stt_service, llm_service, tts_service):
    """
    Handles the core logic for the Free Chat Mode.
    Takes user audio, runs it through the services, and returns updates.
    """
    if user_audio is None:
        return chat_history_state, None, chat_history_state

    # 1. Transcribe user's speech
    user_text = stt_service.transcribe(user_audio)
    if user_text.startswith("Error:"):
        chat_history_state.append((user_text, None))
        return chat_history_state, None, chat_history_state

    chat_history_state.append((user_text, None))

    # 2. Get LLM response
    # We reformat the history every time for the Gemini API.
    gemini_history = []
    for user_msg, ai_msg in chat_history_state:
        if user_msg: gemini_history.append({'role': 'user', 'parts': [user_msg]})
        if ai_msg: gemini_history.append({'role': 'model', 'parts': [ai_msg]})

    ai_response_text = llm_service.get_response(gemini_history[:-1], gemini_history[-1]['parts'][0])
    
    chat_history_state[-1] = (user_text, ai_response_text)

    # 3. Convert AI response to speech
    cleaned_text = clean_text_for_speech(ai_response_text)
    ai_audio_path = tts_service.synthesize_speech(cleaned_text)

    # Return all the necessary updates for the UI
    return chat_history_state, ai_audio_path, chat_history_state