import gradio as gr
from services.stt_service import AssemblyAITranscriber

# This object is created once when the app starts and holds the API key.
transcriber_service = AssemblyAITranscriber()


def create_gradio_interface():
    """
    Creates and returns the Gradio web interface.
    """
    
    # This function now uses the shared service instance.
    def speech_to_text(audio_file):
        transcribed_text = transcriber_service.transcribe(audio_file)
        return transcribed_text

    with gr.Blocks(theme=gr.themes.Soft()) as interface:
        gr.Markdown("# Aurora: Your AI English Speaking Coach")
        gr.Markdown("Record yourself speaking, and see the transcription appear below.")
        
        with gr.Row():
            mic_input = gr.Audio(sources=["microphone"], type="filepath", label="Speak Here")
            
            # --- Step 2: Change Textbox to Text for the output ---
            # This change is made to ensure the try to avoid the error showing up in reload
            text_output = gr.Textbox(label="Transcription", interactive=False)
            # text_output = gr.Text(label="Transcription")
            
        submit_button = gr.Button("Transcribe")
        submit_button.click(
            fn=speech_to_text,
            inputs=mic_input,
            outputs=text_output
        )

    return interface