# In: gradio_app.py

import gradio as gr
from services.stt_service import AssemblyAITranscriber
from services.llm_service import GeminiChat
from services.tts_service import GoogleTTS

# --- Initialize our services once when the app starts ---
stt_service = AssemblyAITranscriber()
llm_service = GeminiChat()
tts_service = GoogleTTS()

# Text cleaning function to remove Markdown characters
# This is useful for cleaning up the AI's response before TTS synthesis
def clean_text_for_speech(text):
    """Removes Markdown characters from text for cleaner TTS output."""
    text = text.replace('*', '')
    text = text.replace('#', '')
    text = text.replace('_', '')
    return text


def create_gradio_interface():
    """
    Creates and returns the Gradio web interface for the chat application.
    """
    
    # The main chat processing function
    def chat_function(user_audio, chat_history_state):
        if user_audio is None:
            return chat_history_state, None, chat_history_state

        # 1. Transcribe user's speech
        user_text = stt_service.transcribe(user_audio)
        if user_text.startswith("Error:"):
            # If transcription fails, show the error and stop
            chat_history_state.append((user_text, None))
            return chat_history_state, None, chat_history_state

        # Append user's transcribed message to the chat history
        chat_history_state.append((user_text, None))

        # 2. Get LLM response
        # We need to format the history for the Gemini API
        gemini_history = []
        for user_msg, ai_msg in chat_history_state:
            if user_msg:
                gemini_history.append({'role': 'user', 'parts': [user_msg]})
            if ai_msg:
                 gemini_history.append({'role': 'model', 'parts': [ai_msg]})

        # Remove the last user message from history for the API call
        *_, last_user_prompt = gemini_history
        ai_response_text = llm_service.get_response(gemini_history[:-1], last_user_prompt['parts'][0])
        
        # Update the last entry in the chat history with the AI's response
        chat_history_state[-1] = (user_text, ai_response_text)

        # 3. Convert AI response to speech
        cleaned_text = clean_text_for_speech(ai_response_text)
        ai_audio_path = tts_service.synthesize_speech(cleaned_text)

        # Return updated chat history, the path to the AI's audio for autoplay, and the new state
        return chat_history_state, ai_audio_path, chat_history_state


    # --- Building the UI ---
    with gr.Blocks(theme=gr.themes.Soft(), title="Aurora AI") as interface:
        gr.Markdown("# Aurora: Your AI English Speaking Coach")
        
        with gr.Tab("Free Chat Mode"):
            gr.Markdown("Speak freely with the AI to practice your conversational English.")
            
            chatbot_display = gr.Chatbot(label="Conversation", height=500)
            
            # Hidden audio component for autoplaying the AI's response
            ai_audio_output = gr.Audio(visible=False, autoplay=True)
            
            # State component to store the conversation history
            chat_history_state = gr.State([])

            with gr.Row():
                mic_input = gr.Audio(sources=["microphone"], type="filepath", label="Speak Here")
            
            mic_input.stop_recording(
                fn=chat_function,
                inputs=[mic_input, chat_history_state],
                outputs=[chatbot_display, ai_audio_output, chat_history_state]
            )

        with gr.Tab("IELTS Practice Mode"):
            gr.Markdown("This feature is coming soon!")

    return interface