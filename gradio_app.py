# In: gradio_app.py

import gradio as gr # type: ignore
from functools import partial
from fastrtc import Stream # type: ignore
# --- Import services and models ---
# from services.stt_service import AssemblyAITranscriber
from services.azure_speech_service import AzureSpeechService
from services.llm_service import GeminiChat
from services.tts_service import GoogleTTS
from services.streaming_speech_service import StreamingAudioService    
from data.ielts_questions import IELTSQuestionBank
from logic.ielts_models import IELTSState
from logic.ielts_logic import (
    start_ielts_test, 
    process_answer, 
    reset_test, 
    continue_to_next_part, 
    generate_feedback,
    generate_final_report
)
from logic.audio_processing import AuroraStreamHandler
from logic.streaming_handlers import start_recording_handler, stop_recording_handler

# --- Initialize services and data handlers once when the app starts ---
# These are the "global" resources our app will use.
azure_speech_service = AzureSpeechService()
streaming_speech_service = StreamingAudioService()
# stt_service = AssemblyAITranscriber()
llm_service = GeminiChat()
tts_service = GoogleTTS()
question_bank = IELTSQuestionBank()
# Initialize the single, global handler
stream_handler = AuroraStreamHandler()
audio_stream = Stream(handler=stream_handler, modality="audio", mode="send-receive")

# --- Main UI Function ---
def create_gradio_interface():
    """
    Defines the Gradio user interface and connects it to the logic functions.
    This file is now only responsible for the 'view' of our application.
    """
    with gr.Blocks(theme=gr.themes.Soft(), title="Aurora AI") as interface: # type: ignore
        gr.Markdown("# Aurora: Your AI English Speaking Coach")
        
        # --- Tab 1: Free Chat Mode ---
        with gr.Tab("Free Chat Mode"):
            # UI components
            chatbot_display = gr.Chatbot(label="Conversation", type="messages", height=500)
            ai_audio_output = gr.Audio(visible=False, autoplay=True)
            status_display = gr.Markdown("**Status**: Ready to record")
            

            with gr.Row():
                start_button = gr.Button("🎤 Start Recording")
                stop_button = gr.Button("⏹️ Stop Recording", visible=False)

            # Mount WebRTC component
            webrtc_component = audio_stream.webrtc_component
            webrtc_component.render()
            
            # Define wrapper functions at module level (outside the Blocks context)
            def start_recording_wrapper(request: gr.Request):
                return start_recording_handler(request, llm_service, tts_service, streaming_speech_service)

            def stop_recording_wrapper(request: gr.Request):
                return stop_recording_handler(request, llm_service, tts_service, streaming_speech_service)
            # Wire up event handlers
            start_button.click(
                fn=start_recording_wrapper,  
                # inputs=[], # Gradio automatically provides `request` if the function signature has it
                outputs=[start_button, stop_button, status_display]
            )
            
            stop_button.click(
                fn=stop_recording_wrapper,
                # inputs=[],
                outputs=[start_button, stop_button, status_display, chatbot_display, ai_audio_output]
            )

        # --- Tab 2: IELTS Practice Mode ---
        with gr.Tab("IELTS Practice Mode"):
            gr.Markdown("""
            ## IELTS Speaking Test Simulation
            
            This is a complete IELTS Speaking test simulation with all three parts:
            - **Part 1**: Introduction and interview (4-5 minutes)
            - **Part 2**: Long turn with cue card (3-4 minutes)
            - **Part 3**: Discussion (4-5 minutes)
            
            Click 'Start Test' to begin a IELTS Speaking simulation set.
            """)
            
            # >> Initialize the state component with our new dataclass
            ielts_state = gr.State(IELTSState())

            with gr.Row():
                start_button = gr.Button("🎯 Start New IELTS Test", variant="primary", size="lg")
                reset_button = gr.Button("🔄 Reset", variant="secondary", visible=False)
            
            with gr.Column(visible=False) as test_interface:
                question_display = gr.Markdown("### Question will appear here")
                
                with gr.Column(visible=True) as recording_interface:
                    mic_input_ielts = gr.Audio(
                        sources=["microphone"], 
                        type="filepath", 
                        label="🎤 Record Your Answer"
                    )
                    gr.Markdown("*Speak clearly and naturally.*")
                
                with gr.Row(visible=False) as feedback_buttons:
                    get_part_feedback_button = gr.Button("📊 Get Feedback for This Part", variant="primary", scale=1, min_width=180)
                    continue_to_next_part_button = gr.Button("➡️ Continue ", variant="secondary", scale=1, min_width=180)
                
                generate_final_report_button = gr.Button(
                    "🏆 Generate Final Comprehensive Report",
                    variant="primary",
                    visible=False,
                    scale=1,
                    size="lg"
                )

                # Component to display the feedback report
                feedback_display = gr.Markdown(visible=False)


                with gr.Accordion("📝 Your Answers", open=False):
                    transcripts_display = gr.Textbox(
                        label="Recorded Answers", 
                        lines=10, 
                        interactive=False,
                        placeholder="Your transcribed answers will appear here..."
                    )

            # --- Event Listeners for IELTS Mode ---
            start_button.click(
                fn=lambda: start_ielts_test(question_bank),
                inputs=[],
                outputs=[
                    ielts_state, 
                    start_button,
                    reset_button, 
                    test_interface, 
                    question_display, 
                    transcripts_display,
                    recording_interface,
                    feedback_buttons
                ]
            )
            
            mic_input_ielts.stop_recording(
                fn=lambda audio, state: process_answer(audio, state, azure_speech_service),
                inputs=[mic_input_ielts, ielts_state],
                outputs=[
                    ielts_state, 
                    question_display, 
                    transcripts_display, 
                    recording_interface,
                    feedback_buttons
                ]
            )
            
            reset_button.click(
                fn=reset_test,
                inputs=[],
                outputs=[
                    ielts_state, 
                    start_button, 
                    reset_button,
                    test_interface, 
                    question_display, 
                    transcripts_display, 
                    recording_interface,
                    feedback_buttons,
                    feedback_display
                ]
            )

            continue_to_next_part_button.click(
                fn=continue_to_next_part,
                inputs=[ielts_state],
                outputs=[
                    ielts_state, 
                    question_display, 
                    transcripts_display,
                    recording_interface, 
                    feedback_buttons,
                    feedback_display,
                    generate_final_report_button
                ]
            )

            # click handler for the get_part_feedback_button
            get_part_feedback_button.click(
                fn=partial(generate_feedback, llm_service=llm_service),
                inputs=[ielts_state],
                outputs=[
                    ielts_state, 
                    feedback_display, 
                    get_part_feedback_button, 
                    continue_to_next_part_button
                ]
            )

            generate_final_report_button.click(
                fn=partial(generate_final_report, llm_service=llm_service),
                inputs=[ielts_state],
                outputs=[
                    ielts_state,
                    feedback_display,
                    generate_final_report_button
                ]
            )

    return interface